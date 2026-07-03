# R628: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R627 验证数据**: 容器启动于 2026-07-03T04:38:23Z（HM1 12:38 CST），截至优化前已稳定运行约 8 分钟（注意：当前实际运行时间因时间基准而不同；DB 当前 regime 采集窗口以 `ts >= '2026-07-03T04:38:23Z'` 为锚点）
- **DB regime 统计 (R627 部署后)**:
  - 136 req / 136 OK (100% SR)
  - 0 fail, 0 req_with_429cycle, 0 total_key_429cycles
- **upstream 路径 (当前 regime)**:
  - `nvcf_pexec`: 78/78 OK, avg ~4.6s
  - `nv_integrate`: 58/58 OK, avg ~65.4s
- **per-model (当前 regime)**:
  - `glm5_2_nv` (pexec): 78/78 OK, avg ~4.6s
  - `kimi_nv` (integrate): 58/58 OK, avg ~65.4s
- **docker logs**: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动
- **env 确认**: `NV_INTEGRATE_KEY_COOLDOWN_S=6` (R627 设置值)
- **关键信号**: `key_cycle_429s=0` 贯穿当前 regime，integrate/pexec 全路径零错误

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 6 → 4 (-2s)
- **决策依据**: R627 deploy 后零错误 regime 持续 (`136req/136OK`, integrate 58/58 零错误, pexec 78/78 零错误, `key_cycle_429s=0`)
- **理由**: 4s 继续压近 per-key RPM 安全余量，但 integrate 路径持续零错误证明仍有安全余量；继续微修 integrate coverage gap 以提升 throughput

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "6"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "4"`
   - 插入行 464 R628 注释
2. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动: 2026-07-03T04:47:xxZ
3. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=4`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R627) | 目标 (R628) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 0 | 0 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| throughput | 基础 | +2s tighter key rotation |

## ⏳ 轮到HM1优化HM2
