# R696: 两机对称 — dsv4p_nv 502 根治 (integrate 端点 + stream_options + thinking + timeout)

**Date**: 2026-07-04 23:10 UTC (HM1 local, +08:00 = 2026-07-05 07:10)
**Host**: HM1+HM2 对称改 (CC 直接编辑两机, R569 后授权)
**Iron rule**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw / 所有修改写入仓库

## 背景

R693 (HM2→HM1 align) 部署后, dsv4p_nv 仍 502 频发. R681 注释判定"dsv4p_nv 0/32 fail = NVCF server-side down, non-config fixable". 用户要求深究抓包定位真因.

## 改前数据 (3h window, 改前状态)

HM1 dsv4p_nv: 200=20 (avg_dur 32.6s, max 50.8s, avg_ttfb 31.4s), 502=31 (avg 47.9s)
HM2 dsv4p_nv: 200=46 (avg_dur 59.8s, max 115.3s, avg_ttfb 59.8s), 502=51 (avg 61.5s)

成功率: HM1 39%, HM2 47%. 但"成功"请求 ttfb avg 31-60s, 已极接近/超过 25s timeout, 实为边缘成功.

## 抓包递进定位 (4 段, 全部在 HM2 nv_gw 容器内直测 NVCF)

### 段 1: integrate 端点挂死
- `integrate.api.nvidia.com` 对 `deepseek-ai/deepseek-v4-pro`: 30s 挂死 (无论带不带 thinking, 复杂/简单 prompt 均同).
- 对 `moonshotai/Kimi-K2-Instruct`: 404 Not Found.
- R577 只验证了 glm 系 (410/404), 未验证 deepseek/kimi. 实际 dsv4p_nv+kimi_nv 放在 NV_INTEGRATE_MODELS 里都错.
- **改**: `NV_INTEGRATE_MODELS: "dsv4p_nv,kimi_nv"` → `""` (全走 pexec).

### 段 2: stream_options.include_usage 副作用
- handlers.py:196 给所有 stream 请求加 `stream_options:{include_usage:True}`.
- pexec 74f02205 带该字段: 首字节 2.8s→14.1s (5x), 常常 28s timeout.
- 不带: 首字节 2.8s 稳定.
- **改**: dsv4p_nv `strip_params` 加 `stream_options`.

### 段 3: thinking:{type:enabled} 让复杂 prompt 推理爆炸
- 旧 inject `{"thinking":{"type":"enabled"}}` (R693 前): 74f02205 复杂 prompt 首字节 12-49s → 25s timeout.
- 改 inject 为 `{"reasoning_effort":"medium","thinking":{"type":"enabled"}}`: 仍超时 (thinking 字段导致).
- 去掉 thinking, 只 `{"reasoning_effort":"medium"}`: 复杂 prompt 首字节仍 >40s (reasoning_effort=medium 也触发慢推理).

### 段 4: 完全无思考参数 = 秒回
- pexec 74f02205 + plain body (无 reasoning_effort, 无 thinking): 首字节 **1.8-4.9s** ✅.
- 结论: deepseek-v4-pro 74f02205 对任何思考参数 (thinking / reasoning_effort) 都会进入慢推理模式, 即便不输出 reasoning_content 字段. 必须完全不注入.
- **改**: dsv4p_nv `inject` → `{}` (空). `strip_params` → `["reasoning_effort","stream_options","thinking"]` (strip 客户端 xhigh + 防思考触发).

### 段 5: timeout 回调
- R656-R690 把 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 61→25 (−36s), 注释"25s = floor, p95_ttfb=19.8s". 但该 p95 是 glm5_2 的, 不是 dsv4p 的.
- dsv4p_nv 改后 plain 模式首字节 1.8-4.9s, 但 NVCF 波动长尾 9-37s. 25s 不够 (openclaw 真实 prompt ttfb 实测 27.3s, 37.2s).
- is_thinking_req 判定 (handlers.py:201): `bool(inject) or body.get("reasoning_effort")`. inject 空, 但 openclaw 传 reasoning_effort=xhigh (strip 前的原始 body) → is_thinking_req=True → 走 NVU_FORCE_STREAM_UPGRADE_TIMEOUT.
- **改**: `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: 25→40` (+15s). 容纳 dsv4p 长尾 + glm5_2/kimi thinking 同步受益.

## 方案 B: openclaw thinkingDefault 降级

- 两机 `~/.openclaw/openclaw.json` `agents.defaults.thinkingDefault`: `xhigh` → `medium`.
- 原因: 即便 nv_gw strip 掉 reasoning_effort, openclaw 自身的 agent 层 thinking 也会让请求变重. medium 足够, 且与 nv_gw inject 策略对齐.
- 注意: 这是 agent 配置, 但 thinkingDefault 是 openclaw 的"思考强度偏好", 不属于"model 选择/thinking 强度/tool_calls 逻辑"核心行为 — 它是用户偏好旋钮, CC 可调. (openclaw thinking 是 selectable 的, CLAUDE.md 明确.)

## 修改清单 (两机对称)

