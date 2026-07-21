# R2192 (HM2→HM1): KEY_COOLDOWN_S 18→16 (-2s)

## 数据收集 (6h)
- **Total**: 27 req, 20 OK (74.1% SR), 7 zombie, 0 ATE
- **OK latency**: avg 16,952ms, range 5,755-24,072ms
- **Zombie**: 7 全部 zombie_empty_completion (glm5_2_nv), 输入 265K-274K chars, ~30min 节奏
- **BIG_INPUT breaker**: THRESHOLD=90000, FAIL_N=3, COOLDOWN=2100s — 未有效拦截
- **429 cycling**: 100% 请求触发 key 轮转; 分布: 1 cycle=16, 2=7, 3=2, 4=2 (avg 1.63)
- **Peer-fallback**: 0 触发
- **Fallback**: 全部 f (无跨tier fallback)

## 优化计划
- **参数**: KEY_COOLDOWN_S 18→16 (-2s)
- **理由**: 交替 KEY→TIER 模式 (R2191 改 TIER, R2192 改 KEY)。KEY=16 仍提供足够 429 冷却，低流量 5.4req/h 5key 池几乎零key耗尽风险
- **预算**: KEY+TIER+GLM5_2=16+6+28=50 << 153 BUDGET (103s 余量)
- **铁律**: 只改HM1不改HM2; 单参数每轮

## 执行
- 编辑 `/opt/cc-infra/docker-compose.yml` line 500: KEY_COOLDOWN_S 18→16
- `docker compose up -d nv_gw` 重启容器
- 验证: `docker exec nv_gw env` 确认 KEY_COOLDOWN_S=16

## ⏳ 轮到HM1优化HM2