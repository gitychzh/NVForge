# R2193 (HM2→HM1): TIER_COOLDOWN_S 6→4 (-2s)

## 数据收集 (6h)
- **Total**: 27 req, 20 OK (74.1% SR), 7 zombie, 0 ATE
- **Models**: 全部 glm5_2_nv
- **OK latency**: avg 14,666ms, range 5,755-24,072ms
- **Zombie**: 7/7 zombie_empty_completion (NVCF function-level empty-200), 输入 265K-274K chars
- **Tier attempts**: 27 pexec_success, 10 SSLEOF, 5 429, 1 timeout, 1 RemoteDisconnected
- **429 cycling**: 100% 请求触发 key 轮转; 分布: 1 cycle=16, 2=7, 3=2, 4=2 (avg 1.63)
- **Peer-fallback**: 0 触发
- **ATE**: 0 (consecutive 0 ATE)

## 优化计划
- **参数**: TIER_COOLDOWN_S 6→4 (-2s)
- **理由**: 交替 TIER→KEY 模式 (R2192 改 KEY 18→16, R2193 改 TIER)。TIER=4 仍提供足够 NVCF 函数级冷却，低流量 4.5req/h 下 tier 级别冷却需求极低
- **预算**: KEY+TIER+GLM5_2=16+4+28=48 << 153 BUDGET (105s 余量)
- **铁律**: 只改HM1不改HM2; 单参数每轮

## 执行
- 编辑 `/opt/cc-infra/docker-compose.yml` line 506: TIER_COOLDOWN_S 6→4
- `docker compose up -d nv_gw` 重启容器
- 验证: `docker exec nv_gw env` 确认 TIER_COOLDOWN_S=4, KEY_COOLDOWN_S=16
- 验证: `/health` 返回 ok

## ⏳ 轮到HM1优化HM2
