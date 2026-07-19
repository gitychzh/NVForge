# R1987 (HM2 cc2): NOP 巡检 R97 — 30min SR95.06%/6h SR95.64% 0 真中断, 与 R1984 6h +0.42pp 0 漂移微升, 连续冻结第 34 轮延续

## 数据 (本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933, 0 restart)

### 30min 窗口 (nv_gw)
- status: 200×77 / 502×4 → SR = 77/81 = **95.06%** (小样本偏稳; R1984 95.51%, 本轮 -0.45pp 小波动区间内)
- 502 error_type: **zombie_empty_completion×4** (全已知类, glm5_2_nv 出口 IP 段 134.195.101.0/24 同源快回空; R1984 是 zombie×3+fbt×1, 本轮 zombie +1/fbt -1 微调, 0 新类)
- abs_cap 30min = **0** (DB `error_type like '%abs%'` 0 rows; R1918 方案0 持续归零连续多轮)
- tier_attempts 30min: pexec_success×78 (nv_gw 转发层稳, 无 429; R1984 56, 本轮 78 +22 正常区间)

### 6h 窗口 (nv_gw)
- status: 200×746 / 502×34 → SR = 746/780 = **95.64%** (大样本稳态区间; R1960-1987 94.0-96.1% 区间内非退化; **与 R1984 6h 95.22% +0.42pp 0 漂移微升**)
- 502 error_type 全已知类: **zombie×25 (R1984 24, +1) + all_tiers_exhausted×5 (R1984 7, -2) + first_byte_timeout×4 (R1984 6, -1)**
  - 与 R1984: zombie +1 / ATE -2 / fbt -1, 全已知类无新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)

### fallback (cc4101 30min)
- **fallback 3** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 3 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - R1984 fallback 5, 本轮 3 (-2 区间内波动无恶化, R1967 8/R1970 7/R1971 6/R1972 7/R1973 6/R1976 2/R1977 3/R1978 6/R1979 5/R1983 4/R1984 5/R1987 3 区间内)
- ms 救回 3293/4803/1739ms → 0 条 fallback 失败 → CC 收 0 真 502
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → 确认 0 真中断
- **120s 跑满类本轮 0** 持续趋稳归零 (R1951 4→R1953 2→R1954 0→...→R1983 0→R1984 0→R1987 0)
  - 注: 日志 "saves ~120s" 是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/fallback 请求), **非 120s 跑满类**, 不要混淆

### breaker (30min)
- cc4101 PRIMARY-BREAKER-OPEN = **0** (连续多轮)
- nv_gw NV-ANTH-BREAKER-FAIL = **3** 但 state 全 **CLOSED** (`('CLOSED',N,0)` ×3, 只记 failure 未达 5/300s 阈值, 仍 CLOSED 不 OPEN)
  - R1957/R1978/R1979/R1983/R1984 同类抖动, 本轮 3 仍 CLOSED 不 OPEN; breaker **OPEN 0 连续多轮**
- 注: 日志见 `NV-MS-FB-SERVED state=CLOSED` 是 nv_gw 内部 ms_fb 路径 (Point A/B) 记 breaker failure 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关

### BUG-A 修复 (R1913) 真实生效确认
- 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (R1952 6/R1951 1/R1953 5/R1954 4/R1956 2/R1957 1/R1967 2/R1970 4/R1971 5/R1972 6/R1973 5/R1976 2/R1977 2/R1978 4/R1979 5/R1983 4/R1984 5/R1987 4)
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发, 验证 BUG-A 修复长期生效 (省约 ~120s/fallback 请求)

## 改动

**0 改动 0 restart** (NOP 巡检 R97, 连续第 34 轮冻结指数退避延续)。

## 验证

- env 无漂移 (与 R1984 完全一致; NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)
- docker ps 全 Up (nv_gw Up 9h, cc4101 Up 10h, ms_gw Up 2d, logs_db Up 3d)
- nv_gw StartedAt 13:33:43Z (0 restart 维 R1933), cc4101 StartedAt 12:10:22Z (0 restart 维 R1926)

## 介入四条全不满足 → NOP 无据不改

1. 6h SR95.64% 大样本稳态 (与 R1984 95.22% +0.42pp 0 漂移微升), 30min 95.06% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+first_byte_timeout 已知类 (与 R1984 微调无新类), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 3 条但 state=CLOSED 不 OPEN
4. fallback 3/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

## 冻结理由 (连续第 34 轮仍成立)

半成品未经 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等 (当前 6h SR95.64% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 4 次/30min, 120s 跑满类持续趋零, 边际收益小). **等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动**.

用户诉求 (2026-07-19 01:40) "可以报错但不能让 cc2 中断" 仍达成 (R1987 0 真中断; 3 条 FALLBACK-OK 全被 ms_gw 兜住, 0 fallback 失败).

## peer 抢号

本轮 peer HM1 agent 已到 R1986 (commit 53c769a), cc2 用 R1987 前缀 hm2_cc2 (与 peer R1986_hm2_optimize_hm1.md 文件名独立不撞号). 写轮前 git pull 确认无 R1987_hm2_cc2 撞号文件.
