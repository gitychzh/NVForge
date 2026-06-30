# R477: HM2→HM1 — ⏸️ NOP · 全参数天花板 · dsv4p_nv tier NVCFPexecTimeout · 零配置变更 · 铁律:只改HM1

**方向**: HM2 优化 HM1 (本轮执行者=HM2, 对端=HM1, host_machine=opc_uname)
**动作**: ⏸️ NOP — 全8参数在天花板/地板, 无参数可调, 零配置变更
**时间**: 2026-07-01 05:02 UTC
**轮次**: R477 (HM2→HM1方向, 第19轮连续NOP)
**变更文件**: 无 (零配置变更)

## 0. 执行约束
- **铁律**: 只改HM1配置, 绝不改HM2本地
- **单参数原则**: 每轮只改1个参数, 少改多轮积累
- **数据驱动**: 先采集后决策, 5层验证

## 1. 数据采集 (改前Baseline, 04:55-05:05 UTC)

### Layer 1 — 容器Env (8参数完整扫描)
```
UPSTREAM_TIMEOUT=25             ← R476改后(30→25), 当前值
TIER_TIMEOUT_BUDGET_S=125       ✓ (R386, 之后未动)
MIN_OUTBOUND_INTERVAL_S=3.8      ✓ (R442, 之后未动)
KEY_COOLDOWN_S=25                ✓ (R438/R162, 之后未动)
TIER_COOLDOWN_S=38               ✓ (R270, 之后未动)
HM_CONNECT_RESERVE_S=10          ✓ (R322, 之后未动)
HM_PEXEC_TIMEOUT_FASTBREAK=2    ✓ (R473, 之后未动)
HM_SSLEOF_RETRY_DELAY_S=2.0     ✓ (R429, 之后未动)
```
容器: cc-infra-hm40006, started 2026-06-30T18:30:57Z, /health=ok, hm_num_keys=5

### Layer 2 — Docker Logs (04:55-05:05, 最新200行)

成功模式:
  - 全部 first-attempt 成功 (k1-k5 循环, 连接建立<25s)
  - 成功延迟: 3.2s-24s (个别streaming达44s)
  - 04:55-05:02: 密集连续成功, 8+ consecutive SUCCESS

失败模式: 100% NVCFPexecTimeout (~25s per attempt, UPSTREAM_TIMEOUT ceiling)
  - 每attempt完全25s (UPSTREAM_TIMEOUT=25 ceiling)
  - 2连timeout触发 FASTBREAK=2 → break (省后续key尝试)
  - ATE总耗时: ~50-51s (2×25s)
  - 0×429, 0×empty200, 0×SSLEOF — 纯净NVCF server-side超时

时序(10分钟窗口):
  04:55-05:01: 连续成功 (first-attempt, k1-k5循环)
  05:02:13: 1st ATE (k5=25.3s, k1=25.7s, FASTBREAK, total=51s)
  05:02:41: 2nd ATE (k1=25.3s, k2=25.3s, FASTBREAK, total=50.6s)
  05:03:37: 3rd ATE (k2=25.3s, k3=25.7s, FASTBREAK, total=51s)

### Layer 3 — DB 30min窗口
```
status=200 no-retries: 47req | avg=13054ms | (全first-attempt成功)
status=200 with-retries: 2req | avg=36576ms | (1次key cycle后成功)
status=502 all_tiers_exhausted: 8req | avg=50969ms | (NVCFPexecTimeout×2→FASTBREAK)

Overall 6h: 1114req/928OK(83.3%)/186ATE(16.7%)
  p50=8481ms p95=102725ms max=124158ms
```

### Layer 4 — 失败聚类 (10min window)
| 时段 (UTC) | 成功(est) | 失败(est) | 成功率(est) |
|------|------|------|------|
| 04:55-05:05 | ~10 | ~3 | ~77% |

### Layer 5 — Per-key Error分析
| 键 | 请求(6h) | 错误 | 结论 |
|------|------|------|------|
| k1 | 199 req | 0 per-key error | 无劣化 |
| k2 | 157 req | 0 per-key error | 无劣化 |
| k3 | 217 req | 0 per-key error | 无劣化 |
| k4 | 188 req | 0 per-key error | 无劣化 |
| k5 | 167 req | 0 per-key error | 无劣化 |
| ATE(None) | 186 | 全NVCFPexecTimeout | server-side |

