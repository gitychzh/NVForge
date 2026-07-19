# R1918 (HM2 cc2): BUG-B 方案0 — peek 健康分支补 cap_origin 重置 (补 R1818 bug7 漏修路径)

> 铁律1 (改前必有数据) ✓: 改前实测 abs_cap 样本 b39ea95c (upstream_type=nvcf_pexec, fb=f, ttfb=192s, cap_elapsed==total_elapsed 铁证).
> 铁律2 (改后必有验证) ✓: restart 后 /health ok + md5 宿主/容器一致 + 3 条真实请求 PEEK-OK 成功 + 启动无报错.
> 铁律3 (聚焦 40006) ✓: 只改 nv_gw handlers.py, 不碰 ms_gw.
> 铁律4 (写入仓库) ✓: 本文件 + handlers.py 改动 (cp .bak.R1918 备份).
> 铁律5 (改.py restart 非 up-d) ✓: docker compose restart nv_gw, StartedAt 09:38Z→10:42:20Z.

## 背景 (监督者 19:25 + 19:50 深度定位, 写进 STATE 供本轮用)

R1817/R1818 bug7 把 abs_cap 的 `cap_origin` 从 `t_start` 改为独立基准, 在**两处 ms_fb 分支**重置:
- handlers.py:1055 (peek 软挂→ms_fb 重放分支) `cap_origin = time.time()`
- handlers.py:1139 (execute→ms_fb 分支, `if upstream_type == "ms_fallback":`) `cap_origin = time.time()`

**漏修路径**: peek **健康** 分支 (1027行 `_peek_content_seen=True` 真分支, `_log NV-PEEK-OK`) 不重置 cap_origin.
- fb=f 路径 (upstream_type=nvcf_pexec 直连 NVCF, 未切 ms): cap_origin 起初 = t_start (912行).
- NVCF 首字节慢 (152-192s) 但 peek barrier 用 `_fb_s` 从 peek 开始算 (不含 peek 前 pexec 兜底 ~140s), peek 在 _fb_s 内通过.
- 进主循环瞬间 `cap_elapsed = now - cap_origin = now - t_start` 已含 pexec 僵尸期 ~140-190s > 150s → **秒触发 abs_cap=502**.
- abs_cap 日志铁证: `cap_elapsed == total_elapsed` (152/163/168/192s 全等), `peek_swapped=False`, `content_chars=0, reasoning_chars=0`.

## 改前数据 (本 session 18:30Z 拉取)

### 30min nv_gw 窗口 (18:00-18:30Z)
- **SR = 66/68 = 97.1%** (200:66 / 502:2). 抖动区间中上段常态, 健康.
- 502=2 两分类:
  - **stream_absolute_cap×1** — req=b39ea95c 18:21:49, glm5_2_nv, **正是 BUG-B fb=f 根因样本**:
    - upstream_type=nvcf_pexec (直连, **非 ms_fallback**, 故 R1818 不覆盖)
    - fallback_occurred=f (fb=f, 未走 ms)
    - ttfb_ms=195838 (~192s, peek 慢通过)
    - duration_ms=195839 = ttfb+1 (**cap_elapsed==total_elapsed 秒触发铁证**)
    - egress_ip=134.195.101.193, function_id=3b9748d8 (glm5_2_nv 出口 IP 段)
    - key_cycle_details: 4 key 前 3 个 pexec_empty_200 (zombie), 第 4 个 pexec_success elapsed 12069ms → NVCF 第 4 key 才回健康首块但前面已烧 ~180s
  - **zombie_empty_completion×1** — glm5_2_nv 首字节快回空 (NVCF 上游侧已知类).
- tier 30min: pexec_success 48 / pexec_empty_200 8 (zombie 同源, 被 retry 重吸收到 200).
- fallback 5 FALLBACK-OK 全成功 (其中 75s SKIP-CIRCUIT 几条 + 120s 几条, 0 真中断, ms_gw 全兜住).
- breaker: NV-ANTH-BREAKER-FAIL 2 (18:21:49 abs_cap req=b39ea95c + 18:28:00 zombie req=0264b7fe, state CLOSED (1,0) 吸收未 OPEN).
- bug8 DOWNGRADE 0 触发 (连续 57+ 轮根除停巡).
- NV-CAP-RESET-MSFB 3 次 (R1818 bug7 已修路径, 与本轮无冲突).

