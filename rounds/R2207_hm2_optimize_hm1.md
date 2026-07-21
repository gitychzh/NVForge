# R2207 — HM2 优化 HM1

**日期**: 2026-07-22  
**触发**: HM1 提交新 commit (R2205: KEY_COOLDOWN 6) → 脚本检测 HM1 改动 → 轮到 HM2 优化 HM1  
**角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname@100.109.153.83)  
**铁律**: 只改 HM1 配置，绝不改 HM2 本地

## 数据采集 (HM1 6h)
- 总请求: 31 (20 OK / 11 fail, 64.52% SR)
- 模型分布: glm5_2_nv 27 (17 OK / 10 zombie), dsv4p_nv 4 (3 OK / 1 zombie)
- 错误类型: 11 zombie_empty_completion (10 glm5_2 + 1 dsv4p), 0 ATE, 0 peer-fallback
- p50 OK 延迟: glm5_2_nv ~12695ms, dsv4p_nv ~27457ms
- **429 循环: 87.10% (27/31)**, glm5_2_nv 100% (27/27) 全部 key_cycle_429s≥1
- tier_attempts: glm5_2_nv pexec_success=27, pexec_SSLEOFError=7, pexec_429=7, pexec_timeout=4
- docker logs: 无 error/warn (最近 100 行仅 6 行输出)

## 根因分析
R2206 将 KEY_COOLDOWN_S 从 6→0，但 KEY=0 + TIER=1 的组合在低流量 (5.2 req/h) 下造成严重 429 循环:
- 每请求 key1 立即 429 → key2 也可能 429 (NVCF 同函数 rate limit 窗口未过)
- 87.1% 请求至少 1 次 429，mean 1.9 cycles/req
- R2126 历史数据: 66=zero-429, 64=58% 429 — 该函数 429 安全边界 >64s ≤66s
- KEY=0 在 anti-pattern 区 (1-65s)，比 66s 更差

## 修改
| 参数 | 文件 | 旧值 | 新值 | 变化 |
|------|------|------|------|------|
| KEY_COOLDOWN_S | /opt/cc-infra/docker-compose.yml:500 | 0 | 66 | +66s |

**依据**: R2126 验证 66s 为该 NVCF 函数的 zero-429 安全值 (64s=58% 429, 66s=0%)。  
**预算**: KEY+TIER=66+1=67 << 153 BUDGET (86s margin) ✓  
**单参数**: 遵循少改多轮原则

## 验证
- `docker exec nv_gw env | grep KEY_COOLDOWN_S` → KEY_COOLDOWN_S=66 ✓
- 容器名: nv_gw
- `docker logs nv_gw --tail 20` → 无异常

## ⏳ 轮到HM1优化HM2