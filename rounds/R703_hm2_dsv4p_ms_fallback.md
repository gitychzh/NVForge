# R703: HM2 ms_gw 实现 dsv4p_ms + hermes fallback 链切换

> 日期: 2026-07-05
> 主机: HM2 (100.109.57.26, opc2_uname)
> 范围: 只 HM2。HM1 未动 (HM1 dsv4p_nv 走日本直连, 失败率低, 不急需 ms fallback)。

## 背景 (改前数据)

HM2 最近 6h `nv_requests` (dsv4p_nv):

| request_model | status=200 | status=502 | 失败率 |
|---|---|---|---|
| dsv4p_nv | 254 | 128 | 33.6% |
| glm5_2_nv | 227 | 13 | 5.4% |
| kimi_nv | 21 | 3 | 12.5% |

dsv4p_nv 502 集中在 `IntegrateTimeout` (nv_tier_attempts 显示 integrate_deepseek-ai/deepseek-v4-pro_k1..k5
61-65s 超时)。R696 的 `NV_INTEGRATE_MODELS=""` 修复在 HM2 仍有 integrate 残留 (见 [[dsv4p-nv-502-root-cause-r696]]),
dsv4p_nv 502 率 33.6% = hermes 主链 1/3 请求失败 → 需要 ms_gw 同模型 fallback 兜底。

旧 hermes fallback 链: `dsv4p_nv → glm5_2_ms` (跨模型 fallback, 语义错位, 且 hermes 实测
`fallback_actually_attempted: False` — 旧链路从未真正触发过)。

## 目标

1. ms_gw 实现 `dsv4p_ms` (DeepSeek V4 Pro via ModelScope, 7key×10variant 2D 轮换)。
2. hermes fallback 链改: `dsv4p_nv → dsv4p_ms` (同模型 fallback, 语义对齐)。
3. 端到端验证: nv_gw 5 key 全挂 → hermes 切到 dsv4p_ms 成功响应。

## ModelScope dsv4p 变体探测 (改前数据)

`/v1/models` 列表: `deepseek-ai/DeepSeek-V3.2`, `deepseek-ai/DeepSeek-V4-Flash`, `deepseek-ai/DeepSeek-V4-Pro`。
标准 model_id = `deepseek-ai/DeepSeek-V4-Pro`。

实测 (HM2 MS_KEY1, 10 个大小写 typo 变体全部 HTTP 200):

```
[deepseek-ai/DeepSeek-V4-Pro] -> OK     # canonical
[deepseek-ai/Deepseek-V4-Pro] -> OK
[deepseek-ai/deepseek-v4-pro] -> OK
[deepseek-ai/DeepSeek-v4-pro] -> OK
[deepseek-ai/DEEPSEEK-V4-PRO] -> OK
[deepseek-ai/Deepseek-v4-Pro] -> OK
[deepseek-ai/deepseek-V4-Pro] -> OK
[deepseek-ai/DeepSeek-V4-pro] -> OK
[deepseek-ai/deepseek-v4-Pro] -> OK
[deepseek-ai/DEEPSEEK-v4-pro] -> OK
```

ModelScope 对 model_id 大小写不敏感路由 — 与 GLM-5.2 同样具备"每个 typo 变体独立 200/id/day 配额"
行为 (GLM-5.2 的 10 变体即基于此 quirk, R466 起验证)。dsv4p 复用同样模式: 10 variant × 7 key = 70 槽位。

## 改动

### 1. `/opt/cc-infra/proxy/ms-gw/gateway/config.py` (HM2, bind-mount)

备份: `config.py.bak.R703` (md5 与原文件一致)。

- 新增 `DSV4P_VARIANT_IDS` 列表 (10 个大小写变体, 上文)。
- 新增 `DSV4P_NUM_VARIANTS` (env 可覆盖, 默认 10)。
- `MODEL_REGISTRY["dsv4p_ms"]`: `variants` 从 `[]` 填为 `DSV4P_VARIANT_IDS`, 去 `_disabled`,
  name 从 "NOT IMPLEMENTED" 改为 "DeepSeek V4 Pro (ModelScope via ms_gw, 7key×10variant)"。
