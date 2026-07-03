# R631: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R630 验证数据**: 容器启动时间 `2026-07-03T05:04:09.86372946Z`，运行期间 regime 持续清洁
- **DB regime 统计 (R630 部署后至重启前)**:
  - 134 req / 134 OK (100% SR)
  - 0 fail
  - key_cycle_429s = 0 (integrate 与 pexec 路径均无 key 轮转冲突)
- **upstream 路径 (R630 regime)**:
  - `nv_integrate` / `kimi_nv`: 全部 200 OK，零错误
  - `nvcf_pexec` / `glm5_2_nv`: 全部 200 OK，零错误
- **docker logs**: clean start，零 ERROR / WARN；NV-unified proxy 正常启动
- **env 确认**: `NV_INTEGRATE_KEY_COOLDOWN_S=1` (R630 设置值)
- **关键信号**: integrate 路径 (kimi) 零错误, pexec 路径 (glm5_2) 零错误, 全局 key_cycle_429s=0， regime 完全健康

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 1 → 0 (-1s)
- **决策依据**: R630 deploy 后零错误 regime 持续 (134/134 OK, integrate 全路径零错误, key_cycle_429s=0, pexec 路径零错误); 1s 已完全验证安全，继续压至 0s 以彻底消除 integrate key 轮转等待，最大化 throughput
- **理由**: 持续微修 integrate coverage gap；历史 600+ 轮从 64s 逐步降至 1s 全部零错误，证明 integrate 路径有充分安全余量；单参数每轮只改 HM1 配置

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "1"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "0"`
   - 插入行 R631 注释
2. **备份**: `cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R631`
3. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动并 healthy (~11s)
4. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=0`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R630) | 目标 (R631) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 0 | 0 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| throughput | 基础 | 移除 key 轮转等待 |

## ⏳ 轮到HM1优化HM2
