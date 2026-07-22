# SPEC-003: 撤掉 40007(ms_gw fallback)路线图

> 状态: **规划中**(2026-07-22 与 ChatGPT 多轮讨论得出,代码改造第一步待实施)
> 关联: rounds/R1716(nv_gw 流式软全挂 ms barrier)、R1719/R1774(breaker)、
> R1771/R1820(graceful end)、R1673(big_input breaker)、R1648(转换下沉)
> 讨论工具: chatgpt_api `login_edge.py ask`(本仓库不承载讨论文档,讨论结论回流至此)

## 1. 终极目标

撤掉 40007(ms_gw fallback),让主 agent(cc2)完全靠 40006 nv_gw 主路径
(NVCF glm5.2)稳住,不再走 fallback。

## 2. 背景约束

1. nv_gw 有僵尸响应(NVCF 返 200+message_start 但内容空/极少),已用
   peek barrier + graceful end + breaker 三件套缓解(详见第 6 节)。
2. fallback(ms_gw,ModelScope glm5.2)走 cc4101 适配器层自动切换,但自身
   也有问题:ms_gw TTFB 慢(30s)、格式转换层曾出 parse-fail bug(已修)、
   cc2 走 fallback 时也出过 mid-response 中断。
3. cc2 prompt 很大(150K+ 字符),NVCF 对大 input 系统性 hang,cc2 是
   僵尸/超时高发对象。
4. 499(client_gone_mid_stream):cc2 中途主动断流被 cc4101 记成 client_gone,
   这种 499 在 primary 流式途中,**根本不进 fallback 分支**——所以 fallback
   对 499 也帮不上忙(R2199/R2202 已定位真根因为 NVCF TTFB 慢踩 cc4101 档)。

## 3. 四条前置条件(撤 40007 前必须达到的状态)

| # | 前置条件 | NVForge 现状 | 差距 |
|---|---|---|---|
| 1 | **主路径失败不可见**(最硬)— NVCF 异常不穿透到 cc2,nv_gw 自主检测/恢复/可控失败 | peek barrier 挡僵尸(R1716)、graceful end 让 cc2 正常结束(R1771/R1820) | nv_gw 软挂时仍切外部 ms_gw;需把"内部多 key 重试"做实替代 `_ms_fallback_request` |
| 2 | **大负载长期稳定**(最远)— 证明 150K+ prompt 下长期达 SLO,不靠 fallback 掩盖 | big_input breaker 把 >250k 预分流到 ms_gw(R1673);150-250k 段(R1715)仍漏 | 需影子 agent 在 150K+ 纯主路径(无 fallback)下跑 7-14 天收集数据 |
| 3 | **mid-response 可控** — 流中 hang/断流/半截响应不致 cc2 不可恢复 | R1774 已根治 mid-response breaker + graceful end | 已接近达成,需影子数据验证无复发 |
| 4 | **可观测性+故障归因**(最接近)— 撤 fallback 后能区分问题在 nv_gw/NVCF/cc2 | 已有 logs_db、peek、breaker、失败判定、cc4101 stall 观测 | 差链路归因体系化 |

## 4. 关键悖论与破法

**悖论**:前置条件 2 要求"证明主路径在 150K+ 大负载下稳",但只要 fallback 还在,
失败就被兜住,**永远收集不到纯主路径的大负载失败数据**——鸡生蛋问题。

**破法(影子测试)**:旁路复制真实流量给一个独立的影子 agent,它在 nv_gw 主路径上
**失败不兜底**,专门收集纯主路径的大负载失败数据,而真正生产的 cc2 还保留 fallback
不受影响。既收集到数据又不伤生产。

> NVForge 已部署的 hermes2/openclaw2 自优化系统正是这个思路的现成基础:
> 独立 agent session 跑在 nv_gw 上,失败不兜底,即天然的影子探针。

## 5. 执行顺序与量化切换标准

### 5.1 执行顺序

