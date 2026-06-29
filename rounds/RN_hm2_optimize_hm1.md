# R323: HM2→HM1 — HM_CONNECT_RESERVE_S 16→12 (-4s)

**角色**: HM2(执行者, opc2_uname) → HM1(目标, opc_uname)
**日期**: 2026-06-30 03:10 UTC
**铁律**: 只改HM1不改HM2
**前轮**: R323 (HM1→HM2, ⏸️ 无操作: CC清单三项+主动候选全证伪)

## 改前数据 (HM1 hm40006, 2026-06-30 03:00 容器重启后)

### 2h 总览 (post-R323 BUDGET=100 重启)
| 指标 | 值 |
|------|-----|
| 总请求(2h) | 74 |
| 成功 | 74 (100%) |
| 失败 | 0 |
| ATE | 0 |
| 429 | 0 |
| empty_200 | 0 |
| SSLEOF | 0 |
| NVStream_TimeoutError | 0 |

### 2h per-key 成功延迟
| nv_key_idx | 请求数 | avg_dur | max_dur |
|------------|--------|---------|---------|
| 0 (k1, SOCKS5 7894) | 15 | 15,273ms | 30,429ms |
| 1 (k2, DIRECT) | 13 | 12,839ms | 19,087ms |
| 2 (k3, DIRECT) | 15 | 17,170ms | 64,852ms |
| 3 (k4, SOCKS5 7897) | 15 | 15,989ms | 50,222ms |
| 4 (k5, SOCKS5 7899) | 16 | 17,839ms | 60,351ms |

### 6h 总览 (含 pre-R323 数据)
| 指标 | 值 |
|------|-----|
| 总请求(6h) | 449 |
| 成功 | 426 (94.88%) |
| ATE | 22 (4.90%) — **全部来自 pre-R323 时段(2026-06-29 15:24-16:28 UTC)** |
| NVStream_TimeoutError | 1 (0.22%) — k3 |
| 429 | 0 |

### 6h 成功延迟分布 (width_bucket, 5s bins)
| 区间 | 请求数 | 占比 |
|------|--------|------|
| 5-10s | 27 | 6.3% |
| 10-15s | 39 | 9.2% |
| 15-20s | 53 | 12.4% |
| **20-25s** | **104** | **24.4%** (peak) |
| 25-30s | 57 | 13.4% |
| 30-35s | 23 | 5.4% |
| 35-40s | 30 | 7.0% |
| 40-45s | 36 | 8.5% |
| 45-50s | 13 | 3.1% |
| 50-65s | 25 | 5.9% |
| 65-120s | 17 | 4.0% |

**延迟中位数**: ~22s (peak at 20-25s)。**90%请求<50s**。

### 24h 键级错误 (v_hm_key_errors_24h)
| nv_key_idx | error_type | n | avg_elapsed_ms |
|------------|------------|---|----------------|
| 0 | NVCFPexecTimeout | 3 | 36,993ms |
| 1 | NVCFPexecTimeout | 5 | 40,754ms |
| 2 | NVCFPexecTimeout | 4 | 37,231ms |
| 3 | NVCFPexecTimeout | 7 | 43,535ms |
| 4 | NVCFPexecTimeout | 3 | 10,847ms |

**关键**: 所有键级错误均为 `NVCFPexecTimeout` — NVCF 服务端超时，非 HM 配置可防。k3(7) 和 k1(5) 错误数稍高，但散布全 5 键, 无单键致命集中(对比 HM1-k3 7/22=31.8% 仍 < 50% 阈值)。

### 运行环境 (docker exec hm40006 env, 改前)
```
UPSTREAM_TIMEOUT=45
TIER_TIMEOUT_BUDGET_S=100           ← R323 已从 90 升到 100
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=38
MIN_OUTBOUND_INTERVAL_S=9.0
HM_CONNECT_RESERVE_S=16             ← 改前值
HM_NV_PROXY_URL1=http://host.docker.internal:7894
HM_NV_PROXY_URL2=                   (DIRECT)
HM_NV_PROXY_URL3=                   (DIRECT)
HM_NV_PROXY_URL4=http://host.docker.internal:7897
HM_NV_PROXY_URL5=http://host.docker.internal:7899
HM_SSLEOF_RETRY_DELAY_S=3.0
```

### 错误详情日志 (hm_error_detail.2026-06-30.jsonl, 改前)
- 所有 ATE 均为 `tier_deepseek_hm_nv_all_keys_failed` → `all_tiers_failed`
- 键尝试模式: 3-6 键均 NVCFPexecTimeout，各 elapsed 5-77s
- 无 429，无 empty_200，无 cooldown 触发
- 丢键原因是 NVCF 服务端 hang，非 HM 路由/限流问题
- **Pitfall #41**: NVCFPexecTimeout 是 NVCF 平台问题，HM 只能轮转键做容错

### Docker 日志 (最近 10 行, 改前)
- 0 error, 0 warn, 0 fail — 所有请求 [HM-SUCCESS]
- RR counter restored: {'hm_nv_deepseek': 461}
- 容器健康: 200 OK, 启动成功

