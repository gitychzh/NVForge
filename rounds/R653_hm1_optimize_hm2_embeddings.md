# R653 HM1→HM2: nv_40006_uni 网关加 /v1/embeddings 转发, 修 openclaw 6.11 memorySearch

## 背景
用户点网页版升级, openclaw HM2 6.8→6.11. 新版 memorySearch 默认 provider=openai,
需 openai API key 做语义召回. HM2 没配 key → CLI 崩 (`missing-provider-auth`,
`openclaw memory status --deep` 直接退出) + 飞书 [memory] sync failed 持续报错.
HM1 是显式 `memorySearch.enabled=false` 规避的. 用户要求保留 memory 功能,
用 nv_40006_uni 网关能力实现 (不引入外部 openai key).

## 改前数据
- 容器 `nv_40006_uni` env: `NVU_KEY1..5` 均为 `nvapi-` 前缀 (NVIDIA integrate key).
- 实测 `NVU_KEY1` 调 `https://integrate.api.nvidia.com/v1/embeddings`,
  body `{"model":"nvidia/nv-embed-v1","input":["hello"],"input_type":"query","encoding_format":"float"}`
  → 200, 返回正常 embedding 向量. ✅
- openclaw memorySearch schema (6.11) 支持: `provider`/`remote.baseUrl`/`remote.apiKey`/
  `model`/`queryInputType`/`documentInputType`/`fallback`. provider 可设 `openai-compatible`.
- nv_40006_uni gateway 源码 `handlers.py` 是手写 `BaseHTTPRequestHandler`,
  `do_POST` 硬编码 path 路由; 已有 `NV_INTEGRATE_HOST`, `NVU_KEYS`, cooldown.py
  (`is_key_cooling`/`mark_key_cooling`/`reset_key429_count`) 现成可复用.
- gateway bind-mount (`/opt/cc-infra/proxy/nv-uni/gateway → /app/gateway` rw),
  改 .py 只 restart 不 rebuild (r569).

## 改动 (HM2, 单链路聚焦 nv_40006_uni)

### 1. gateway/handlers.py — 加 /v1/embeddings 路由
- imports: 加 `NVU_KEYS, NV_INTEGRATE_HOST, is_key_cooling, mark_key_cooling,
  reset_key429_count` (config.py 已 re-export cooldown 三函数).
- `do_POST`: path 分支加 `("/v1/embeddings","/embeddings")` → `_handle_embeddings()`.
- `do_HEAD`: 白名单加 `/v1/embeddings`, `/embeddings`.
- 新增 `_handle_embeddings()`: 鉴权 (`_check_auth`, HM2 default `NVU_GATEWAY_API_KEY=nv-local`)
  → 读 body 透传 → 5 key rr 轮转 (虚拟 tier `embeddings_integrate`, 与 chat tier 隔离)
  → 跳过冷却中的 key → `HTTPSConnection(NV_INTEGRATE_HOST, timeout=60)` POST `/v1/embeddings`,
  headers `Authorization: Bearer <key>` → 429 mark_key_cooling 跳下一 key → 200/其他
  relay 原样 + reset_key429_count → 全 key 冷却 502 `all embeddings keys exhausted`.
  非流式一次性返回. metrics 走 `_log_metrics`, `agent_type=embeddings`,
  `upstream=nv_integrate`.
- 备份: `handlers.py.bak.R581_embeddings`.

### 2. openclaw config (HM2, agents.defaults.memorySearch)
```
enabled: true
provider: openai-compatible
remote.baseUrl: http://localhost:40006/v1
remote.apiKey: nv-local            # 网关鉴权, nvapi key 不出网关
model: nvidia/nv-embed-v1
queryInputType: query             # NVCF asymmetric embedding
documentInputType: passage
fallback: none
```

## 改后验证
- `docker restart nv_40006_uni` → /health ok, chat 链路不受影响 (embeddings 独立分支).
- `curl /v1/embeddings -H "Authorization: Bearer nv-local" -d '{...nvidia/nv-embed-v1...}'`
  → 200, 返回 embedding 向量. ✅
- `openclaw memory status --deep` → `Provider: openai-compatible`,
  `Model: nvidia/nv-embed-v1`, `Embeddings: ready`, 不再 `missing-provider-auth`. ✅
- `openclaw memory index` → `Indexed: 4/4 files · 13 chunks`, `Dirty: no`. ✅
- `openclaw memory search "openclaw stability"` → 语义召回返回相关记忆内容
  (GLM5.2 链路 / 5 NV API Key 轮转 / Peer Fallback). ✅ 端到端闭环.
- 网关日志: 9+ 次 `NV-EMB ok status=200`, key 0-4 轮转 (rr 生效),
  耗时 1052-2297ms (冷启动 8887ms). metrics jsonl 完整记录.
- journalctl: 重启后无 `[memory] sync failed` / `missing-provider`, `doctor.memory.status ✓ 163ms`. ✅

## 铁律
- 聚焦 hm40006 (nv_40006_uni) — 只加 embeddings 路由, 未碰其他 model link. ✅
- 改前有数据 — nvapi key + integrate embeddings 实测可用. ✅
- 改后有验证 — curl / memory status / memory index / memory search / journal / 网关日志. ✅
- 写入仓库 — 本文件 + handlers.py 改动. ✅
- R569 起: CC 直接改两机静态运维, 无交替优化. ✅

## 回滚
- 网关: `cp handlers.py.bak.R581_embeddings handlers.py && docker restart nv_40006_uni`.
- openclaw: `openclaw config set agents.defaults.memorySearch.enabled false`
  (降级到 HM1 同款禁用状态).
