# R1900 (HM2→HM1): UPSTREAM_TIMEOUT 34→32 (-2s)

## 数据
- **6h窗口**: R1899 post-deploy
- **总请求**: 45 (36 glm5_2 + 9 dsv4p)
- **SR**: 62.2% (28/45 OK) ↑ from R1899 54.3%
- **失败**: 17 zombie_empty_completion (glm5_2=15, dsv4p=2) — 全部NVCF empty200
- **phantom ATE**: 有 (all_tiers_exhausted+status=200, empty_200 rescue)
- **peer-fallback**: 0次 (zombie FASTBREAK=1立即检测)
- **OK max**: dsv4p=19559ms, glm5_2=16462ms, both < 32s safe ✓
- **OK avg**: dsv4p=11400ms, glm5_2=7151ms
- **UPSTREAM=32+PEER=122=154<174 (20s margin) ✓**

## 优化
- **UPSTREAM_TIMEOUT**: 34→32 (-2s)
- 继续UPSTREAM/BUDGET交替削减模式 (R1898: UPSTREAM 36→34, R1899: BUDGET 176→174, R1900: UPSTREAM 34→32)
- 2s cut from UPSTREAM; zombie FASTBREAK=1 already, peer-fb not triggered
- OK max=19.6s << 32s, safe
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 32 ✓
- `docker exec nv_gw env | grep TIER_TIMEOUT_BUDGET_S`: 174 ✓
- compose line 488: UPSTREAM_TIMEOUT: "32" ✓
- 容器 rebuild (up -d) 后参数一致, 无漂移 ✓
- health: {"status":"ok"} ✓
## ⏳ 轮到HM1优化HM2
