# R1248 cc2 — 4 容器 fallback 统一切到 ms_gw(dsv4f0731_ms), 与 NVCF 账号解耦

- **日期**: 2026-08-10
- **类型**: 内容改动 (fallback 通道切换)
- **主机**: HM2 (100.109.57.26)
- **用户决策**: 用户主动提出 — 原 fallback(glm5_2_nv@nv_gw:40006) 与 primary(dsv4f0731_nv@40666) 同在 NVCF 同一批 key/账号，
  账号级 429 时 fallback 被同款故障打败 (非真正备用)。切到 ms_gw(dsv4f0731_ms@40007, modelscope 7key 10variant) 实现跨供应商真备用。

## 背景: 为什么必须切 (数据锚点, R1247 之后的独立发现)

**问题**: primary 与 fallback 都挂同一个 NVCF 账号/同一批 5 个 key (k0~k4)。
查 `nv_requests.key_cycle_429s` (24h): dsv4f0731_nv 1110 次内置 429, glm5_2_nv 180 次。
两模型在同一 5 key 上走同一 `nvcf_pexec`。故障同源 = fallback 不是真备用。

**联调证据 (24h 小时级)**:
- dsv4f0731 429 高峰时段 (08-09 09~11 点 92/122/109; 21 点 63) **正是** glm5_2 429 抬高时段 (14/28/10; 28)。
- dsv4f0731 429 低谷时段 (16~20 点 22~38) glm5_2 429 全为 0。
- **关键不对称**: 无任何小时 glm5_2 有 429 而 dsv4f0731 没有 (`g_without_d=0`)。
- 秒级: 08:30:19 dsv4f0731 502 + 08:30:44/31:03 glm5_2 502, 同一波 NVCF 抖动两模型同受。

**结论**: NVCF 限流是账号级共享配额, 两模型同 key 同源。原 fallback 无法在 primary 被限流时兜底。

## 目标通道健康实测 (ms_gw:40007, dsv4f0731_ms)

- `ms_gw` health: role=ms_uni, num_keys=7, num_variants=10, models 含 `dsv4f0731_ms`, rr_counter `ms_dsv4f0731=2212`。
- `ms_requests.status='ok'` 24h: **dsv4f0731_ms SR 98.8%** (83/84), avg ~35s; glm5_2_ms SR 80% (12/15)。
  (注: 正确字段是 `ms_requests.status='ok'`, 非 `resp_status` — resp_status 对 stream 不填充, 勿误读为 0%。)
- 端到端 curl 实测 (R1248): `/v1/messages` (Anthropic, cc4101 路径) HTTP 200 ttfb 1.3s;
  `/v1/chat/completions` (OpenAI, adapter 路径) HTTP 200 ttfb 1.4s。均正确路由 model=dsv4f0731_ms。
- auth: `MSU_GATEWAY_API_KEY=ms-gw-token` (compose line 29 实值, 非密文; 无 token/错 token 均 401)。

## 改动 (compose env, 4 容器)

**切换目标**: `FALLBACK_URL=http://ms_gw:40007/...` + `FALLBACK_MODEL=dsv4f0731_ms` + auth token `ms-gw-token`。

| 容器 | 变量 | 原值 | 新值 |
|---|---|---|---|
| cc4101 | FALLBACK_UPSTREAM_URL | nv_gw:40006/v1/messages | ms_gw:40007/v1/messages |
| cc4101 | FALLBACK_UPSTREAM_TOKEN | nv-gw-token | ms-gw-token |
| cc4101 | FALLBACK_UPSTREAM_MODEL | glm5_2_nv | dsv4f0731_ms |
| hm4104 | FALLBACK_URL | nv_gw:40006/v1 | ms_gw:40007/v1 |
| hm4104 | FALLBACK_MODEL | glm5_2_nv | dsv4f0731_ms |
| hm4104 | MS_GW_API_KEY | nv-gw-token | ms-gw-token |
| opclaw4103 | FALLBACK_URL | nv_gw:40006/v1 | ms_gw:40007/v1 |
| opclaw4103 | FALLBACK_MODEL | glm5_2_nv | dsv4f0731_ms |
| opclaw4103 | MS_GW_API_KEY | nv-gw-token | ms-gw-token |
| oc4105 | FALLBACK_URL | nv_gw:40006/v1 | ms_gw:40007/v1 |
| oc4105 | FALLBACK_MODEL | glm5_2_nv | dsv4f0731_ms |
| oc4105 | FALLBACK_API_KEY | nv-gw-token | ms-gw-token |

**认证变量注意 (cc-adapter 源码 config.py:70)**: `FALLBACK_API_KEY = os.environ.get("FALLBACK_API_KEY", MS_GW_API_KEY)`。
cc-adapter (hm4104/opclaw4103/oc4105) fallback 走 `_post_upstream(FALLBACK_URL, FALLBACK_MODEL, FALLBACK_API_KEY)`。
- hm4104/opclaw4103 未显式设 FALLBACK_API_KEY → 回落 MS_GW_API_KEY (故改 MS_GW_API_KEY)。
- oc4105 显式设 FALLBACK_API_KEY=nv-gw-token → 覆盖 MS_GW_API_KEY (故改 FALLBACK_API_KEY, MS_GW_API_KEY 已是 ms-gw-token 不变)。
- cc4101 走 routing.py:161 用 FALLBACK_UPSTREAM_TOKEN (默认 ms-gw-token, 现显式 nv-gw-token 需改回)。

**不碰**: cx4102 (FALLBACK_URL=none 已禁用, MS_GW_API_KEY 本就 ms-gw-token); ms_gw/nv_gw/dsvf40666 自身; HM1。

## 验证 (已通过部分)

| 项 | 结果 |
|---|---|
| compose config | VALID |
| ms_gw dsv4f0731_ms 端到端 | /v1/messages 200 (1.3s) + /v1/chat/completions 200 (1.4s) |
| docker compose up -d 4 容器 | Recreated + Started |
| 4 容器 health | 全 HTTP 200, fallback_url=http://ms_gw:40007/v1 |
| 4 容器 env 生效 | 全确认 (见上表新值) |
| 残留 nv_gw:40006 fallback | 无 (仅剩 cc4101 primary 注释 + cx4102 PRIMARY_URL, 均无关) |

## 待验证 (用户手动密集请求后, 我拉 DB 复核)

- [ ] 用户密集请求期间, primary(40666 dsv4f0731) 失败时, fallback 是否落到 ms_gw 的 dsv4f0731
      (查 `nv_requests.fallback_occurred=true` 且 `fallback_to`/`fallback_tiers_used` 含 ms_gw / dsv4f0731_ms)。
- [ ] `ms_requests` 新增 dsv4f0731 请求的 caller 是否来自 4 容器 (cc4101/hm4104/opclaw4103/oc4105 而非仅 curl)。
- [ ] fallback 触发率 + 各容器 SR 无恶化。

## 备份
- docker-compose.yml.bak.R1248-switch-fallback-ms

## 下一步
- 等用户密集请求 → 拉 DB 确认 fallback 真正生效 (见待验证)。
- 确认后: 观察 4 容器 fallback 触发率 (应 <5%) 与 ms_gw dsv4f0731 SR 稳定。
- 若 fallback 触发频繁且 ms 慢 (avg 35s), 评估是否需调 FALLBACK_TIMEOUT 预算。