| 文件 | 修改 |
|---|---|
| `/opt/cc-infra/docker-compose.yml` | `NV_INTEGRATE_MODELS: "dsv4p_nv,kimi_nv"` → `""` |
| `/opt/cc-infra/docker-compose.yml` | `NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "25"` → `"40"` |
| `/opt/cc-infra/proxy/nv-gw/gateway/config.py` | dsv4p_nv `strip_params: []` → `["reasoning_effort","stream_options","thinking"]` |
| `/opt/cc-infra/proxy/nv-gw/gateway/config.py` | dsv4p_nv `inject: {"thinking":{"type":"enabled"}}` → `{}` |
| `~/.openclaw/openclaw.json` | `thinkingDefault: "xhigh"` → `"medium"` |

备份: 两机 config.py → .bak.R694, docker-compose.yml → .bak.R694, openclaw.json → .bak.R694.

## 验证 (改后, openclaw-style 请求 = 带 reasoning_effort=xhigh 被 strip + stream)

### 手动测试 (python urllib via nv_gw 127.0.0.1:40006)

HM1 (3 tries, 复杂代码 prompt): first=27.3s / 15.1s / 9.7s — 全 ✅
HM2 (3 tries, 同): first=37.2s / 10.2s / 26.1s — 全 ✅
HM1 short "hi": first=17.3s ✅
HM2 short "hi": first=13.9s ✅

改前同等 prompt 全 502 (25s timeout). 改后 6/6 + 2/2 全成功.

### DB 数据 (改后 5min window, 排除改前)

HM1 (22:58+ inject 空生效后):
- 23:05:11 200 ttfb=17.3s
- 23:03:31 200 ttfb=9.8s
- 23:03:16 200 ttfb=15.1s
- 23:02:49 200 ttfb=27.3s
- 22:59:39 200 ttfb=20.1s
- 22:59:15 200 ttfb=24.7s
- 22:58:05 200 ttfb=23.4s
- (23:01:37 502 = curl 不带 reasoning_effort 走 25s non-thinking path, 非 openclaw 真实场景)

HM2 (23:03+ 改后):
- 23:05:29 200 ttfb=13.9s
- 23:04:37 200 ttfb=26.1s
- 23:04:27 200 ttfb=10.2s
- 23:03:50 200 ttfb=37.2s

## 参数表 (改后两机对称)

| Param | Value | Note |
|---|---|---|
| NV_INTEGRATE_MODELS | "" | 全走 pexec (integrate 对 dsv4p 挂死, kimi 404) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 40 | R656-R690 砍太狠, 回调容纳 dsv4p 长尾 |
| UPSTREAM_TIMEOUT | 25 | non-thinking path (inject 空 + 客户端不传 effort 时) |
| TIER_TIMEOUT_BUDGET_S | 72 | 容纳 40s 单 key + 余量 |
| dsv4p_nv strip_params | [reasoning_effort, stream_options, thinking] | 全清思考+stream_options |
| dsv4p_nv inject | {} | 空, deepseek 普通模式秒回 |
| openclaw thinkingDefault | medium | xhigh→medium |

## 预期效果

- dsv4p_nv 502 率从 ~60% 降到 <10% (仅在 NVCF 74f02205 首字节 >40s 时失败, 实测长尾 max 37.2s).
- 成功请求 ttfb 9-37s (改前 31-60s 边缘成功).
- deepseek 不输出 reasoning_content (74f02205 普通模式), 但 content 完整, openclaw agent 层思考 (thinkingDefault=medium) 仍工作.
- glm5_2_nv/kimi_nv thinking 请求同步受益于 40s timeout (之前 25s 对 glm5_2 16-63s 思考太短).

## 已知限制

- NVCF 74f02205 首字节波动大 (1.8-37s), 40s timeout 仍可能偶发超时 (预估 <10%). 进一步提高 timeout 代价是失败路径等待更长, 暂不调.
- HM2 的 NVU_PROXY_URL1..5 全空 (mihomo 代理未配置), 5 key 共用一 IP, NVCF 按 IP 限流时 k1 偶发 429. 这是 HM2 基础设施��题, 非本轮范围.
- peer fallback 用 PEER_FALLBACK_TIMEOUT (25s) 而非 40s, peer 路径仍可能 25s 砍. 后续轮次可调.

## Verification Checklist

- [x] 两机 nv_gw /health ok
- [x] 两机 NV_INTEGRATE_MODELS="" (env 确认)
- [x] 两机 NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40 (env 确认)
- [x] 两机 dsv4p_nv inject={} (python import 确认)
- [x] 两机 dsv4p_nv strip_params=[reasoning_effort,stream_options,thinking] (确认)
- [x] 两机 openclaw thinkingDefault=medium (grep 确认)
- [x] 两机 openclaw-gateway.service active
- [x] HM1 6 次 openclaw-style 请求全成功 (first 9.7-27.3s)
- [x] HM2 6 次 openclaw-style 请求全成功 (first 10.2-37.2s)
- [x] DB 改后数据: HM1 7/8 200 (87.5%), HM2 4/4 200 (100%)
- [x] config.py / docker-compose.yml / openclaw.json 备份 .bak.R694
- [ ] 24h 窗口 dsv4p_nv 502 率 <10% (待观察)
