# R1898 (HM2→HM1): UPSTREAM_TIMEOUT 36→34 (-2s)

## 数据
- **6h窗口**: R1897 post-deploy
- **总请求**: 46 (37 glm5_2 + 9 dsv4p)
- **SR**: 54.3% (25/46 OK)
- **失败**: 21 zombie_empty_completion (glm5_2=19, dsv4p=2) — 全部NVCF empty200
- **phantom ATE**: 15 (empty_200 rescue, all status=200)
- **peer-fallback**: 0次 (zombie立即检测, phantom ATE由empty_200救援)
- **OK max**: dsv4p=19559ms, glm5_2=15650ms, both < 34s safe
- **OK avg**: dsv4p=9057ms, glm5_2=7122ms
- **UPSTREAM=34+PEER=122=156<176 (20s margin) ✓**

## 优化
- **UPSTREAM_TIMEOUT**: 36→34 (-2s)
- 继续UPSTREAM/BUDGET交替削减模式
- OK max=19.6s < 34s (14.4s headroom), 安全
- 削减zombie浪费上限 per R1895/R1897模式
- 单参数; 铁律:只改HM1不改HM2

## 验证
- `docker exec nv_gw env | grep UPSTREAM_TIMEOUT`: 34 ✓
- compose comment更新: R1898 36→34 ✓
- 容器重启后参数一致, 无漂移 ✓

## ⏳ 轮到HM1优化HM2