1. **上线影子 agent**(复用 hermes2/openclaw2),失败不 fallback,采集足够长周期的
   "纯 nv_gw 主路径失败数据",验证四条前置条件是否真实成立。
2. **根据影子数据修正并补齐** peek barrier、graceful end、breaker 等保护阈值,
   确认主路径失败可控后,**灰度降低 fallback 覆盖范围**。
3. **把 nv_gw 自己的异常恢复链路**(peek barrier、graceful end、breaker)补齐并稳定
   (不再依赖上层切后端)——即第 7 节的 peek 内部换 key 改造。
4. 达到量化切换标准后,彻底拔掉 40007。

### 5.2 量化切换标准(四条同时满足才撤 40007)

连续 **7~14 天**,线上大输入请求(≥5000 字符):

- 僵尸率 < 0.1%
- 流中断率 < 0.1%
- P99 成功延迟无恶化
- nv_gw 自恢复成功率 > 99%

## 6. 撤 40007 的本质(关键判断)

> **撤掉 40007 不是删一个后端,而是把 fallback 的恢复职责从"cc4101 适配层切后端"
> 下沉到"nv_gw 内部多 key 自愈":多 key/多通道重试、peek 判活、熔断降级、请求重放。
> 上层只看到一个稳定的 nv_gw 入口。**

撤 40007 后,cc4101 不再有"切到 ms_gw"这个动作,nv_gw 内部自己用多 key 重试 +
peek 判活 + 熔断把失败消化掉,对 cc2 呈现为一个永不暴露内部异常的稳定入口。

## 7. 第一步代码改造:nv_gw peek 内部换 key 重试

> 这是撤 40007 的前置代码改造:让 nv_gw 内部具备自愈能力,**本轮不撤 40007**
> (ms_gw 保留作二线)。

### 7.1 ChatGPT 确认的设计原则

1. **commit point 边界(最关键)**:peek barrier = SSE transaction commit barrier。
   边界不是"有没有收到上游 200",而是"**是否已向下游发送协议不可撤销事件
   (message_start)**"。
   - peek 窗口内(message_start 未 commit):可安全丢弃当前上游流、换下一个 key、
     重新发起完整请求。
   - peek 窗口后(message_start 已 commit):SSE 会话不可回滚,只能 graceful end。
   - **本次改造完全落在 peek 窗口内 → 技术安全可行。**
2. **peek 已读 chunk 丢弃安全**:前提是已 peek 的 chunk 尚未提交给下游,且新 key 流
   会从完整内容重新发送,丢弃不会造成下游可见的数据缺口。当前代码在 peek 健康分支
   才 feed converter + 存 prebuffer,peek 软挂分支没 feed,丢弃零成本。
3. **时间预算**:T 按下游可接受首字节延迟预算倒推,重试次数宁少而快(限 2~3 个 key),
   不线性耗尽 5T 把 SLA 打穿。
4. **实现方式**:独立 peek-retry 子循环,不复用 execute_request 全量轮转(避免污染
   RR counter、扩大延迟、污染 key 状态)。
5. **跨机 peer-fallback**(HM1↔HM2,NVU_PEER_FALLBACK_URL):若仍提升可用性就保留,
   否则随 40007 一起撤,避免无效复杂度。

### 7.2 改造点(精确到文件/行)

仅改 **HM2** `/opt/cc-infra/proxy/nv-gw/gateway/handlers.py`
`_stream_openai_to_anth` 的 peek 软挂分支(L1055 附近,`_peek_content_seen=False`
的 else 分支)。

- **现状**:peek 软挂 → `conn.close()` → `_ms_fallback_request(...)` 切外部 ms_gw →
  swap resp/conn → 进主循环。兜底(L1146):ms 也失败 → `send_response(200)` +
  api_error SSE(CC 重试)。
- **改造**:在 `conn.close()` 后、`_ms_fallback_request` **之前**,插入"内部 peek-retry
  换 key"子循环;只有内部重试也失败时,才落到 ms_gw(本轮保留)或 graceful end。

