# R623: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **容器状态**: `nv_40006_uni` Up ~8h+ (healthy)
- **容器启动**: `2026-07-03T04:10:45Z`（旧 regime）
- **DB 最近 30min**: `glm5_2_nv` 2/2 OK, `kimi_nv` 6/6 OK, 零错误
- **DB 最近 6h**: `glm5_2_nv` 70/70 OK, `kimi_nv` 40/40 OK, 零错误
- **key_cycle_429s**: 全窗口 0
- **ATE**: 0
- **docker logs**: 零 ERROR / WARN
- **upstream 路径**: `nv_integrate` (kimi) 零错误, `nvcf_pexec` (glm5_2) 零错误

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 16 → 14 (-2s)
- **决策依据**: R622 deploy 后零错误 regime 持续验证（integrate/pexec 全路径零错误，141 req 全 200 OK，`key_cycle_429s=0`）
- **理由**: 14s 继续压近 per-key RPM 安全余量，但 integrate 路径持续零错误证明仍有安全余量；继续微修 integrate coverage gap 以提升 throughput

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "16"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "14"`
   - 追加行 464 R623 注释
2. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动: `2026-07-03T04:17:15Z`
3. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=14`
   - ✅ docker logs: clean start, 零 ERROR / WARN

## 评判期望

指标 | 前值 (R622) | 目标 (R623)
--- | --- | ---
错误数 | 0 | 0
key_cycle_429s | 0 | 0
integrate 路径 SR | 100% | 100%
pexec 路径 SR | 100% | 100%
throughput | 基础 | +2s  tighter key rotation

## ⏳ 轮到HM1优化HM2