- `kimi_ms` 保持 placeholder 不动。
- `upstream.py` / `handlers.py` 未改 — 2D 轮换 / sanitize / 错误处理全 model-agnostic, 现成可用。

### 2. `~/.hermes/config.yaml` (HM2)

备份: `config.yaml.bak.R703`。

- `fallback_providers[0].model`: `glm5_2_ms` → `dsv4p_ms` (其余字段 base_url/api_key/context_length 不变)。
- 顶层 keys 与 `_config_version: 27` 保持一致 (python yaml round-trip 验证)。
- compression 段的 `glm5_2_ms` 保留 (辅助任务, 非 fallback)。
- hermes-gateway.service 重启 (`systemctl --user restart`, 旧 PID 2495620 → 新 PID 2610266)
  让新 fallback 生效 (config 启动时一次性读取)。

## 验证 (改后)

### ms_gw 侧

`/health`: `num_variants=10, models=[glm5_2_ms, dsv4p_ms, kimi_ms]`。
`/v1/models`: `dsv4p_ms disabled=False`。
端到端 chat (non-stream, max_tokens=200): `content='hello' reasoning_len=155 finish=stop`。
端到端 chat (stream): `data: {...delta...reasoning_content...}` 正常流式。
DB `ms_requests` 4 条 dsv4p_ms 全 `status=ok`, variant_idx=0, key_idx 0→1→2→3 递增 (2D 轮换工作)。

### hermes fallback 链

`hermes fallback list`:
```
Primary:   dsv4p_nv  (via nv_gw)
Fallback chain (1 entry):
  1. dsv4p_ms  (via custom)  [http://127.0.0.1:40007/v1]
```

### 端到端 fallback 触发 (受控测试)

临时把 hermes `providers.nv_gw.base_url` 端口 40006→40060 (不存在的端口, 模拟 5 key 全挂/
primary 不可达), `systemctl --user reload` (USR1 热重载), 发:
`hermes chat -q "Reply with exactly one word: ok" --max-turns 1 -Q`

结果: 返回 `ok` (主链 connection refused → hermes 自动 fallback 到 dsv4p_ms)。
DB 新增 `ms_requests` 记录: `ts=19:14:03 agent_model=dsv4p_ms backend_model=deepseek-ai/DeepSeek-V4-Pro
variant_idx=0 key_idx=4 status=ok duration_ms=2053`。
(key_idx 从验证前的 3 递增到 4, 证明是这次 fallback 走的 ms_gw)

测试后立即恢复 base_url 40060→40006 + reload, `hermes fallback list` 确认 primary 恢复 nv_gw:40006。

## hermes fallback 机制说明 (文档确认)

<https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers>

- 触发条件: 429 (rate-limit, 重试耗尽后) / 5xx (重试耗尽后) / 401/403/404 (立即, 无重试) /
  malformed empty response (反复) / connection drop。
- nv_gw 的 `all_tiers_exhausted` 表现为 HTTP 502 → 命中 5xx 触发条件 → hermes 重试耗尽后切 dsv4p_ms。
- fallback 是 turn-scoped: 每条新 user message 从 primary 重新开始, 单 turn 内最多 fallback 一次。
- hermes 原生支持, 无需额外组件; `fallback_providers` 配置即生效。

## 未做 / 后续

- HM1 未部署 (HM1 dsv4p_nv 日本直连失败率低, 不急需; 如需对称, 复制 config.py 改动 +
  hermes config 同步即可, 改动量相同)。
- nv_gw 的 dsv4p_nv integrate 残留 (R696 修复在 HM2 未完全生效) 不在 R703 范围 — fallback 兜底
  正是为了应对这条链路的持续失败, 不替 nv_gw 修 integrate。
- 自然 fallback 观测: 重启后 1h 内 dsv4p_nv 502 的请求 hermes 应自动切 dsv4p_ms, 后续查
  `ms_requests where agent_model='dsv4p_ms'` 应有自然增长 (非测试请求)。

## 关联

- [[dsv4p-nv-502-root-cause-r696]] — dsv4p_nv 502 真因 (integrate 挂死 + stream_options/thinking 副作用)
- rounds/R466 — GLM-5.2 的 10 变体 typo quirk 首次发现 (dsv4p 复用同模式)
