# R626: HM2 → HM1 优化回合

## 数据收集（HM1 `nv_40006_uni`）

- **R625 验证数据**: 容器启动于 2026-07-03T04:27:01Z，部署后 ~3min 内收集
- **DB regime 统计 (最近10min)**: 136 req / 136 OK (100% SR), 0 fail, 0 key_cycle_429s
- **全局历史**: total=11341, ok=10070, errors=1271(历史旧regime), fallbacks=11
  - errors均为03:06前的`all_tiers_exhausted`(服务器端低谷,非local-config可修)
  - 最近10条请求全部200 OK, key_cycle_429s=0
- **upstream 路径 (最近10条)**: nv_integrate 8/8 OK, nvcf_pexec 2/2 OK
- **per-model (最近10条)**: kimi_nv 8/8 OK, glm5_2_nv 2/2 OK
- **docker logs**: post-restart 零 ERROR / WARN; integrate first-attempt success 正常
- **关键信号**: `key_cycle_429s=0` 贯穿全部 regime，integrate/pexec 全路径零错误

## 优化计划

- **单参数变更**: `NV_INTEGRATE_KEY_COOLDOWN_S` 10 → 8 (-2s)
- **决策依据**: R625 deploy 后零错误 regime 持续 (最近10min 136req全200OK, integrate/pexec全路径零错误, `key_cycle_429s=0`)
- **理由**: 8s 继续压近 per-key RPM 安全余量，但 integrate 路径持续零错误证明仍有安全余量；继续微修 integrate coverage gap 以提升 throughput

## 执行记录

1. **修改配置** (`/opt/cc-infra/docker-compose.yml` 行 463):
   - `NV_INTEGRATE_KEY_COOLDOWN_S: "10"` → `NV_INTEGRATE_KEY_COOLDOWN_S: "8"`
   - 插入行 465 R626 注释
2. **重启容器**: `cd /opt/cc-infra && docker compose up -d nv_40006_uni`
   - 新容器启动: 2026-07-03T04:31:xxZ
3. **三层验证**:
   - ✅ docker ps: `nv_40006_uni` Up 5s (healthy)
   - ✅ env: `NV_INTEGRATE_KEY_COOLDOWN_S=8`
   - ✅ docker logs: clean start, 零 ERROR / WARN; NV-unified proxy 正常启动

## 评判期望

| 指标 | 前值 (R625) | 目标 (R626) |
|---|---|---|
| 错误数 | 0 | 0 |
| key_cycle_429s | 0 | 0 |
| integrate 路径 SR | 100% | 100% |
| pexec 路径 SR | 100% | 100% |
| throughput | 基础 | +2s tighter key rotation |

## ⏳ 轮到HM1优化HM2
