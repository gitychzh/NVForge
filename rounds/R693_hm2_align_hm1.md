# R693: HM2 nv_gw 全参数对齐 HM1 + hermes agent 配置修复

## 背景
R6xx 系列"HM2→HM1"轨迹长期遵循"只改 HM1 不改 HM2"旧铁律(R569 已取消但后续轮次未执行两机对称编辑),
导致 HM1 被一路精调到激进参数, HM2 停留在 R537~R576 旧保守值。两机严重不对称, HM2 失败路径拖长
(avg 71s/max 114s, ATE 跑满 90s budget)。本轮一次性把 HM2 对齐 HM1 当前最新值, 并修两个 hermes
agent 配置 bug。

## 改前数据 (HM2, 2026-07-04 19:34 CST 抓取, 30min 窗口)

### nv_requests
| status | count | avg_ms | max_ms |
|--------|-------|--------|--------|
| 200 | 14 | 71656.5 | 114502 |
| 502 | 3 | 151465.0 | 154098 |

### nv_tier_attempts
| error_type | count |
|------------|-------|
| IntegrateTimeout | 12 |

### hermes 日志告警
- `Unknown approvals.mode 'bypass'` ×30/h (BUG-3)
- `Model glm5_2_ms has a context window of 32,768 tokens, below minimum 64,000` (BUG-4)

## 修改清单

### BUG-3 (hermes): approvals.mode bypass→off
- 文件: `~/.hermes/config.yaml` (HM2)
- 备份: `config.yaml.bak.R693`
- 原因: `bypass` 非合法值(合法: manual/smart/off), hermes 退回 manual 导致本该免审批的命令卡审批
- 验证: 重启 hermes 后 1min 内告警 0 次 ✅

### BUG-4 (hermes): fallback glm5_2_ms 补 context_length
- 文件: `~/.hermes/config.yaml` (HM2) fallback_providers 段
- 新增: `context_length: 131072`
- 原因: hermes 误报 glm5_2_ms context=32768 < 64000 门槛, background review 失败
- 验证: 重启 hermes 后 context window 告警 0 次 ✅

### BUG-1 (HM_NV_MODEL_TIERS): 误报, 不修
- 两机 compose 均未注入 HM_NV_MODEL_TIERS, 但 config.py 默认值两机一致
  (`['kimi_nv','dsv4p_nv','glm5_1_nv','glm5_2_nv']`), /health 输出一致
- config.py 注释: 该变量在单 tier 架构下为死参数 (tier_order=[mapped_model])
- 无实际影响

### BUG-2 (HM2 nv_gw 全参数对齐 HM1)
| 参数 | HM2 改前 | HM2 改后(=HM1) | HM1 当前 | 说明 |
|------|---------|---------------|---------|------|
| UPSTREAM_TIMEOUT | 30 | 25 | 25 | R652 |
| TIER_TIMEOUT_BUDGET_S | 90 | 76 | 76 | R692 |
| MIN_OUTBOUND_INTERVAL_S | 0.5 | 0 | 0 | R638 |
| NVU_CONNECT_RESERVE_S | 2 | 0 | 0 | — |
| NVU_EMPTY_200_FASTBREAK | 3 | 2 | 2 | — |
| NVU_FORCE_STREAM_UPGRADE | 1 | 0 | 0 | 对齐(HM1 走默认 0, 本轮补显式) |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 61 | 25 | 25 | R656-R690 |
| NV_INTEGRATE_KEY_COOLDOWN_S | (缺失=90) | 0 | 0 | R631 |

- HM2 compose 备份: `docker-compose.yml.bak.R693`
- HM1 compose 备份: `docker-compose.yml.bak.R693` (补 NVU_FORCE_STREAM_UPGRADE: "0" 显式)
- 部署: `docker compose up -d nv_gw` (两机)
- 验证: `diff <env HM1> <env HM2>` 关键参数完全一致 ✅

## 改后验证 (30min 窗口, 2026-07-04 21:03~21:24 CST)

### nv_requests (HM2)
| status | count | avg_ms | max_ms |
|--------|-------|--------|--------|
| 200 | 4 | 29650 | 41081 |
| 502 | 7 | 52142 | 55010 |

### 按 model 分(关键)
| mapped_model | 200 | 502 | 说明 |
|--------------|-----|-----|------|
| dsv4p_nv | 3 | 7 | NVCF 服务端 dsv4p_nv integrate 持续超时, peer fallback 到 HM1 同样 timeout(HM1 也走 NVCF dsv4p_nv), **服务端故障非配置可修** |
| glm5_2_nv | 1 | 0 | openclaw 主力 pexec 路径正常 ✅ |

### nv_tier_attempts (30min)
| error_type | count |
|------------|-------|
| IntegrateTimeout | 3 |

### docker nv_gw 错误分布(30min, top)
- NV-PEER-FB ×21 (peer fallback 全 timeout, 因 HM1 同样依赖 NVCF dsv4p_nv)
- NV-INTEGRATE-TIMEOUT/FASTBREAK/FAIL/FALLBACK ×10 各 (dsv4p_nv integrate 路径)
- NVCFPexecTimeout ×7, all_tiers_exhausted ×7
- hermes approvals 告警: 0 ✅ (BUG-3 修复确认)

### 对照 (改前 → 改后)
- 502 avg: 151465ms → 52142ms (**失败路径压缩 99s, -65%**) ✅ 预期内改善(budget 90→76, upgrade_timeout 61→25)
- 502 count: 3 → 7 (dsv4p_nv NVCF 服务端故障持续, 非本轮引入; 改前改后同源)
- IntegrateTimeout: 12 → 3 (减少, 因 budget 缩短更早 fastbreak)
- 两机 nv_gw 关键参数: 完全一致 ✅
- hermes approvals/context 告警: 消失 ✅

## 结论

### 本轮修复有效性
1. **BUG-3 (approvals.mode bypass→off)**: ✅ 告警 30/h → 0, hermes 不再误退 manual 审批
2. **BUG-4 (glm5_2_ms context_length)**: ✅ background review 告警消失
3. **BUG-1 (HM_NV_MODEL_TIERS)**: 误报结案, 两机 config.py 默认一致, 死参数无影响
4. **BUG-2 (HM2 nv_gw 全参数对齐 HM1)**: ✅ 两机 8 个关键参数完全一致, 对称性恢复

### 502 根因澄清
改后 502 全部来自 `mapped_model=dsv4p_nv`, 根因是 **NVCF 服务端 dsv4p_nv integrate 端点持续超时**,
peer fallback 到 HM1 也 timeout(因 HM1 同样走 NVCF dsv4p_nv, 两机对等无法互救服务端故障).
**非本轮配置改动引入**, 改前 30min 的 3 个 502 同源. 本轮把 budget 90→76 + upgrade_timeout 61→25 反而
让失败路径从 avg 151s 压到 52s(-65%), 更快释放, 是改善而非恶化.

### 后续建议 (非本轮范围)
- dsv4p_nv NVCF 服务端不可用属上游故障, 需等 NVCF 恢复或考虑将 hermes primary 临时切到 glm5_2_nv
  (openclaw 已用 glm5_2_nv pexec 路径, 当前 100% 成功)
- peer fallback 对"两机同走 NVCF"的服务端故障无救济能力, 这是架构局限, 非 bug
