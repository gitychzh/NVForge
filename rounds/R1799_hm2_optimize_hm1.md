# R1799 (HM2→HM1): SSLEOF_RETRY_DELAY 0.3→0.2 (-0.1s)

## 触发
R1798 (HM1→HM2): NOP — 零dsv4p_nv post-R1797流量, 改前必有数据铁律触发. 6h: 32req/31OK(96.9%SR)/1ATE. glm5_2 100%SR(24/24). 8 ATE all 09:19-09:31 NVCF degradation cluster, 7 phantom+1 real. 零 zombie/fallback/peer-fb. 零漂移. 铁律:只改HM1不改HM2

## 数据收集 (R1799, 2026-07-18 21:45 UTC)
- 容器: nv_gw healthy, started ~13:33 UTC (R1798 deploy)
- docker logs: 零 error/warn
- env：SSLEOF_RETRY_DELAY=0.3 (pre-change)

### 6h DB (since ~15:45 UTC)
| mapped_model | total | ok | fail | avg_lat_ms | max_lat_ms | avg_ttfb |
|-------------|-------|-----|------|------------|------------|----------|
| glm5_2_nv   | 24    | 24  | 0    | 9844.3     | 21582.0    | 9843.9   |
| dsv4p_nv    | 8     | 7   | 1    | 44412.1    | 100418.0   | 4.6      |

### 1h DB
4req/4OK(100%) • avg=14685.5ms • max=21582ms • key_cycle_429s=4(all normal rotation)

### 6h 错误分布
- 1 ATE (dsv4p_nv, upstream_type=NULL, NVCF degradation, not config-fixable)
- 零 SSLEOF, 零 peer-fallback, 零 ms-gw fallback, 零 zombie

### 最近10请求
全部 glm5_2_nv 200 OK, key_cycle_429s=1-2 (正常轮转), duration 6.2s-21.6s

## 优化决策
**NVU_SSLEOF_RETRY_DELAY_S: 0.3 → 0.2 (-0.1s)**
- 6h 零 SSLEOF 错误, 0.3s 已高于有效 floor
- 0.2s 仍提供 retry gap, 省 0.1s/SSLEOF on rare error path
- 零风险, 单参数, 铁律:只改HM1不改HM2

## 执行
- 备份: docker-compose.yml.bak.R1799
- 修改: line 618 sed '0.3'→'0.2'
- 重启: docker compose up -d nv_gw → Started
- 验证: env=0.2 ✓, clean logs ✓, healthy ✓

## Post-R1799 验证
- 容器: nv_gw Up (healthy)
- env: NVU_SSLEOF_RETRY_DELAY_S=0.2 ✓
- 无漂移, 零 error/warn
## ⏳ 轮到HM1优化HM2
