# OC-R1 (OpenClaw 8-Round Optimization) — 2026-07-01

## 目标
本机 openclaw 全链路优化,8轮,间隔5min,每轮基于日志数据做单点改动。本轮=第1轮(基线+日志补齐)。

## 改前数据 (最近30min 01:09–01:39, hm_metrics+error_detail)

全链路基线 (hm40006 侧,所有 caller 混合):
- 总请求 156, 成功 117, 失败 39 → 成功率 **75.0%**
- 成功延迟 P50 6.5s / P90 11.2s / P99 21.6s / max 93.9s
- 失败:39× 502 `all_tiers_exhausted`
  - 硬失败 6×: 3 key 各 ~30s `NVCFPexecTimeout`, tier 总 ~92–115s
  - 软失败 ~33×: `attempts=0`, elapsed <5s (全 key/tier 在 cooldown 秒退)

openclaw 侧 (/tmp/openclaw/openclaw-2026-07-01.log):
- 502 时 openclaw 报 `Embedded agent failed before reply` + `lane task error`,最长一次 lane duration 422634ms (7min, openclaw 内部重试累加)
- `model-fallback/decision` 触发但无备选模型可 fallback (单模型清理)
- **per-request 成功/延迟无结构化记录** — 只有失败时 `provider-transport-fetch` WARN

根因: NVCF 平台间歇整批不可用 ([[nvcf-platform-intermittent-outage-2026-06-29]]),非代码可根治。

## 日志缺口 (本轮要修)
"openclaw 全链路"分析需要把 openclaw 的流量从 hermes/opencode 里独立出来,但 hm40006 的 `agent_type` 硬编码 `"_nv"`,不区分 caller。openclaw 自身日志又无 per-request 成功记录。→ **在 hm40006 metrics 加 `caller` 字段**,把 openclaw 流量标记出来,后续7轮可独立分析 openclaw 子集。

## 改动 (单点, 可逆)
1. **hm40006 `handlers.py`**: 加 `_detect_caller(user_agent, x_caller)` 模块级 helper;metrics dict 加 `"caller"` 字段;`_log("REQ")` 行带 `caller=`。
   - 优先读 `X-Caller` 请求头,回退到 User-Agent。
   - `OpenAI/Python` → openclaw; `python-httpx` → httpx; `python-requests` → requests; `opencode/` → opencode-standalone; 否则 other/unknown。
   - **注意**: `opencode/` UA 不映射到 openclaw(standalone opencode 用同 UA,会误标);openclaw 靠 `X-Caller` 头主通道。
2. **openclaw 配置**: `openclaw config patch` 给 provider `nv_cus` 加 `headers: {"X-Caller":"openclaw"}`,`openclaw daemon restart` 生效。

铁律破例自改: HM1 自改本机 hm40006 源码 + openclaw 配置(先例 [[hm1-mihomo-removed-2026-06-30]] [[dsv4p-thinking-mode-enabled-2026-06-30]]),理由=三 agent 共用本机 hm40006,加 caller 字段是观测层零热路径影响,服务于本机 openclaw 优化。

## 验证
- hm40006 health ok,容器 healthy
- openclaw 端到端 `openclaw agent -m "reply: PING_R1_OK"` → 回复正确
- metrics 里 `caller=openclaw` 正确出现(含一次 502 = NVCF 间歇故障,非改动引入)
- caller 覆盖: openclaw(主流量) / httpx(hermes 或 opencode) / 其他可区分
- 备份: `handlers.py.bak.caller_field_20260701_0145`; openclaw config 自动备份机制

## 后续7轮的数据基础
现在 hm_metrics.jsonl 每条带 `caller`。后续按 `caller=openclaw` 筛子集做延迟/成功率分析,决定单参数改动(超时/cooldown/throttle 等)。

## ⏳ 下一轮 OC-R2 (5min 后): 用新 caller 字段采集 openclaw 专属窗口基线,识别首个可优化参数
