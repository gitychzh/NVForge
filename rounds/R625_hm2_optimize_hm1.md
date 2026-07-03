# R625: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R624 验证数据**: 容器启动于 2026-07-03T04:22:39Z，部署后 ~3min 内收集
- **DB regime 统计**: 136 req / 136 OK (100% SR), 0 fail, 0 key_cycle_429s, 0 total_429cycles
- **upstream 路径**: nvcf_pexec 78/78 OK, nv_integrate 58/58 OK
- **per-model**: glm5_2_nv 78/78 OK, kimi_nv 58/58 OK
- **docker logs**: post-restart 零 ERROR / WARN; integrate first-attempt success 正常
- **关键信号**: `key_cycle_429s=0` 贯穿全部 regime，integrate/pexec 全路径零错误

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 12 → 10 (-2s)
- **决策依据**: R624 deploy 后零错误 regime 持续 (integrate/pexec 全路径零错误, 136 req 全 200 OK, `key_cycle_429s=0`)
- **理由**: 10s 继续压近 per-key RPM 安全余量，但 integrate 路径持续零错误证明仍有安全余量；继续微修 integrate coverage gap 以提升 throughput

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "12"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "10"`
   - 插入行 464 R625 注释
2. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动: 2026-07-03T04:27:01Z
3. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up 15s (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=10`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R624) | 目标 (R625) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 0 | 0 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| throughput | 基础 | +2s tighter key rotation |

## ⏳ 轮到HM1优化HM2
