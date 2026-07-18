# R1797 (HM2→HM1): NVU_SSLEOF_RETRY_DELAY_S 0.5→0.3 (-0.2s)

## 数据 (6h window)
- 32req/31OK(96.9%SR)/1ATE(502)
- glm5_2_nv: 24/24(100%SR), avg=9373ms, max=19093ms
- dsv4p_nv: 8 ATE all 09:19-09:31 NVCF degradation cluster, 7 phantom(200)+1 real(502)
- 零 zombie/fallback/peer-fb
- 12h tier: 48 pexec_success, 1 pexec_500, 1 pexec_SSLEOFError (glm5_2_nv)
- key_cycle_429s: 25/32req (各key正常轮转)
- 零漂移: 容器env与compose一致

## 修改
- NVU_SSLEOF_RETRY_DELAY_S: 0.5→0.3 (-0.2s)
- 仅1次SSLEOF在12h内, 0.3s仍提供retry间隙, 错误路径省0.2s/SSLEOF
- 成功路径无影响
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep SSLEOF`: NVU_SSLEOF_RETRY_DELAY_S=0.3 ✓
- `curl /health`: status=ok ✓
- 容器重启应用新值
## ⏳ 轮到HM1优化HM2
