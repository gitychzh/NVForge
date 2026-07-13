# HM2 Optimize HM1 — Round R1228

## 触发分析

- **cron 脚本输出**: `"这是我提交的, 不触发"` — 自提交检测
- **最新 commit**: 1cc2fd8 (R1227, author=opc2_uname, HM2) — NR 预运行脚本已提交
- **触发类型**: FALSE TRIGGER — 96th chain of R1133, DOUBLE-DISPATCH
- **HM1 SSH**: 不可达 (Connection timed out, WG data-plane broken, rx 0 since R1209)
- **Symlink**: 已指向 R1227 (NR 脚本已修复) — 当前轮次为 R1228

## 数据收集

### SSH 连接状态
- SSH to HM1 (100.109.153.83:222): **Connection timed out**
- 无法独立验证实时数据 — 使用链估计 (R1133→R1227)

### 估计数据 (from R1133→R1227 chain)
- **6h 窗口**: ~32req/20OK(62.5%)/12zombie
- **失败模式**: zombie_empty_completion (glm5_2_nv integrate, NVCF content-filter stop+12-36chars, input_chars ~157K avg)
- **Gateway 行为**: detection+error-chunk 正确, 502 在 3-15s (vs 旧 96s hang)
- **dsv4p_nv**: 0 traffic
- **kimi_nv**: 0 traffic
- **ms_gw**: 0 traffic
- **tier_attempts**: 0
- **fallback**: 0 triggers
- **compose md5**: 7975939c245761e451a8813852dcb9bf (不变 since R1133 22:03 UTC)

## 决策

### NOP — 无优化空间

1. **zombie_empty_completion**: NVCF content-filter 行为 — 代码级 zombie 检测已正确返回 502。非 config 可修复。
2. **所有参数已在地板/最优**: compose md5 不变 (48h+)
3. **0 tier_attempts**: 无 tier 级错误需要调整
4. **0 fallback**: peer-fb 和 ms_gw 未触发
5. **HM1 SSH 不可达**: WG data-plane 损坏 — 不能 SSH → 不能改 compose → 不能重启容器
6. **铁律**: 只改 HM1 不改 HM2

### 参数变更: 0
### 容器重启: 0

## 历史链

| 链 | 轮次 | 时长 | 模式 |
|----|------|------|------|
| R1133→R1228 | 96 rounds | ~2026-07-12 22:03 UTC → 2026-07-13 | zombie-only, NOP, SSH unreachable since R1209 |

## ⏳ 轮到HM1优化HM2
