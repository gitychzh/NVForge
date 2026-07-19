# R1989 (HM2 cc2) — NOP 巡检 R98, 连续第 35 轮冻结指数退避

> 接力棒: R1987 (commit 2223ace) → R1989 (本轮). 中间 peer 写了 R1988 HM2→HM1 (b534a26, 前缀 hm2_optimize_hm1 不同, 文件名不撞号).
> 本轮 0 改动 0 restart, 拉数据确认链路稳态延续.

## 数据 (本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933, cc4101 StartedAt 12:10:22Z 维 R1926)

### nv_gw 成功率
- 30min SR = 116/121 = **95.87%** (200:116 / 502:5). 小样本偏稳 (R1987 95.06 / R1984 95.51 / R1983 96.12, 区间稳态非退化).
- 6h SR = 807/841 = **95.95%** (200:807 / 502:34). 大样本稳态区间 (**与 R1987 6h 95.64% +0.31pp 0 漂移微升**).

### 502 错误分类 (全已知类)
- 30min 502=5: zombie_empty_completion×4 + stream_first_byte_timeout×1. (R1987 30min zombie×4; 本轮 zombie 持平 +1 fbt, **0 新类**)
- 6h 502=34: zombie×25 (R1987 25, 持平) + stream_first_byte_timeout×5 (R1987 4, +1) + all_tiers_exhausted×4 (R1987 5, -1). 与 R1987 **zombie 持平 / fbt +1 / ATE -1 微调全已知类无新可配置类**.
- **abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零连续多轮, R1987=0 → R1989=0).

### 持久化层 (30min tier_attempts)
- pexec_success×89 + pexec_conn_RemoteDisconnected×2. (R1987 78, 本轮 89 +11 正常区间; 转发层稳, 无 429).

### fallback (负向核心指标, 0 真中断)
- fallback **2** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 2 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层). ms 救回 1739/3205ms.
- R1987 fallback 3×75s SKIP, 本轮 2×75s SKIP -1 (R1967 8/R1970 7/R1971 6/R1972 7/R1973 6/R1976 2/R1977 3/R1978 6/R1979 5/R1983 4/R1984 5/R1987 3/R1989 2 区间内波动, 无恶化).
- **120s 跑满类本轮 0** 持续趋稳归零 (R1951 4→R1953 2→R1954 0→...→R1987 0→R1989 0).
- 注: 日志中 "saves ~120s" 是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/fallback 请求), **非 120s 跑满类**, 不要混淆.
- 注: 日志见 `NV-MS-FB-SERVED ms_gw served glm5_2_nv fallback (state=CLOSED)` — nv_gw 内部 ms_fb 路径记 breaker failure, state 仍 CLOSED, 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关.
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → **0 真中断** 确认.

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**.
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **3** (但 state 全 CLOSED: ('CLOSED',2,0)×2 + ('CLOSED',3,0)×1 — 只记 failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN; R1957/R1978/R1979/R1983/R1984/R1987 抖到 2-3 同类抖动, 非 OPEN 事件). breaker **OPEN 0 连续多轮**.

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求. (R1952 6/R1951 1/R1953 5/R1954 4/R1956 2/R1957 1/R1967 2/R1970 4/R1971 5/R1972 6/R1973 5/R1976 2/R1977 2/R1978 4/R1979 5/R1983 4/R1984 5/R1987 4/R1989 2). R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮机制持续触发, 长期生效.

## 验证
- env 无漂移 (与 R1987 完全一致; NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中确认半成品从未激活).
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 9h, cc4101 Up 10h, ms_gw Up 2d, logs_db Up 3d).
- nv_gw StartedAt 13:33:43Z (0 restart, 维 R1933); cc4101 StartedAt 12:10:22Z (0 restart, 维 R1926).
- 0 改动 0 restart.

## 介入决策: NOP 无据不改 (介入四条全不满足)
1. 6h SR95.95% 大样本稳态 (与 R1987 95.64% +0.31pp 0 漂移微升), 30min 95.87% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线.
2. 502 全 zombie+fbt+ATE 已知类 (与 R1987 微调无新类), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认).
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 3 条但 state=CLOSED 不 OPEN.
4. fallback 2/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立).

## 指数退避激活决策: 仍冻结 (连续第 35 轮)
- R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立.
- env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立.
- 当前链路稳态 (6h SR95.95% 与 R1987 +0.31pp 0 漂移微升, 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 2 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结.
- **等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动**.

## 下一轮
- 继续 NOP 巡检 R99. 拉数据看 SR/fallback/breaker 抖动是否仍在已知区间.
- 关注 120s 跑满类是否持续低位 (持续 0) + breaker 是否开始 OPEN (当前仍 CLOSED).
- peer 抢号快, 下一轮 git pull 后看最新号 +1 (peer 可能到 R1989+, cc2 从 R1990 起; 前缀 hm2_cc2 与 peer hm2_optimize_hm1 文件名独立不撞号).
