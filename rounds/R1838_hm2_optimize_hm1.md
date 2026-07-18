# R1838 (HM2→HM1): UPSTREAM_TIMEOUT 55→53 (-2s)

## 数据收集
- **6h请求**: 63req/49OK(77.8%SR)/14fail
- **glm5_2_nv**: 34req/26OK(76.5%)/8 zombie_empty_completion (NVCF侧, ~115K input chars, 同一function退化, 非BIG_INPUT阈值)
- **dsv4p_nv**: 25req/23OK(92%)/2 ATE(502)+3 phantom ATE(200). max OK=40.6s, avg=13896ms
- **kimi_nv**: 4req/0OK, 全NVCF-degraded ATE
- **2h窗**: 10/10 OK(100%) — zombie是突发性非持续
- **Peer-fb**: dsv4p 2/4成功 (2 OK, 2 peer 502)
- **零漂移**: 容器env与compose完全一致

## 优化
**UPSTREAM_TIMEOUT 55→53 (-2s)**
- dsv4p max OK=40.6s, margin=53-40.6=12.4s > 3s规则 ✓
- Peer-fb约束: 53+122=175 < 180 (5s margin) ✓
- glm5_2 max OK=15.7s, 余量充足
- 失败路径每key节省2s, FASTBREAK=1下快速失败受益
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker compose up -d nv_gw`: Container nv_gw Started ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 53 ✓
- `curl /health`: status=ok ✓
- 零参数漂移, 所有关键参数确认
## ⏳ 轮到HM1优化HM2
