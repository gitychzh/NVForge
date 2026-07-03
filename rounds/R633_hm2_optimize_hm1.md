# R633: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R632 验证数据**: 容器先前已运行 ~8h，regime 持续健康
- **DB regime 统计 (R632 部署后)**:
  - 1h: 142 req / 142 OK (100% SR), 0 fail, key_cycle_429s = 0
- **upstream 路径 (R632 regime, 1h)**:
  - `nv_integrate` / `kimi_nv`: 61/61 零错误，avg duration 65.0s
  - `nvcf_pexec` / `glm5_2_nv`: 81/81 零错误，avg duration 4.5s
- **docker logs**: clean start，零 ERROR / WARN；NV-unified proxy 正常启动
- **env 确认 (变更前)**: `MIN_OUTBOUND_INTERVAL_S=0.25`
- **关键信号**: integrate 与 pexec 路径均零错误，全局 key_cycle_429s=0， regime 完全健康

## 优化计划

- **单参数变更**: `MIN_OUTBOUND_INTERVAL_S` 0.25 → 0.20 (-0.05s)
- **决策依据**: R632 deploy 后零错误 regime 持续 (1h 142req/142OK, 0fail, 0key_cycle_429s); 0.25s 已完全验证安全，继续压近以进一步减少请求间 throttle 间隔
- **理由**: KEY_COOLDOWN_S=25 >> 0.20，零 429 风险；减少 outbound 排队时间提升 throughput；integrate 与 pexec 路径均无错误，持续微修成功路径延迟；单参数每轮只改 HM1 配置

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 424-425 区间):
   - `MIN_OUTBOUND_INTERVAL_S: "0.25"` → `MIN_OUTBOUND_INTERVAL_S: "0.20"`
   - 插入行 R633 注释
2. **备份**: `cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R633`
3. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动并 healthy (~14s)
4. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `MIN_OUTBOUND_INTERVAL_S=0.20`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R632) | 目标 (R633) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 0 | 0 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| 请求间间隔 | 0.25s | 0.20s (-0.05s) |

## ⏳ 轮到HM1优化HM2
