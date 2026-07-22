# R2253 (HM2): BUG1 499 完整 trace 抓证 — cc4101+nv_gw 两端加 _log_error_detail (撤40007 可观测性优先步)

## 背景
承接 [[cc2-real-status-2026-07-22]] + ChatGPT 讨论 (chatgpt_api/docs/cc2_real_status_2026-07-22.md, commit 3e318d7).
ChatGPT 决策: 撤40007 4 前置条件攻击顺序 = **可观测性(优先) → mid-response → failure-invisible → 大负载**.
R2252 后单个最高价值动作 = **做 BUG1 499 最小可复现 + 证据链**, 不是修, 是回答:
499 是 client 真断? proxy 误判? R2252 retry 切换导致连接失效? 还是 upstream body 生命周期问题?
最小动作 = 给 499 加完整 trace (request_id + key版本 + retry次数 + stream阶段 + body bytes sent + disconnect timestamp).

## 改前数据 (HM2, 2026-07-22, 近6h)
- 499 (client_gone_mid_stream): **22 个/6h** (约 3.7/h), 全 cc-glm5-2, 全 is_stream=true
- **两种形态**:
  - **形态A primary 路径 499 (18/22=82%)**: fallback_triggered=false, primary_error_type=NULL, upstream_used=primary
    - ttfb_ms 巨大: 125714/124762/135400/139932/132178/26768 (NVCF 首字节 125-140s)
    - duration_ms: 多在 120-140s 区间; total_input_chars 157K-237K (大请求)
    - primary_error_type=NULL → primary 阶段没记 timeout, 是流到一半 client 断
  - **形态B fallback 路径 499 (4/22=18%)**: fallback_triggered=true, primary_error_type=timeout, primary_elapsed_ms=180105
    - primary 跑满 180s timeout 触发 fallback, fallback 也 499 (client 早走了)
- **核心假设**: NVCF TTFB 慢 (125-140s) → CC 客户端等不及/中途断 → cc4101 检测 client gone → 499.
  但 DB 显示 ttfb 都有值 (post-ttfb 499), 说明 client 是在 NVCF 开始返回后才断,
  真根因可能是 ttfb 后流式输出太慢/中途 stall → client 在 ttfb 后又等很久才断 (duration 135s - ttfb 125s = ttfb后10s断).
  **需 trace 区分子类**: 499-pre-ttfb vs 499-post-ttfb + 断点 bytes_sent + exc_type.

## 改动 (仅 HM2, 3 文件, bind-mount restart 生效)
**cc4101 端 (client 侧 trace, 证据最直接)**:
1. `proxy/cc4101/gateway/stream.py`:
   - `_write_bytes` 累计 `_bytes_written` + 记 `_disc_exc` (断开异常对象)
   - L128 mid-stream 499 断点: 加 `_log_error_detail` 写 `CC4101-499-MIDSTREAM` trace
     (stage=streaming_post_ttfb, ttfb_ms, duration_ms, post_ttfb_ms, bytes_sent, exc_type, exc_msg, upstream_error_seen)
   - L44 pre-stream 499: 加 `CC4101-499-PRE-HEADERS` trace (stage=pre_headers, bytes_sent=0)
2. `proxy/cc4101/gateway/handlers.py`:
   - L219 mid-stream outer catch: 加 `CC4101-499-OUTER-MIDSTREAM` trace
   - L239 mid-collect outer catch: 加 `CC4101-499-MIDCOLLECT` trace

**nv_gw 端 (上游侧 trace, 含 R2252 retry 状态)**:
3. `proxy/nv-gw/gateway/handlers.py`:
   - L1322 pre-SSE-headers 499: 加 `NV-GW-499-PRE-HEADERS` trace
     (nv_key_idx, peek_internal_rescued, mapped_model, ttfb_ms, duration_ms, exc_type)

**trace 字段对照 ChatGPT 要求**:
| 要求 | 字段 | 来源 |
|---|---|---|
| request_id | request_id | 两端 metrics |
| key版本 | nv_key_idx | nv_gw (cc4101 透传不知) |
| retry次数 | peek_internal_rescued | nv_gw R2252 |
| stream阶段 | stage | cc4101 (pre_headers/streaming_post_ttfb/mid_collect) |
| body bytes sent | bytes_sent | cc4101 _write_bytes 累计 |
| disconnect timestamp | ts + duration_ms + post_ttfb_ms | 两端 |

**不动**: metrics 流 / DB schema / 现有 _log_metrics. 只加 _log_error_detail JSONL (error_detail.{date}.jsonl / nv_error_detail.{date}.jsonl).

## 验证
- ast: stream.py/handlers.py(cc4101)+handlers.py(nv_gw) 全 ast OK
- restart: docker compose restart cc4101 nv_gw, 两容器 Up, 无报错
- health: nv_gw 200 (nv_num_keys=5, default=glm5_2_nv), cc4101 200 (primary=glm5_2_nv)
- 代码加载: grep CC4101-499-MIDSTREAM/OUTER-MIDSTREAM/NV-GW-499-PRE-HEADERS 各=1 (容器内)
- 流量: 重启后 glm5_2_nv 请求正常流过 (NV-GLM52-ATTEMPT k1 pexec)

## 预期 + 下轮
- **shadow 抓证 2-3h**: 基线 3.7 499/h, 2h 预期抓 6-14 个完整 trace.
- 分析维度:
  1. **stage 分布**: pre_headers vs streaming_post_ttfb vs mid_collect 占比 → 定位断点阶段
  2. **post_ttfb_ms 分布**: ttfb 后多久断 → 若普遍 <10s 则是 ttfb 后 stall; 若 >60s 则是流到尾端断
  3. **bytes_sent 分布**: 断时已发多少字节 → 0=pre-ttfb 假死; 大=流到一半
  4. **exc_type 分布**: BrokenPipe vs ConnectionReset vs OSError → client 主动断 vs 网络断
  5. **nv_key_idx/peek_internal_rescued 关联**: R2252 retry 是否制造新 499 (换 key 时下游连接中断?)
- 拿到 trace 后判定根因, 再决定改法 (不盲改, 铁律).
- 回滚 = restore .bak.R2253_t1_499trace + restart (3 文件均有 .bak).

## 关联
- [[cc2-real-status-2026-07-22]] 真实状态诊断
- [[r2252-peek-internal-keyretry]] R2252 peek 内部换 key (task3 已做, 本轮验证是否引入新 499)
- ChatGPT 讨论: chatgpt_api/docs/cc2_real_status_2026-07-22.md (commit 3e318d7)
- 铁律: 只改 HM2, 不碰 ms_gw 源码, 改后必验证