```python
_internal_keys_left = int(os.environ.get("NVU_PEEK_RETRY_KEYS", "2"))  # 限 1-2
_internal_rescued = False
_next_k = (_peek_nv_key(mapped_model_pre_fallback) + 1) % NVU_NUM_KEYS  # 跳过软挂 key
while _internal_keys_left > 0 and not _internal_rescued:
    _internal_keys_left -= 1
    _r = _peek_retry_next_key(oai_body, mapped_model_pre_fallback, ...,
                              start_key_idx=_next_k)
    if _r and _r.success and _r.resp is not None:
        _new_peek_ok = _do_peek(_r.resp, _r.conn, _fb_s, ...)  # 重新 peek 新 key
        if _new_peek_ok:
            resp, conn = _r.resp, _r.conn
            _peek_swapped = True; _internal_rescued = True
            break
        else:  # 新 key 也软挂
            try: _r.conn.close()
            except: pass
            big_input_breaker.record_big_input_failure(...)  # 同现有联动
    _next_k = (_next_k + 1) % NVU_NUM_KEYS
if _internal_rescued:
    cap_origin = time.time(); ...  # 复用现有 ms-swap 成功分支的 reset
else:
    _ok, _ms_r = _ms_fallback_request(...)  # 现有 ms_gw 二线, 原样保留
    ...
```

### 7.3 新增组件

- **`_peek_retry_next_key`**(upstream.py,新写):指定起始 key,只试 1 个 key,返回
  `UpstreamResult`。不 advance `_next_nv_key`(避免污染 RR),用显式 `start_key_idx`。
  复用 `_build_pexec_body` + `func_health.select_healthy_function` + 单 key pexec 建连
  (从 `_try_tier_keys` 抽出单 key 段)。
- **`_do_peek(resp, conn, fb_s)`**(handlers.py,抽出):把现有 L990-1130 peek while
  循环抽成独立方法,供主路径和 retry 子循环共用。返回 `(ok, prebuffer, prefed, ttfb_ms)`。

### 7.4 新增 env 开关(config.py)

```python
NVU_PEEK_RETRY_KEYS = int(os.environ.get('NVU_PEEK_RETRY_KEYS', '2'))   # 内部换 key 次数, 0=禁用(等价现状走 ms_gw)
NVU_PEEK_RETRY_BUDGET_S = float(os.environ.get('NVU_PEEK_RETRY_BUDGET_S', '0'))  # 0=用 _fb_s 作单 key 上限
```

默认 `NVU_PEEK_RETRY_KEYS=2`。设 0 即回退现状,作回滚开关。

### 7.5 不改的部分

- peek **之后**的软挂(no_content_gap / total_deadline / 流中途 hang):维持现有
  break + graceful end(commit point 已过,不能换 key)。
- ms_gw fallback 开关(`NVU_MS_FALLBACK_ENABLED`):本轮保持现状(二线),内部
  peek-retry 耗尽才落 ms_gw。撤 40007 是后续轮(待 shadow 数据达标)。
- HM1 nv_gw:本轮不改(无 format/ 无 R1716 peek;铁律聚焦 HM2)。
- peer-fallback(HM1↔HM2):本轮不动(独立容灾,仍提升可用性)。

### 7.6 验证(铁律:改后必有验证)

1. **语法 + 重启**:`docker exec nv_gw cp .../handlers.py .../handlers.py.bak.R2224`,
   bind-mount 改 .py 后 `docker compose restart nv_gw`(非 up -d),`curl /health`。
2. **shadow 验证**:`NVU_PEEK_RETRY_KEYS=2` 上线,观察 `NV-PEEK-INTERNAL-RESCUE` 日志
   计数 + `NV-PEEK-PROBE SOFTFAIL` 里的 key/IP 分布;确认内部救援后不再落 ms_gw
  (`NV-PEEK-MS-OK` 计数下降)。
