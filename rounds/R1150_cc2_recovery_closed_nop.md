# R1150 — cc2 恢复闭环 NOP (R1148/49 风暴尾窗已完全滚出活跃窗口)

- 轮次: R1150
- 时间: 2026-08-08 02:20 CST
- 类型: **恢复闭环 NOP (不改码)**
- 容器: nv_gw 23h / cc4101 22h / dsv4p_nv40066 3d — 全部稳定未重启

## 结论一句话

R1148/R1149 那场瞬时 (DEGRADED-fid + 全 5 key egress RemoteDisconnected) 风暴的**尾窗已完全滚出 30min
活跃窗口**: 风暴段 17:47-18:02 UTC 结束后的所有请求 **55/55 = 100% SR**, 最新 5min 15/15, 无新错误类型、
无配置漂移 → 恢复闭环, NOP 不改码。

## 本轮数据 (live 实查 2026-08-08 02:18 CST)

### 30min 主链 (cc2-primary)
- **200 | 54** (18:03:42 → 18:20:05 连续)
- **502 | 4** — 全部落在 **17:54:11 → 18:02:45 UTC** = R1149 记录的风暴带 (17:47-18:02) **尾窗**
- **整窗 SR = 54/58 = 93.1%**, 但**末次失败 18:02:45 之后全是 200**

### 风暴后 18:03 → 现在 (决定性)
- cc2-primary: **55/55 = 100% SR, 连续 55 个 200, 0 失败** (18:03:42 → 18:20:05)

### 最新 5min
- 15/15 = **100% SR, 0 非-200**

### 错误分类 (30min surface)
- `all_tiers_exhausted` × 4, avg_dur ~237s — 全在风暴尾窗, **与 R1148/49 同签名, 无新类型**

### tier 层 (nv_tier_attempts)
- 5 key 几乎全是 `pexec_success` (k0:10 k1:9 k2:11 k3:11 k4:8)
- 错误仅 `NVCFPexecRemoteDisconnected` × 2 (k0/k1) — 瞬时 egress, 无 429/empty200

### buffer 日志 (live 实查)
- 全 `attempt=1/5 → direct flush` 干净稳态 (7-35s/req, content 530c-47357b)
- 唯一一次 attempt-1 `execute_failed` (req=9f06e4d9, k4) → 5s backoff → **attempt-2 success** (35053ms)
  = 已知 k 瞬时 egress 自愈签名, 非回归
- 无 WAIT / DEGRADED / buffer_exhausted

### fallback
- ms_gw 未走 (nb=0) ✅

## 依据 vs R1148/49

| 项 | R1148/49 | R1150 现状 |
|---|---|---|
| 错误签名 | all_tiers_exhausted + buffer_exhausted | 同, 4× all_tiers_exhausted |
| 429/empty200 | 0=非 cooldown | 0, 同 |
| tier 错误 | NVCFPexecRemoteDisconnected | 同, ×2 |
| 风暴后 SR | 18:03 起 28+/20+ 全 200 | **55/55=100% 连续** |
| buffer | 风暴期 attempt-2/3, 后 attempt-1 | 全 attempt-1, 1 次瞬时自愈 |
| fid | 281478d0-f307 | 281478d0-f307 稳定, 无 52e1ddb6 |

## 改动

**无 (NOP)。** 风暴为过境事件, 无参数可调、无码可改。恢复已闭环:
30min surface 窗口的 4× 502 为风暴末段 17:54-18:02, 下个窗口 (18:20+) 即使入窗也已全部 200。

## 验证
- 风暴后连续 55 个 200 = 100% SR
- 最新 5min 15/15 = 100% SR
- buffer 全 attempt-1 direct flush, 唯一 execute_failed attempt-2 自愈
- 容器全部稳定未重启, health all ok

## 下一步
- 维持静稳观察。若下轮 30min 整窗 SR 保持 97%+ (4× 502 滚出 30min 窗口) 即**正式宣告恢复闭环**。
- 若再出现全 5 key 连败或新错误类型, 再深挖 (查 mihomo 线路 egress / KeyManager cooldown)。