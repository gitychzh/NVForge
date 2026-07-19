# R1899 (HM2→HM1): TIER_TIMEOUT_BUDGET_S 176→174 (-2s)

## 数据
- **6h窗口**: R1898 post-deploy
- **总请求**: 46 (37 glm5_2 + 9 dsv4p)
- **SR**: 54.3% (25/46 OK)
- **失败**: 21 zombie_empty_completion (glm5_2=19, dsv4p=2) — 全部NVCF empty200
- **phantom ATE**: 有 (empty_200 rescue, all status=200)
- **peer-fallback**: 0次 (zombie立即检测, FASTBREAK=1)
- **OK max**: dsv4p=19559ms, glm5_2=16462ms, both < 34s UPSTREAM safe
- **OK avg**: dsv4p=9057ms, glm5_2=7518ms
- **UPSTREAM=34+PEER=122=156<174 (18s margin) ✓**

## 优化
- **TIER_TIMEOUT_BUDGET_S**: 176→174 (-2s)
- 继续UPSTREAM/BUDGET交替削减模式 (R1898 cut UPSTREAM, R1899 cut BUDGET)
- 2s cut from BUDGET headroom; zombie detection already at FASTBREAK=1, no peer-fb triggered
- OK max=19.6s << 174s, safe
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S`: 174 ✓
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 34 ✓
- compose line 490: TIER_TIMEOUT_BUDGET_S: "174" ✓
- 容器重启后参数一致, 无漂移 ✓
## ⏳ 轮到HM1优化HM2
