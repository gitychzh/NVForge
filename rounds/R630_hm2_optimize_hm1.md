# R630: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R629 验证数据**: 容器运行期间 regime 持续清洁; DB 最近 2h 聚合如下
- **DB regime 统计 (R629 部署前 2h)**:
  - 199 req / 198 OK (99.5% SR)
  - 1 fail (`all_tiers_exhausted`, upstream_type 为空, 调度层直接拒, 非 integrate 路径错误)
  - key_cycle_429s = 1 (pexec 路径正常轮转, 非致命)
- **upstream 路径 (R629 部署前 2h)**:
  - `nvcf_pexec` / `glm5_2_nv`: 103/103 OK, 零错误
  - `nv_integrate` / `kimi_nv`: 95/95 OK, 零错误
  - `nv_integrate` / `dsv4p_nv`: 包含于 integrate 统计, 零错误
- **docker logs**: clean start (R630 recreate 前), 零 ERROR / WARN; NV-unified proxy 正常启动
- **env 确认**: `NV_INTEGRATE_KEY_COOLDOWN_S=2` (R629 设置值)
- **关键信号**: integrate 路径 (kimi+dsv4p) 95/95 零错误, kc429=1 (pexec 正常轮转); pexec 路径 103/103 零错误

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 2 → 1 (-1s)
- **决策依据**: R629 deploy 后零错误 regime 持续 (integrate 全路径零错误, key_cycle_429s 维持低位, pexec 路径零错误); 1s 继续压近 per-key RPM 安全余量, 历史连续多轮零错误证明 integrate 路径仍有安全余量
- **理由**: 继续微修 integrate coverage gap 以提升 throughput; 单参数每轮只改 HM1 配置

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "2"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "1"`
   - 插入行 R630 注释
2. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动并 healthy (~11s)
3. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=1`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R629) | 目标 (R630) |
|---|---|---|
| 错误数 | 0 (integrate) / 1 (ate, 非 integrate) | 0 |
| key_cycle_429s | 1 (pexec 正常轮转) | ≤1 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| throughput | 基础 | +1s tighter key rotation |

## ⏳ 轮到HM1优化HM2
