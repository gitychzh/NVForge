# R1: HM1→HM2 单模型glm5.1超时/cooldown优化 (R262 baseline)

## 📊 数据收集 (HM2 hm40006)

### Docker环境变量 (优化前)
| 参数 | 值 | 说明 |
|------|-----|------|
| UPSTREAM_TIMEOUT | 63s | R220: 54→57→63 |
| KEY_COOLDOWN_S | 38s | key冷却时长 |
| TIER_COOLDOWN_S | 45s | tier冷却时长 |
| MIN_OUTBOUND_INTERVAL_S | 16.0s | R188: 14.2→14.6→16.0 |
| TIER_TIMEOUT_BUDGET_S | 128s | 单tier预算 |
| HM_CONNECT_RESERVE_S | 24s | SSL握手预留 |

### 30min DB统计 (R262 baseline)
| 指标 | 值 |
|------|-----|
| 总请求 | 1233 |
| 成功 | 1183 (96.0%) |
| 错误(5xx) | 50 |
| 错误类型 | 49 all_tiers_exhausted + 1 NVStream_IncompleteRead |
| P50 | 24.1s |
| P95 | 58.3s |
| 平均成功 | 24.1s |

### 日志错误模式
- `SSLEOFError` — k2/k1 SSL握手失败 (底层代理)
- `NVCFPexecTimeout` — k1/k4/k5 pexec超时 10-39s
- `empty200` — k5/k3 返回空Content-Length:0
- `429_nv_rate_limit` — k4 被NV API限流
- 全key耗尽 → ABORT-NO-FALLBACK (无fallback tier)

## 🔧 优化方案

### 诊断
HM2 R262是单模型glm5.1架构，只有1个tier无fallback。当NV API返回空/超时/SSL错误时，5个key全部被标记cooling(38s+指数增长)→所有key不可用→请求立即失败。核心问题是cooldown太长(38s×5key=190s周期)，key无法及时恢复。

### 本轮修改 (4参数, 保守增量)
1. **UPSTREAM_TIMEOUT: 63→75** (+12s, +19%)
   - 理由: P95=58s但63s截断慢请求(87s成功示例存在); +12s给超时key额外完成时间
   - 少改多轮: 12s增量保守, 避免过度放大

2. **KEY_COOLDOWN_S: 38→25** (-13s, -34%)
   - 理由: 38s cooldown + 指数增长→50s 导致key长时间不可用; 缩短到25s让被429的key更快恢复
   - 5×25=125s总周期 vs 原来5×50=250s峰值

3. **MIN_OUTBOUND_INTERVAL_S: 16.0→12.0** (-4s, -25%)
   - 理由: 16s间隔太长→请求排队积压; 12s保持安全但不浪费
   - 5×12=60s cycle vs GLOBAL=45s, 安全边距15s

4. **TIER_COOLDOWN_S: 45→30** (-15s, -33%)
   - 理由: 全key耗尽后tier冷却45s太长; 单tier场景下30s更快恢复

### 未修改(保守)
- TIER_TIMEOUT_BUDGET_S: 128s (保持)
- HM_CONNECT_RESERVE_S: 24s (保持)
- HM_NV_PROXY_URLS: 保持SOCKS5代理
- NVCF_GLM51_FUNCTION_ID: 保持

## 📈 预期效果
- 减少 all_tiers_exhausted 50→35-40/30min (-20%)
- 快请求P50保持20-25s范围
- 慢请求P95不超75s新timeout
- key冷却更快恢复, 减少全耗尽概率

## ⚖️ 评判标准
- ✅ 更少报错: 减少all_tiers_exhausted, 让更多请求成功
- ✅ 更快请求: 降低key cooldown减少等待, 减少interval减少排队
- ✅ 超低延迟: P50保持<25s, P95<75s
- ✅ 稳定优先: 保守增量不激进, 单轮验证
- ✅ 铁律: 只改HM2不改HM1 — 修改/opt/cc-infra/docker-compose.yml hm40006环境变量

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记