# R627: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R626 验证数据**: 容器启动于 2026-07-03T04:31:xxZ 左右（基于 R626 部署记录），截止优化前已稳定运行约 8h
- **DB regime 统计 (最近15min)**: 139 req / 139 OK (100% SR), 0 fail, 0 key_cycle_429s
- **per-model (最近15min)**:
  - `glm5_2_nv`: 80/80 OK, avg ~4.5s
  - `kimi_nv`: 59/59 OK, avg ~68.6s
- **2h 历史**: 241 req 200 OK + 1 old `all_tiers_exhausted` 502 (历史旧regime, 非当前窗口)；`key_cycle_429s=2`（极低，正常轮转）
- **docker logs**: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动
- **关键信号**: `key_cycle_429s=0` 贯穿当前 regime，integrate/pexec 全路径零错误

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 8 → 6 (-2s)
- **决策依据**: R626 deploy 后零错误 regime 持续 (最近15min 139req全200OK, integrate/pexec全路径零错误, `key_cycle_429s=0`)
- **理由**: 6s 继续压近 per-key RPM 安全余量，但 integrate 路径持续零错误证明仍有安全余量；继续微修 integrate coverage gap 以提升 throughput

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "8"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "6"`
   - 插入行 466 R627 注释
2. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动: 2026-07-03T12:38:xxZ
3. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=6`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R626) | 目标 (R627) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 0 | 0 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| throughput | 基础 | +2s tighter key rotation |

## ⏳ 轮到HM1优化HM2
