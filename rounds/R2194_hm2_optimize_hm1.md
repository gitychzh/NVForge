# R2194 (HM2→HM1): KEY_COOLDOWN_S 16→14 (-2s)

## 数据收集 (6h)
- **Total**: 27 req, 19 OK (70.4% SR), 8 zombie, 0 ATE
- **Models**: 全部 glm5_2_nv
- **OK latency**: avg 16,226ms, range 6,205-24,072ms
- **Zombie**: 8/8 zombie_empty_completion (NVCF function-level empty-200), 输入 265K-274K chars
- **Tier attempts**: 27 pexec_success, 9 SSLEOF, 4 429, 1 timeout
- **429 cycling**: 100% 请求触发 key 轮转; avg 1.5 cycles/req
- **Peer-fallback**: 0 触发
- **ATE**: 0 (consecutive 0 ATE streak)
- **Paired pattern**: 请求成对到达(间隔10-20s), 每30min一波, 低流量 ~4.5 req/h

## 优化计划
- **参数**: KEY_COOLDOWN_S 16→14 (-2s)
- **理由**: 交替 KEY→TIER 模式 (R2193 改 TIER→KEY, R2194 改 KEY)。低流量下 5 key 轮转冗余充足, 14s 仍远低于 per-key RPM 恢复窗口
- **预算**: KEY+TIER+GLM5_2=14+4+28=46 << 153 BUDGET (107s 余量)
- **铁律**: 只改HM1不改HM2; 单参数每轮

## 执行
- 编辑 `/opt/cc-infra/docker-compose.yml` line 500: KEY_COOLDOWN_S 16→14
- `docker compose stop nv_gw && docker compose up -d nv_gw` 重启容器
- 验证: `docker exec nv_gw env` 确认 KEY_COOLDOWN_S=14, TIER_COOLDOWN_S=4
- 验证: `/health` 返回 ok, container healthy

## ⏳ 轮到HM1优化HM2
