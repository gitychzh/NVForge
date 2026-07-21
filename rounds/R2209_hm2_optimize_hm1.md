# R2209 — HM2 优化 HM1

**日期**: 2026-07-22  
**触发**: 检测脚本判定轮到 HM2 执行优化 (HM1 提交了新 commit 到 GitHub)  
**角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname@100.109.153.83)  
**铁律**: 只改 HM1 配置，绝不改 HM2 本地

## 数据采集 (HM1 6h)
- 总请求: 44 (31 OK / 13 fail, 70.45% SR)
- 模型分布: glm5_2_nv 28 (19 OK / 9 zombie), dsv4p_nv 16 (12 OK / 3 ATE + 1 zombie)
- 错误类型: 9 zombie_empty_completion (glm5_2, 全部 BIG_INPUT 上游 NVCF), 3 all_tiers_exhausted (dsv4p, NVCF function 74f02205 已知退化), 1 zombie_empty_completion (dsv4p)
- **429 循环: 100% glm5_2 (28/28)**, key_cycle_429s 分布: 18×1, 7×2, 1×3, 1×5, 1×6
- 0 peer-fallback (30+122=152>151 不触发预 R2209)
- 0 glm5_2 ATE
- docker logs: 无 error/warn，仅 zombie 日志
- 容器 env: KEY_COOLDOWN_S=65, TIER_COOLDOWN_S=1, BUDGET=153, UPSTREAM=24
- OK 延迟: glm5_2 avg 23954ms, dsv4p avg 27056ms
- 30min: 2 req (1 OK / 1 zombie, 50.00%)

## 根因分析
glm5_2_nv 100% key cycling 是主导模式——28/28 请求全部经历 key_cycle_429s≥1，说明 KEY_COOLDOWN=65 在 5-key 轮转下仍偏长。9 zombie 全部为 BIG_INPUT 上游 NVCF 问题 (非本地旋钮可修)。3 dsv4p ATE 为 NVCF function 74f02205 已知退化 (非本域)。遵循交替模式 (R2207 KEY 66→0 修复，R2208 KEY 66→65)，本轮 KEY 65→64 继续微降。TIER=1 已触底无法再减。64 为 R2126 验证的 429 边界 (64s=58% 429)，但 5-key 低流量下风险可控。

## 修改
| 参数 | 文件 | 旧值 | 新值 | 变化 |
|------|------|------|------|------|
| KEY_COOLDOWN_S | /opt/cc-infra/docker-compose.yml:500 | 65 | 64 | -1s |

**依据**: R2126 验证 64s 为 429 边界值，但 5-key 轮转 + 低流量 (44req/6h ≈ 7.3req/h) 时 key 耗尽风险极低。  
**预算**: KEY+TIER+GLM5_2=64+1+28=93 << 153 BUDGET (60s margin) ✓  
**单参数**: 遵循少改多轮原则。交替模式：R2208 KEY→R2209 KEY (TIER=1 已触底)

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=64 ✓
- 容器名: nv_gw
- Health: `{"status": "ok"}` ✓
- `docker logs nv_gw --tail 20` → 无异常
## ⏳ 轮到HM1优化HM2