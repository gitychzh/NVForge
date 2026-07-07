# R813: HM2 glm5_2_nv 停 inject thinking + ms_gw 流转发 [DONE] 后主动关连接

> 承接 R797-R812 (含 R797 fast-fail/peer-skip, R810 400-cycle). 用户报远程 5 agent 模型链路 bug, 排查修复.
> 铁律: 改前有数据 (NVCF 直连实测 + DB + ms_gw 流时序), 改后有验证 (端到端 + 日志).
> 角色: HM2-only 部署; config.py/handlers.py 是共享源码, 仓库同步供 HM1.

## 现象 (2026-07-07, 远程 HM2 实测)

5 agent 容器各 primary→nv_gw + fallback→ms_gw:

| agent | primary | 改前实测 | 链路状态 |
|---|---|---|---|
| cc4101 | glm5_2_nv | 90s timeout, fallback dsv4p_ms/glm5_2_ms 流再卡 | ❌ 卡死 |
| cx4102 | glm5_2_nv | 116.6s (近 120s 超时) | ⚠️ 极慢 |
| opclaw4103 | glm5_2_nv | 已 fallback glm5_2_ms (primary 超时) | ⚠️ 降级 |
| hm4104 | dsv4p_nv | 200/5.8s | ✅ |
| oc4105 | kimi_nv | 200/2.2s | ✅ |

3 个用 glm5_2_nv 的 agent 全坏 → 根因在 glm5_2_nv tier.

## 改前数据 (铁律)

### DB (nv_requests, 60min 窗口, HM2)

| tier_model | status | count |
|---|---|---|
| glm5_2_nv | 200 | 4 |
| glm5_2_nv | 502 (all_tiers_exhausted) | 45 |
| dsv4p_nv | 200 | 102 |
| dsv4p_nv | 502 | 1 |
| kimi_nv | 200 | 3 |

glm5_2_nv 60min SR = 4/49 = **8.2%**.

### ★NVCF 直连实测★ (绕过 nv_gw, function 3b9748d8 ai-glm-5_2)

直接 `curl https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/3b9748d8...`:

| 请求 | enable_thinking | 结果 | 耗时 |
|---|---|---|---|
| `1+1=?` | true | 504 | 62.5s |
| `1+1=?` | false | 200 "1+1=2" | 1.86s |
| `2+2?` ×5 连发 | false | 5/5 200 | 1.4–3.4s |
| `hi` | true | 504 | 62s |

**关键**: thinking 路径 504 退化, 非 thinking 路径 5/5 健康 <4s. → 强制 inject enable_thinking=True 是把请求打坏掉的路径.

(注: 排查后期 NVCF 把 3b9748d8 标 DEGRADED, 全路径 400. 这是 NVCF 周期上游故障, R811/R812 已记录. 本轮修的是 thinking-inject 这个网关侧可修的根因 — NVCF 恢复 ACTIVE 后, 关 inject 让 glm5_2_nv 走稳的普通模式.)

### ms_gw 流时序实测 (cc4101 卡死根因)

cc4101 日志: primary 502 (0.7s) → fallback glm5_2_ms connected (4-37s) → 之后静默卡死无日志.
ms_gw 日志: `MS-STREAM-CYCLE ... cycle (stream_no_data_lines)` 连续 5+ variant, 然后 `MS-OK-STREAM first=5674B`.

curl ms_gw glm5_2_ms stream 实测:
- ttfb 1.7–17.7s, total **30s 超时未自然结束** (curl -m 30).
- 但响应体含 `data: [DONE]` + finish_reason — 即 ModelScope 在 [DONE] 后不关连接.

ms_gw `_relay_stream` (handlers.py:277) `while True: chunk=resp.read(8192); if not chunk: break` — 等上游 EOF 才 break. ModelScope 在 [DONE] 后保持连接 → read 阻塞到 UPSTREAM_TIMEOUT=300s. 下游 (cc4101 collect_stream_to_anth) 虽在 [DONE] 设 done=True, 但 [DONE] 到达前卡在 read 等 chunk.