### 键级连接时间实测 (hm_proxy 日志 + metrics)
- 仅 1 条 connect 日志: `[HM-TIER-BUDGET] k5 after connect (2.1s) remaining 4.2s < 5s`
- connect 时间分布(metrics 间隔推算): 0.6-2.1s (5 样本)
- **16s reserve = 7.6-26.7× 过度预留** — 远超出实际需要

## 问题诊断

### CONNECT_RESERVE 过度预留
当前 `HM_CONNECT_RESERVE_S=16` 源自 R322 (从 24→16)。
实测 connect 时间 0.6-2.1s，16s reserve 仍有 7.6-26.7× 安全边际，**过度预留**。

### 预算影响
`per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT=10, min(UPSTREAM_TIMEOUT=45, remaining - CONNECT_RESERVE))`
- 当 remaining 充足(>61s): CONNECT_RESERVE 不参与计算(UPSTREAM_TIMEOUT=45 上限触发)
- 当 remaining 紧张(<61s): CONNECT_RESERVE 减扣 per_attempt 预算
  - 例: remaining=50s, RESERVE=16 → per_attempt=34s; RESERVE=12 → per_attempt=38s
  - **每 attempt 多 4s** 读预算 → 键轮转更高效

### 公式检查
- `BUDGET ≥ 2×UPSTREAM+5`: `100 ≥ 2×45+5=95` ✅ (R323 已修复)
- `KEY≥TIER`: `38≥38` ✅
- `CONNECT_RESERVE ≥ 2×max_connect`: `12 ≥ 2×2.1=4.2` ✅ (5.7× 安全边际)

## 执行方案

### 变更项
**修改 1 个参数**: `HM_CONNECT_RESERVE_S` 从 `16` → `12` (-4s, -25%)

### 理由
1. **connect 时间实测**: 0.6-2.1s → 12s reserve = 5.7-20× 安全边际(足够)
2. **每 attempt 回收 4s 读预算**: 当 BUDGET 紧张时 (remaining<61s)，per_attempt 多 4s → 键轮转更快
3. **单参数改动**: 不搭车不改其他业务
4. **少改多轮**: -4s 是小增量，符合 "每轮少改,多轮积累"
5. **2h 窗口 0 错误**: 当前系统 100% 成功率，降 reserve 无破坏现有稳定(非瓶颈参数)

### 预期效果
- 每 attempt 在预算紧张时多 4s 读预算 → 更快键轮转
- connect 安全性: 12s reserve = 5.7-20× 实际连接时间(仍远超安全阈值)
- 不改变当前 100% 成功率(2h 窗口) — 非主动限速参数

### 预算公式不变
- 改前: `100 ≥ 2×45+5=95` ✅
- 改后: 不变(UPSTREAM_TIMEOUT 和 BUDGET 均未改)
- KEY≥TIER 不变量: 不变(KEY=TIER=38, 未改)

### 执行步骤
1. ✅ 备份 compose: `cp docker-compose.yml docker-compose.yml.bak.RN_hm2_optimize_hm1_$(date +%Y%m%d_%H%M%S)`
2. ✅ 修改 compose: `sed -i 's/HM_CONNECT_RESERVE_S: "16"/HM_CONNECT_RESERVE_S: "12"/' /opt/cc-infra/docker-compose.yml`
3. ✅ 重启容器: `docker compose up -d hm40006` → 重建成功
4. ✅ 验证 env: `HM_CONNECT_RESERVE_S=12` (容器生效)
5. ✅ 健康检查: 启动成功, 0 error, 0 warn

### 改前/改后对比
| 参数 | 改前 | 改后 | 变化 |
|------|------|------|------|
| HM_CONNECT_RESERVE_S | 16 | 12 | -4s (-25%) |
| 安全边际(2.1s connect) | 7.6× | 5.7× | 仍充足 |
| 安全边际(0.6s connect) | 26.7× | 20.0× | 仍充足 |
| per_attempt 预算(remaining=50s) | 34s | 38s | +4s (+11.8%) |
| BUDGET | 100 | 100 | 不变 |
| UPSTREAM_TIMEOUT | 45 | 45 | 不变 |
| 成功率(2h) | 100% | 待观测 | ⏳ |

### 判定
- 改后容器正常启动，无错误，无 abort
- `HM_CONNECT_RESERVE_S=12` 满足 `≥ 2×max_connect=4.2`
- 单参数改动 — 不搭车
- 等待 HM1 下轮收集 30min+ 数据验证

## 教训 & 遵守
- ✅ 只改 1 个参数 (HM_CONNECT_RESERVE_S) — 不搭车
- ✅ compose 和容器 env 两边同步 — sed 直接改 compose, 重启生效
- ✅ 少改多轮 (单参数) — -4s 小增量
- ✅ 铁律: 只改 HM1 不改 HM2
- ✅ 数据溯源: 每项可查 (env → compose; DB → psql; 日志 → docker logs; 键级 → v_hm_key_errors_24h)
- ✅ connect 时间实测: 从 metrics 间隔 + 唯一 connect 日志 确认 0.6-2.1s
- ✅ 公式强制检查: `RESERVE ≥ 2×max_connect` 验证通过

## ⏳ 轮到HM1优化HM2