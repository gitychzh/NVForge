# R1983 (HM2 cc2) — NOP 巡检 R95, 指数退避冻结第 32 轮

## 数据 (本 session 拉取, 2026-07-20 ~05:4x UTC)

- nv_gw 30min (样本 103): 200×99 / 502×4 → **SR = 96.12%** (小样本偏稳)
- nv_gw 6h (样本 751): 200×714 / 502×37 → **SR = 95.07%** (大样本稳态)
  - **与 R1979 6h 95.09% -0.02pp 几乎 0 漂移** (R1978→R1979 +0.28pp / R1979→R1983 -0.02pp, 区间内非退化)
- 30min 502=4 全 NVCF 上游侧已知类: **zombie_empty_completion×3 + stream_first_byte_timeout×1**
  (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空; R1979 是 zombie×5+fbt×1, 本轮 zombie×3 -2 + fbt×1 一致)
- 6h 502=37 全已知类: **zombie×24 (R1979 24 同) + all_tiers_exhausted×7 (R1979 7 同) + first_byte_timeout×6 (R1979 6 同)**
  - **与 R1979 6h 几乎 0 漂移 (zombie 0, ATE 0, fbt 0 — 完全一致)**, 无新可配置类
- **abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 持续归零)
- 持久化层 (30min tier_attempts): pexec_success×62 (nv_gw 转发层稳, 无 429)
- **fallback 4/30min 全 FALLBACK-OK**, 0 真中断, 0 fallback 失败
  - 全 4 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - ms 救回: 3490/2370/5123/3299ms
  - `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → 0 真中断
  - **120s 跑满类本轮 0** (R1951 4 → R1953 2 → R1954 0 → ... → R1979 0 → R1983 0, 持续趋稳)
- breaker: cc4101 PRIMARY-BREAKER-OPEN 30min=0 / nv_gw NV-ANTH-BREAKER-FAIL 30min=3 (**但 state 全 CLOSED**: 1/0, 2/0, 2/0 — 只记 failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN)
  - breaker **OPEN 0 连续多轮**
- **BUG-A 修复 (R1913) 真实生效**: 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (R1979 5, 本轮 4 区间内波动)

## 验证

- env 无漂移 (与 R1979 完全一致; NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)
- docker ps 全 Up (nv_gw Up 8h, cc4101 Up 9h, ms_gw Up 2d, logs_db Up 3d)
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926)
- **0 改动 0 restart**

## 决策: NOP 巡检 R95, 介入四条全不满足

1. 6h SR95.07% 大样本稳态 (与 R1979 6h 95.09% -0.02pp 几乎 0 漂移), 30min 96.12% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+first_byte_timeout 已知类 (与 R1979 几乎 0 漂移完全一致), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 3 条但 state=CLOSED 不 OPEN
4. fallback 4/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

**指数退避激活决策仍冻结 (连续第 32 轮)**: R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立。env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立。当前链路稳态 + 本轮无新监督者激活指令 → 继续冻结。

## commit

本轮 0 改动 0 restart, 仅 round 文件 + STATE 覆写。peer HM1 agent 已到 R1982, 本轮用 R1983 前缀 hm2_cc2 (与 peer R1982_hm2_optimize_hm1.md 文件名独立不撞号)。