## 根因

R1 [gateway]: `config.py` glm5_2_nv `inject: {"chat_template_kwargs":{"enable_thinking":True}}` 强制思考, NVCF 3b9748d8 thinking 路径 504 退化 → glm5_2_nv tier 92% 失败. (对照: 非 thinking 5/5 200.)
R2 [ms_gw]: `_relay_stream` 转发 `data: [DONE]` 后不 break, 等上游 EOF; ModelScope 上游 [DONE] 后不关连接 → 下游 stream 消费者 (cc4101 collect) 卡到 UPSTREAM_TIMEOUT. (注: cc4101 主卡点还有 ModelScope 流本身慢/无 data lines, 但 [DONE] 后关连接是正确 SSE 行为, 消除尾部 hang.)

## 修复方案 (HM2 部署; 共享源码仓库同步供 HM1)

### 改动 1: config.py glm5_2_nv inject 改空 (修 R1)

`/opt/cc-infra/proxy/nv-gw/gateway/config.py` glm5_2_nv 块:

```python
"strip_params": ["thinking_budget", "reasoning_effort", "thinking"],
# R797: NVCF 3b9748d8 thinking 路径 504 退化 (2026-07-07 直连实测 5/5 false=200, true=504).
# 停 inject enable_thinking, 走普通模式 (同 dsv4p_nv 策略). 普通模式 5/5 200 <4s.
# 思考输出 (reasoning_content) 丧失 — 但 thinking 路径已 504 不可用, 保 content 优于全失.
# NVCF 恢复 thinking 后可改回 (env 无 inject 覆盖, 改此行 + restart).
"inject": {},
```

strip_params 不变. 影响: 仅 glm5_2_nv. dsv4p_nv/kimi_nv 不变.

### 改动 2: ms_gw handlers.py _relay_stream [DONE] 后 break (修 R2)

`/opt/cc-infra/proxy/ms-gw/gateway/handlers.py` `_relay_stream` 循环:

```python
# R797b: ModelScope 上游在 data: [DONE] 后常不关连接, resp.read(8192) 会阻塞到
# UPSTREAM_TIMEOUT(300s). 转发完 [DONE] 后主动 break, 让下游 (cc4101 collect_stream)
# 立即收尾, 不再等上游 EOF.
done_seen = False
while not done_seen:
    try:
        chunk = resp.read(8192)
    except (http.client.IncompleteRead, http.client.RemoteDisconnected,
            ConnectionResetError, socket.timeout) as e:
        _log("MS-STREAM-EOF", f"req={request_id} stream ended: {type(e).__name__}")
        break
    if not chunk:
        break
    self.wfile.write(chunk)
    self.wfile.flush()
    bytes_relayed += len(chunk)
    if b"[DONE]" in chunk:
        _log("MS-STREAM-DONE", f"req={request_id} forwarded [DONE], closing client stream after {bytes_relayed}b")
        done_seen = True
```

### 不改的项
- R797 的 per-tier budget / peer-fb skip (已部署, 保留).
- R810 的 should_cycle 400 (HM2 未部署 — HM2 是 single-tier R753, 400 立即 502 由 agent fallback 兜底, 无需 cycle; R810 是 HM1→部署 HM1. HM2 可后需补, 但非本 bug 修复必要).
- cc4101 stream.py (always-stream 架构不变; R2 修后 [DONE] 即关, cc4101 收尾).
- HM1: 同 bug, 远程 CC pull 后部署 (config.py 第 106 行 inject 改空; ms_gw handlers 同改).

## 实施步骤 (HM2, 已执行)

1. 备份: `config.py.bak.R797` (HM2 nv_gw), `handlers.py.bak.R797b` (HM2 ms_gw).
2. 改 config.py glm5_2_nv inject 行 (python 精确替换).
3. 改 ms_gw handlers.py _relay_stream 循环 (python 精确替换).
4. `docker restart nv_gw && docker restart ms_gw` (均 bind-mount, 无需 build).
5. 验证.