5键 per-key 0 error — 所有失败在ATE路径(NVCF server-side)

## 2. 优化决策: ⏸️ NOP (全参数天花板)

### 为何NOP (8参数全扫描, 全部在天花板/地板)

| 参数 | 当前值 | 评估 | 结论 |
|------|--------|------|------|
| **UPSTREAM_TIMEOUT** | **25** | **CEIL: 成功p50=6-9s<<25s, R476刚降(30→25)** | **不动** |
| TIER_TIMEOUT_BUDGET | 125 | CEIL: 远超实际需求(50s), 预算已足够 | 不动 |
| MIN_OUTBOUND | 3.8 | FLOOR: p50_gap>>3.8s, throttle非瓶颈 | 不动 |
| KEY_COOLDOWN | 25 | FLOOR: 5键均衡无过热 | 不动 |
| TIER_COOLDOWN | 38 | CEIL: 单tier稳态 | 不动 |
| CONNECT_RESERVE | 10 | FLOOR: 连接预留充足(0 connect超时) | 不动 |
| FASTBREAK | 2 | FLOOR: 已最优(2连break省后续key) | 不动 |
| SSLEOF_RETRY | 2.0 | FLOOR: 0 SSLEOF错误 | 不动 |

### 原理
- R476 (UPSTREAM_TIMEOUT 30→25) 刚执行完毕，系统进入稳定期
- 所有8参数在天花板/地板，无参数可动
- 失败模式: 100% NVCFPexecTimeout (NVCF server-side blackout), 非参数可修复
- 每attempt耗时25s (UPSTREAM_TIMEOUT ceiling), FASTBREAK=2触发后省后续key
- Per-key 0 error — 无劣化键，键分布均衡
- CC清单三项 ([HM1-A/B/C]) 持续在天花板/地板，无新CC项出现
- 连续19轮NOP(R458-R477)，除R476外全零配置变更
- 30min窗口: 77%成功率, ATE=50-51s/次

### 成功请求延迟分布
- p50=8.5s (6h)，p95(TCP连)≈30s，p95(stream)=103s
- 所有p95以下成功请求连接建立<25s — 25s UPSTREAM_TIMEOUT覆盖
- 长尾成功(44s, 44.8s): streaming完成，非连接超时

## 3. 执行记录

### 变更对照
| 项目 | 改前 | 改后 | Δ |
|------|------|------|-----|
| docker-compose.yml | 不修改 | 不修改 | 0 |
| 容器env | 不修改 | 不修改 | 0 |
| 源码 | 不修改 | 不修改 | 0 |

**零配置变更** — 无文件修改，无容器重启

## 4. 系统状态
- **稳定性**: 19轮连续NOP(R459-R477), R476为唯一非NOP(UPSTREAM_TIMEOUT 30→25)
- **延迟**: p50=6-9s (稳定), ATE ~50-51s (R476后改善: 60s→51s)
- **错误模式**: 100% NVCFPexecTimeout server-side (0×429/0×SSLEOF/0×empty200)
- **键健康**: 5键全100% per-key success, 0劣化键
- **铁律遵守**: ✅ 只改HM1不改HM2, ✅ 不碰mihomo服务, ✅ 不修改源码
- **局限**: NVCF server-side blackout不可从proxy层修复; 需NVCF后端基础设施改善

## 5. 上下文: R476与当前状态
- R476 (UPSTREAM_TIMEOUT 30→25) 是R473 FASTBREAK=2之后首次非NOP参数调整
- R476评论: 成功p95=17s well under 25s; 每attempt省5s×2att=10s per ATE
- 当前状态: R476后系统在25s UPSTREAM_TIMEOUT天花板稳定运行
- HM1最新commit `3cfe7f1` (OC-R4): 被动采集规格定稿+schema全勘定 (cc2批判驱动)
- 该次commit为metrics schema完善, 非HM proxy参数变更

## ⏳ 轮到HM1优化HM2  ← 脚本检测此标记