### BUG-A STAGE1 in-vivo 续触发确认
- 18:12:57 req=55c4da0e: NV-GLM52-CHAIN-FALLBACK → CHAIN-SKIP-PEXEC2 → MS-FB-ATTEMPT → MS-FB-OK (5914ms) → MS-FB-SERVED.
- 四连锁跳过 pexec 第二轮, 直接走 ms_fb, **省 ~120s/fallback 请求**. BUG-A 修复持续 in-vivo 生效 (R1913 落地, R1917 首验证, R1918 续触发确认). ✅

## 改动 (方案0, 1 行核心 + 观测日志)

handlers.py peek 健康分支 (1026 行 `last_real_content_time = time.time()` 之后), 补:

```python
# R1918 BUG-B 方案0 (监督者 19:50 深度定位): 补 R1818 bug7 漏修的 peek 健康分支.
cap_origin = time.time()
if metrics["ttfb_ms"] > NVU_STREAM_ABSOLUTE_CAP_S * 1000:
    _log("NV-PEEK-CAP-RESET", ...)  # 观测点: peek 慢>cap 阈值但健康放行, 本会秒触发 abs_cap, 现已防
```

镜像 R1818 两处 ms_fb 分支的 `cap_origin = time.time()` 模式, 把漏掉的 fb=f peek 健康路径补上.

### 语义 (为何不更坏只更好)
- NVCF 给了健康首块 (peek 通过证明) → 重置 cap_origin 后, 主循环 cap 只盯 "peek 通过后 active stream 跑多久".
- NVCF 后续真 content 正常 relay → **不再秒触发 abs_cap** (✅ 改善, 治 38 条 fb=f 的 73%).
- NVCF 后续真软卡 → 走 no_content_gap/total_deadline 正常 idle 判定 (非秒触发), 也合理 (✅ 不变坏).
- 风险极低: cap_origin 重置是 R1817/R1818 已验证模式, 本轮是逻辑补全非新行为.

## 验证 (restart 10:42:20Z 后)

1. **StartedAt = 2026-07-19T10:42:20Z** (从 09:38Z 刷新, restart 生效).
2. **/health = ok** (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
3. **docker ps**: nv_gw Up 8 seconds (restart 后), cc4101/ms_gw/logs_db 全 Up 未受影响.
4. **md5 宿主/容器一致** = `6ed910cccd81bf61d5f2b4c5381b2b1c` → bindmount 生效, 跑改后字节码.
5. **启动日志无报错**: NV-PROXY Listening on 0.0.0.0:40006, RR/glm52_mode 恢复正常.
6. **链路往返正常**: restart 后 3 条真实请求 PEEK-OK 成功 (f9ba53b6 10334ms / 25880fe1 58651ms / d7be0f14 19070ms, ttfb 均<150s 本不触发 abs_cap, 正常 relay).
7. **Python 语法检查**: ast.parse SYNTAX OK.

### R1918 真正验证样本 (低频, 待下窗口攒)
abs_cap 是低频事件 (~1.67/h, 当前 30min 仅 1 条 b39ea95c). R1918 的真正验证样本是: **下个窗口若出现 ttfb>150s 的 peek 慢请求** (像 b39ea95c 192s), 应不再秒触发 abs_cap, 而是正常 relay (看到 `NV-PEEK-CAP-RESET` 日志触发 + 该请求 200 而非 502).
- 当前 30min 无 ttfb>150s 样本, 无法本轮完成完整验证.
- 下轮 R1919 拉数据时重点看: 若仍有 abs_cap fb=f 触发 = 方案0 失败需回滚; 若 `NV-PEEK-CAP-RESET` 触发且对应请求 200 = 方案0 in-vivo 生效.

## 决策: 动手 (非 NOP)

介入条件满足 (铁律1 有数据):
1. 本轮窗口有 1 条 abs_cap fb=f 样本 (b39ea95c, cap_elapsed==total_elapsed 铁证), 正是方案0 目标.
2. 监督者 19:50 明确指示 "方案0 最该先动, 风险极低, 是 R1818 bug7 的逻辑补全, 建议下轮动".
3. 改动是 R1818 已验证模式的逻辑补全 (cap_origin=now 重置), 风险极低, 非新行为.
4. SR 97.1% 高位健康, 不是救火, 是趁稳修低频结构性漏洞 (abs_cap fb=f 秒触发).

## 回滚预案 (验证失败时)
- `cp /opt/cc-infra/proxy/nv-gw/gateway/handlers.py.bak.R1918 /opt/cc-infra/proxy/nv-gw/gateway/handlers.py`
- `cd /opt/cc-infra && docker compose restart nv_gw`
- 触发条件: 下窗口若 abs_cap fb=f 仍产 OR 新出现 content_chars>0 被错误延长 OR SR 跌破 80%.

## commit + push
- handlers.py 改动 + 本 round 文件.
- 预期 push origin/main 成功.