3. **DB 验证**:对比改造前后 6h 窗口 `nv_requests`:
   - 改造前:peek 软挂后 `peer_fallback_ms > 0`(走 ms_gw)的请求数;
   - 改造后:这些请求里有多少被 `NV-PEEK-INTERNAL-RESCUE` 救回(status=200,
     走 nv_gw 全程,无 peer_fallback_ms),多少仍落 ms_gw。
   - 目标:内部救援率 > 0 且无新增 mid-response 中断/499。
4. **回滚开关**:`NVU_PEEK_RETRY_KEYS=0` + restart 即回退现状,秒级回滚。

## 8. 四层防御框架(与 ChatGPT 的架构印证)

ChatGPT 最终判断:**在不能改 NVCF 后端前提下,peek barrier + graceful end +
breaker 已是网关侧最优三层防御,唯一第四思路是 request shaping(预分流降发生率)。**

```
request shaping  →  breaker  →  peek barrier  →  graceful end
(降低发生率)      (隔离坏状态) (拦截坏响应)     (保证可恢复)
```

NVForge 现状已覆盖全部四层,无遗漏:

| 层 | NVForge 实现 |
|---|---|
| request shaping | R1673 big_input breaker(input>250k 预分流到 ms_gw;R1715 发现真实 502 大头在 150-250k 段,待精化阈值) |
| breaker | R1719(引入)+ R1774(修掉"连续 N 次+成功重置"数学不收敛语义,改时间窗 deque) |
| peek barrier | R1716(`_stream_openai_to_anth` 循环前加 peek 首内容 chunk barrier,200 落 cc4101 前判健康,软挂切 fallback 重放续给 cc4101) |
| graceful end | R1771/R1820(oai_to_anth `finish()` 加 `flushed_content_chars`,zombie+有内容发 graceful end 而非 `event:error`) |

**结论:NVForge 方向正确,后续不是找新机制,而是把四层阈值/边界按数据精调 +
把恢复职责从"外部 ms_gw"收敛到"nv_gw 内部多 key 自愈"(第 7 节)。**

## 9. 并发竞速的排除(与 ChatGPT 讨论)

多 key 并发竞速(race):同时发 N 个 key,谁先返回首内容 chunk 且健康就用谁。
ChatGPT 结论:**得不偿失**——

- 必须把多副本流完全隐藏在 nv_gw 内部(不提前 flush message_start 给 agent),否则
  失败副本的 `message_start` 已 flush 撤不回,赢家切换时 agent 收到两个 `message_start`
  造成流错乱,比单路更难处理。
- 代价:NVCF GPU/token/带宽翻倍消耗(尤其大 input + thinking 成本极高),网关要维护
  多路 SSE 状态、取消未中请求、处理"赢家选晚"的额外延迟。
- 在 NVForge 5 key 共享配额 + 单后端 NVCF 下,并发竞速会放大 429/限流。

故不采用并发竞速,改用**串行 peek-retry**(第 7 节):peek 软挂后串行换下一个 key
重放,只在 peek 窗口内(未 commit)操作,代价可控。

## 10. 预测评分的排除(与 ChatGPT 讨论)

ChatGPT 列出的理想 ZombieRiskScore 特征:`input_tokens + conversation_depth +
tool_schema + thinking_budget + historical_failure_rate + backend_health`。

nv_gw 实际约束下只看单次 request 的 messages 数组:

- `conversation_depth` 拿不到完整历史(只有本次 messages);
- 实际可用只剩:**input 大小、thinking_budget、历史失败率、breaker 状态**。

**特征太稀疏,做不到真"预测",只能做粗筛**(如 input>250k 直接走 ms_gw 兜底)。
这正好印证 R1673 big_input breaker 的思路:不是预测,而是按 input 维度粗筛预分流。
不单独做预测评分模块。

## 11. 变更记录

| 日期 | 内容 |
|---|---|
| 2026-07-22 | 初版:与 ChatGPT 三轮讨论整合(僵尸架构 / 撤 40007 路径 / peek 内部换 key 设计)。第 7 节代码改造待实施。 |
