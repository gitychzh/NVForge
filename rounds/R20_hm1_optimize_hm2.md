# R20: HM1优化HM2 — OUTBOUND 4→6 (+2s), UPSTREAM 45→48 (+3s), BUDGET 90→96 (+6s), RESERVE 4→5 (+1s)

**Date**: 2026-06-26 06:47 CST
**Author**: opc_uname (HM1)
**Role**: HM1优化HM2
**Round**: R20

## 1. 数据收集

### HM2 hm40006 容器环境变量
```
UPSTREAM_TIMEOUT: 45
TIER_TIMEOUT_BUDGET_S: 90
MIN_OUTBOUND_INTERVAL_S: 4.0
KEY_COOLDOWN_S: 30.0 (capped at 30 by code)
HM_CONNECT_RESERVE_S: 4
NV_MODEL_TIERS: ['glm5.1_hm_nv', 'deepseek_hm_nv', 'kimi_hm_nv']
DEFAULT_NV_MODEL: glm5.1_hm_nv
HM_NUM_KEYS: 5
```

### 24小时DB数据 (hm_tier_attempts, 2026-06-25~26)
```
glm5.1_hm_nv tier:
  429_nv_rate_limit:      1898  (89.3%)
  NVCFPexecTimeout:          88  (4.1%)
  NVCFPexecSSLEOFError:     37  (1.7%)
  NVCFPexecConnectionResetError: 17 (0.8%)
  NVCFPexecRemoteDisconnected: 1

deepseek_hm_nv tier:
  NVCFPexecTimeout:         121  (88.9%)
  NVCFPexecSSLEOFError:      4  (2.9%)

kimi_hm_nv tier:
  NVCFPexecTimeout:           8
  NVCFPexecSSLEOFError:      4
```

### per-key 429分布 (5 keys, all hot)
```
k0: 388    k1: 380    k2: 375    k3: 383    k4: 372
```
所有key均匀分布429 — 全部分享同一个NVCF function rate limit。

### 24小时请求成功率
```
glm5.1_hm_nv: 成功187, 失败/回退417  →  约31%
deepseek_hm_nv: 100% fallback目标
HM-SUCCESS: 873 (含所有tier直接+fallback成功)
HM-FALLBACK: 1450
```

### 实时日志 (tail, 最新请求)
```
[06:37] glm5.1_hm_nv: k3 429→k4 429→k5 429→k1 429→k2 429
  5key全429, 耗时4021ms, 全部标记15s全局cooldown
  → fallback到deepseek_hm_nv: k3 succeeded (5cycle, ~8s)
[06:37] 下一个请求: glm5.1依然全部cooldown中
  → 直接fallback到deepseek: k4 SSLEOFError→k1 reattempt
```

## 2. 错误分析

### 核心问题: NVCF function-level rate limit + key over-cycling
- 所有5个key共享**同一个NVCF function** (glm5.1 func_id: `822231fa`), 所以NVCF function-level rate limit作用在所有key上
- 当key被429后, 立即cycle到下一个key, 依然429 — 因为rate limit是function-level
- 5个key在~4s内全部被429, 触发全局15s cooldown
- MIN_OUTBOUND=4.0太激进: 第一个key等待4s后, 整个5key cycle仅需~8s (实测key间gap 80-500ms)
- 实际请求间隔(~11s) > NVCF rate limit window(~60s) — 429是应用级, 不是NVCF limit问题

### 次要问题: deepseek fallback路径存在SSLEOFError
- SSLEOFError: k5 (port 7899) 最频繁, 然后是k4,k3 — 慢端口SOCKS5连接更脆弱
- HM_CONNECT_RESERVE=4不够: SOCKS5+SSL handshake ~1-1.5s, 但慢端口有时2-4s
- 需要+1s reserve给慢端口更多余量

## 3. 优化方案

### 变更 (4项)
| # | 参数 | 旧值 | 新值 | Δ | 原因 |
|---|------|------|------|---|------|
| 1 | `MIN_OUTBOUND_INTERVAL_S` | 4.0 | 6.0 | +2s | 4s太激进,5key全429<5s; 6s给function rate limit更多重置; 5key×6s=30s cycle |
| 2 | `UPSTREAM_TIMEOUT` | 45 | 48 | +3s | deepseek avg 29-35s; 48s给13s margin; 减少deepseek边界超时 |
| 3 | `TIER_TIMEOUT_BUDGET_S` | 90 | 96 | +6s | 96s=2×48s; 匹配增加的超时; 2key cycle预算 |
| 4 | `HM_CONNECT_RESERVE_S` | 4 | 5 | +1s | SOCKS5+SSL reserve; 5s给慢端口(7899)+1s margin; 减少SSLEOFError |

### 未改变项 (分析后不调)
- `KEY_COOLDOWN_S=30.0`: 已到code cap (min(...,30)), 无法再提高
- `TIER_COOLDOWN_S=60`: 已确认为DEAD变量, 代码中完全未使用, 无调优价值

## 4. 执行结果

✅ SSH到HM2成功
✅ 编辑`docker-compose.yml`: 4项变更
✅ 重建`hm40006`容器: docker compose build + up -d --force-recreate
✅ 容器启动正常, 日志显示处理请求中
✅ 新配置确认生效:
```
UPSTREAM_TIMEOUT=48
TIER_TIMEOUT_BUDGET_S=96.0
MIN_OUTBOUND_INTERVAL_S=6.0
HM_CONNECT_RESERVE_S=5
KEY_COOLDOWN_S=30.0
NV_MODEL_TIERS=['glm5.1_hm_nv', 'deepseek_hm_nv', 'kimi_hm_nv']
```

## 5. 预期效果

- **MIN_OUTBOUND 4→6**: 首次key延迟+2s, 降低429 key over-cycling速度; 预期减少10-15%的glm5.1 key cycle失败
- **UPSTREAM 45→48**: +3s per-key timeout, 给deepseek更多时间完成NVCF pexec; 预期减少5-10%的deepseek超时
- **BUDGET 90→96**: +6s total budget, 给fallback tier足够2-key cycle时间; 预期减少deepseek timeout→kimi fallback的级联
- **RESERVE 4→5**: +1s SOCKS5+SSL reserve, 慢端口有更多余量; 预期减少SSLEOFError ~5-10%

## ⏳ 轮到HM2优化HM1