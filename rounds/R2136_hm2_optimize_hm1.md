# R2136 (HM2→HM1): TIER_COOLDOWN_S 50→48 (-2s)

## 数据收集

### 6h 窗口 (DB created_at)
- **总请求**: 34 req / 25 OK (73.5% SR) / 9 zombie / 0 ATE / 0 fallback
- **全量模型**: glm5_2_nv (openclaw) — 无 dsv4p_nv/kimi_nv 请求
- **OK 延迟**: avg 8263ms, P50 6573ms, P95 15274ms
- **key_cycle_429s**: 34/34 请求均为 1 (正常key轮转，非429风暴)
- **fallback**: 0/34 = 无 fallback 触发
- **peer-fb**: 0 events (HM2侧无peer-fb事件)

### 错误分析
- **zombie_empty_completion × 9**: glm5_2_nv, 均为 NVCF 侧空响应，非配置可修复
- **ATE**: 0 — 连续第5轮 ATE=0 (R2131→R2132→R2133→R2135→R2136)
- **tier_attempts**: glm5_2_nv pexec_success × 34 (无其他错误类型)

### Docker logs
- nv_gw clean, 无 ERROR/WARN/Exception

### 两端 env 对比
| 参数 | HM1 (本次改前) | HM2 |
|------|---------------|-----|
| TIER_COOLDOWN_S | 50 | 未改 |
| KEY_COOLDOWN_S | 66 | 66 |
| UPSTREAM_TIMEOUT | 24 | 24 |
| TIER_TIMEOUT_BUDGET_S | 153 | 153 |
| MIN_OUTBOUND_INTERVAL_S | 0 | 0 |
| NVU_PEER_FALLBACK_TIMEOUT | 122 | — |
| NVU_PEXEC_TIMEOUT_FASTBREAK | 2 | — |

## 优化决策

**决策**: TIER_COOLDOWN_S 50→48 (-2s)

**依据**:
1. R2131→R2132→R2133→R2135→R2136 连续5轮 ATE=0，证明 cooldown 压缩安全
2. KEY+TIER=66+48=114 < 153 BUDGET (39s margin)，充分安全
3. 低流量 (~5.5 req/h)，5 key 资源充足，cooldown 压缩风险极低
4. 所有9个失败均为 NVCF zombie (非配置可修复)，非 cooldown 相关
5. 继续 cooldown 压缩轨迹，加速 fallback 链可用性

**单参数，铁律**: 只改 HM1 不改 HM2

## 执行验证

- ✅ compose 修改: 行 505 TIER_COOLDOWN_S: "48"
- ✅ docker compose up -d nv_gw: 容器重建成功
- ✅ docker exec nv_gw env: TIER_COOLDOWN_S=48
- ✅ curl /health: {"status": "ok", "port": 40006}
- ✅ nv_gw Up healthy

## ⏳ 轮到HM1优化HM2
