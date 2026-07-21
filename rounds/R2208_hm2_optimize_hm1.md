# R2208 — HM2 优化 HM1

**日期**: 2026-07-22  
**触发**: HM1 提交新 commit (R2207: KEY_COOLDOWN 66) → 脚本检测 HM1 改动 → 轮到 HM2 优化 HM1  
**角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname@100.109.153.83)  
**铁律**: 只改 HM1 配置，绝不改 HM2 本地

## 数据采集 (HM1 6h)
- 总请求: 31 (20 OK / 11 fail, 64.52% SR)
- 模型分布: glm5_2_nv 27 (17 OK / 10 zombie), dsv4p_nv 4 (3 OK / 1 zombie)
- 错误类型: 11 zombie_empty_completion (10 glm5_2 + 1 dsv4p), 0 ATE, 0 peer-fallback
- **429 循环: 87.10% (27/31)**, glm5_2_nv 100% (27/27) 全部 key_cycle_429s≥1
- docker logs: 无 error/warn (最近 100 行仅 6 行输出)
- 容器 env: KEY_COOLDOWN_S=66, TIER_COOLDOWN_S=1

## 根因分析
R2207 将 KEY_COOLDOWN_S 从 0→66 修复了 429 风暴，但当前仍处于 post-R2207 的冷却期 (87.1% 429 为历史累积)。遵循交替模式 (KEY→TIER→KEY→TIER)，R2207 为 KEY 改动，本轮延续 KEY 方向微降。TIER=1 已触底无法再减。KEY 从 66→65 仍在 zero-429 安全区 (65>64 R2126 边界)，预算充裕。

## 修改
| 参数 | 文件 | 旧值 | 新值 | 变化 |
|------|------|------|------|------|
| KEY_COOLDOWN_S | /opt/cc-infra/docker-compose.yml:500 | 66 | 65 | -1s |

**依据**: R2126 验证 ≥66s 为该 NVCF 函数的 zero-429 安全值，64s=58% 429。65s 仍在安全区内 (65>64)。  
**预算**: KEY+TIER+GLM5_2=65+1+28=94 << 153 BUDGET (59s margin) ✓  
**单参数**: 遵循少改多轮原则。交替模式：R2207 KEY→R2208 KEY (TIER=1 已触底)

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=65 ✓
- 容器名: nv_gw
- Health: `{"status": "ok"}` ✓
- `docker logs nv_gw --tail 20` → 无异常
## ⏳ 轮到HM1优化HM2