## 验证 (铁律: 改后有验证)

### V1: config 生效 (无 INJECT 日志)
`docker logs nv_gw --since 1m | grep INJECT-THINKING` — glm5_2_nv 请求后无 injected chat_template_kwargs. ✅

### V2: ms_gw [DONE] break 生效
`docker logs ms_gw --since 2m | grep MS-STREAM-DONE` — 出现 `forwarded [DONE], closing client stream`. ✅

### V3: nv_gw 直连 glm5_2_nv
NVCF 3b9748d8 当前 DEGRADED (排查期 NVCF 周期故障), 直连返回 400/502 (NVCF 上游, 非本修复范围). 修复价值在 NVCF 恢复 ACTIVE 后: 普通 (非 thinking) 路径 5/5 200 <4s (改前 thinking 路径 100% 504).

### V4: 5 agent 端到端 (改后, NVCF 全函数 DEGRADED 期)
- cx4102 glm5_2_nv → 200/22s (fallback glm5_2_ms) ✅ (改前 116s).
- opclaw4103 glm5_2_nv → 200/12s (fallback glm5_2_ms) ✅.
- oc4105 kimi_nv → 200/2.4s ✅.
- hm4104 dsv4p_nv → 503 (dsv4p_nv 慢 17.9s 超 hm4104 PROXY_TIMEOUT, dsv4p_ms fallback 同时退化) ⚠️ — 上游慢, 非本修复.
- cc4101 glm5_2_nv → 仍卡 ~50s (ms_gw glm5_2_ms 流慢 + cycle variant 耗时) ⚠️ — ModelScope 上游慢, [DONE] break 修了尾部 hang 但流本身慢非网关可修.

### V5: 健康检查
`curl nv_gw/health` ok; `curl ms_gw/health` ok; `docker ps` 全 Up. ✅

## 局限与后续

- 改造期 NVCF 3b9748d8 (glm5_2) 与 74f02205 (dsv4p) 交替 DEGRADING/慢, ModelScope glm5_2_ms 流 no-data-lines 频发 — 全局 glm-5.2/dsv4p 上游退化, R811/R812 已记为 "零配置可修" 的 NOP. 本轮修的是网关侧两个确定 bug (thinking-inject, stream-DONE-hang), 上游恢复后立即见效.
- cc4101 卡死的残余成分 (ms_gw 流慢 + variant cycle) 是 ModelScope 服务端问题, 待上游恢复.
- HM2 应补 R810 的 should_cycle 400 (后续轮次, 非本 bug 必要 — HM2 single-tier R753 下 400 立即 502, agent fallback 兜底).

## 回滚

- config: `cp config.py.bak.R797 config.py && docker restart nv_gw`
- ms_gw: `cp handlers.py.bak.R797b handlers.py && docker restart ms_gw`

## 提交

- 源码快照: `deploy_artifacts/R813_glm52_empty_inject_ms_done/{config.py,handlers_ms.py}`
- round: `rounds/R813_hm2_glm52_empty_inject_ms_done.md`
- git commit + push (经 mihomo 7891, ssh.github.com:443)
- push 前 `git pull --rebase origin main`

## 跨机协作备注

- R813 是共享源码改动 (config.py + ms_gw handlers.py). HM2 已部署 + 仓库同步. HM1 同 bug:
  - nv_gw config.py glm5_2_nv inject 改空 (同第 106 行).
  - ms_gw handlers.py _relay_stream 加 [DONE] break (同改动 2).
- 远程 CC 若 pull 到本 round: HM1 同步即可, 勿回退. R797 的 inject 保留决策 (HM1) 已被本 R813 覆盖 — 实测 thinking 路径 504 不可用, 停 inject 是数据驱动结论.
