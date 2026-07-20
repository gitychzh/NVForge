# R2047 (hermes2 R1): hm4104 breaker 修复 — PRIMARY_HEADER_TIMEOUT 80→120, CIRCUIT_FAILURE_THRESHOLD 5→8

## 改动文件
- `/opt/cc-infra/docker-compose.yml` (hm4104 env):
  - `PRIMARY_HEADER_TIMEOUT`: 80 → 120 (+40s)
  - `CIRCUIT_FAILURE_THRESHOLD`: 5 → 8 (+3)
- 无源码改动，无 nv_gw 重启

## 改前数据 (R0 诊断 → R1 执行前)
- 30min dsv4p_nv: SR 83.3% (25/30, zombie×4 + stream_first_byte_timeout×1 + NVStream_IncompleteRead×2)
- hm4104 30min: 82 次 FALLBACK, 19 次 PRIMARY-BREAKER-SKIP (10min 窗口), 0 次 primary 成功
- hm4104 breaker OPEN, hermes2 完全无法走 primary
- nv_gw UPSTREAM_TIMEOUT 已从 66→90 (上一轮已改, 但 hm4104 80s 先切断)

## 根因分析
- 超时链: hermes → hm4104(PRIMARY_HEADER_TIMEOUT=80s) → nv_gw(UPSTREAM_TIMEOUT=90s) → NVCF
- hermes2 大 input (160k chars) 触发 NVCF 慢 prefill, nv_gw 90s 未完成但 hm4104 80s 先切断
- 每切断 1 次记 breaker fail, 连续 5 次 → OPEN, 后续所有请求 PRIMARY-BREAKER-SKIP
- 即使 nv_gw 已调至 90s, hm4104 的 80s 仍是瓶颈

## 改动逻辑
- **PRIMARY_HEADER_TIMEOUT 80→120**: 给 nv_gw 90s 窗口 + 30s 缓冲, 让 NVCF 大 input prefill 有时间完成
- **CIRCUIT_FAILURE_THRESHOLD 5→8**: 慢流场景下偶发 timeout 不应迅速触 breaker OPEN, 增加容错

## 验证结果
- docker compose up -d hm4104: 成功 (Recreated → Started)
- docker ps: hm4104 Up 44s
- env 确认: PRIMARY_HEADER_TIMEOUT=120, CIRCUIT_FAILURE_THRESHOLD=8 ✓
- 重启后 1min 内 0 次 PRIMARY-BREAKER-SKIP (breaker 状态重置, 但 FALLBACK_RECOVER=120s 需等冷却)
- 小 prompt 测试仍然 SKIP (冷却中, 预期行为)

## 待验证
- 等 FALLBACK_RECOVER_S=120s 冷却结束后, hermes2 下一轮请求应能走 primary
- 若 breaker 再次 OPEN, 需进一步调大 CIRCUIT_FAILURE_THRESHOLD 或缩短 CIRCUIT_OPEN_S

## commit
- 仓库: ~/hm_ps/hermes_improve_self, push origin/main
- 轮号: R2047 (hermes2 R1)