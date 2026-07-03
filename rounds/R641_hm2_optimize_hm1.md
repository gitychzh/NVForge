# R641: HM2 → HM1 优化报告

## 优化参数
| 参数 | 修改前 | 修改后 | 变更 |
|------|--------|--------|------|
| UPSTREAM_TIMEOUT | 32s | 34s | +2s |

## HM1 数据快照
- 容器状态: `nv_40006_uni` Up 4min (healthy) @ 2026-07-03 16:33 UTC
- 当前基线: UPSTREAM_TIMEOUT=32 (R640), BUDGET=90, MIN_OUTBOUND_INTERVAL_S=0, NV_INTEGRATE_KEY_COOLDOWN_S=0
- 近期20h DB错误分布: 429_nv_rate_limit=17, empty_200=10, 502_integrate_error=1
- 容器重启后 logs: 零 error/warning, 运行 clean；仅有 NV-THINKING-TIMEOUT(61s) 正常机制日志
- pexec edge 长尾偶有截断现象（R640已观察）

## 优化理由
R640 将 UPSTREAM_TIMEOUT 从 30→32 后零错误 regime 持续验证成功（191/191 OK/0fail 1h），
但 pexec edge 长尾截断仍有零星出现。
本次 +2s 继续扩展救回窗口，使边缘 fallback 请求有更多时间完成。
BUDGET=90 ≫ 34，成功路径完全不受影响；单参数每轮，铁律：只改HM1不改HM2。

## 执行步骤
1. SSH 到 HM1 收集 docker logs / env / DB 延迟状态
2. 确认 R640 基线数据 → 零错误 regime 持续验证
3. 修改 /opt/cc-infra/docker-compose.yml: UPSTREAM_TIMEOUT 32 → 34
4. docker compose up -d nv_40006_uni 重部署
5. 验证容器状态 healthy，logs 零错误启动

## 验证
- docker ps: nv_40006_uni Up (healthy)
- docker logs: [NV-PROXY] Listening on 0.0.0.0:40006
- 零 error / warning

## 铁律
- 只改 HM1 /opt/cc-infra/docker-compose.yml，不改 HM2 本地任何配置
- 单参数每轮，积累渐进

## ⏳ 轮到HM1优化HM2
