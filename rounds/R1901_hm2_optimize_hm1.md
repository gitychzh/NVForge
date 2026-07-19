# R1901 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 174→172 (-2s)

## 数据采集 (HM1 nv_gw, 2026-07-19 15:00 UTC)

### 6h DB 摘要
```
ok | fail | total
----+------+-------
 28 |   17 |    45
```
- SR: 62.2% (28/45)
- 17 失败全部 `zombie_empty_completion` — NVCF function-level 空200

### 按模型 OK 延迟
```
mapped_model | total | avg_ms | min_ms | max_ms
-------------+-------+--------+--------+--------
 glm5_2_nv   |    21 |   7518 |   2374 |  16462
 dsv4p_nv    |     7 |   9057 |   1779 |  19559
```

### 当前配置
- `UPSTREAM_TIMEOUT=32` (R1900: 34→32)
- `TIER_TIMEOUT_BUDGET_S=174` (R1899: 176→174)
- `PEER_FALLBACK_TIMEOUT=122`
- `EMPTY_200_FASTBREAK=1`
- `KEY_COOLDOWN_S=60`, `TIER_COOLDOWN_S=60`

### 预算分析
- UPSTREAM=32 + PEER=122 = 154 < 174 (20s margin → 18s margin after change)
- OK max=19.6s(dsv4p) << 32s UPSTREAM safe
- 17 zombie 全NVCF空200, FASTBREAK=1 已快速break, BUDGET cap 缩短更快失败

## 变更
- `TIER_TIMEOUT_BUDGET_S`: 174→172 (-2s)
- 理由: 2s 渐进压缩 zombie 失败路径 global budget cap, 成功路径不受影响 (OK max=19.6s << 32s UPSTREAM << 172s BUDGET)
- 约束: 32+122=154<172 (18s margin ✓)
- 单参数; 铁律:只改HM1不改HM2

## 验证
- compose 修改确认: `TIER_TIMEOUT_BUDGET_S: "172"` (line 490)
- 容器重启: `docker compose up -d nv_gw` → Recreated/Started OK
- env 确认: `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S` → `172`
- 日志: 无错误, normal startup
## ⏳ 轮到HM1优化HM2
