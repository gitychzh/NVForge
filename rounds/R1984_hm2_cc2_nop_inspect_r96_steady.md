# R1984 (HM2 cc2): NOP 巡检 R96 — 30min SR95.51%/6h SR95.22% 0 真中断, 与 R1983 6h +0.15pp 0 漂移, 连续冻结第 33 轮延续

> cc2 自优化 nv_gw 链路 (HM2)。本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933 (0 restart)。
> 连续第 33 轮 NOP 冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1967/R1970/R1971/R1972/R1973/R1976/R1977/R1978/R1979/R1983/R1984 NOP)。
> 铁律: 只改 HM2 nv_gw(40006), 不碰 ms_gw(40007), 不碰 HM1。

## 数据 (改前必有数据 — 本 session 拉取 30min/6h 窗口)

**nv_gw 30min SR = 85/89 = 96%? → 实 = 95.51%** (200:85 / 502:4, 样本 89 小)。
正确算法: 200 占 85/(85+4)=85/89=**95.51%**。R1983 30min 96.12% (99/103), 本轮 95.51% (85/89), -0.61pp 小样本波动非退化 (R1979 93.88 / R1978 93.51 / R1977 96.25 / R1976 95.3 区间内)。

**nv_gw 6h SR = 717/753 = 95.22%** (200:717 / 502:36), 大样本稳态区间。
R1983 6h 95.07% (714/751), 本轮 95.22% (717/753), **+0.15pp 0 漂移** (微升)。
R1979 95.09% / R1978 94.81% / R1977 94.96% / R1976 94.9% 区间内非退化。

**30min 502=4 全 NVCF 上游侧已知类**:
- zombie_empty_completion×3 + stream_first_byte_timeout×1 (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空)。
- R1983 30min 502=4 是 zombie×3+fbt×1, **本轮完全 0 漂移 (zombie 0/fbt 0)**。

**6h 502=36 全已知类**:
- zombie_empty_completion×24 (R1983 24, **0**) + all_tiers_exhausted×7 (R1983 7, **0**) + stream_first_byte_timeout×5 (R1983 6, **-1**)。
- 与 R1983 **完全 0 漂移 (zombie 0/ATE 0)**, fbt -1 微降。

**abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` = 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零)。
连续多轮归零序列: R1931=4 → R1942=2 → R1943=2 → R1946=0 → R1947=0 → R1949=0 → R1951=0 → R1952=0 → R1953=0 → R1954=0 → R1956=0 → R1957=0 → R1960=0 → R1961=0 → R1964=0 → R1966=0 → R1967=0 → R1970=0 → R1971=0 → R1972=0 → R1973=0 → R1976=0 → R1977=0 → R1978=0 → R1979=0 → R1983=0 → R1984=0。
注: 日志中 NV-PEEK-CAP-RESET 是方案0 reset 事件非真 abs_cap 502。

**持久化层 (30min tier_attempts)**: pexec_success×56 (nv_gw 转发层稳, 无 429; R1983 62, 本轮 56 -6 正常区间)。

**fallback 5 / 30min 全 FALLBACK-OK (0 真中断, 0 fallback 失败)**:
- 全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)。
- R1983 fallback 4×75s SKIP, 本轮 5×75s SKIP +1 区间内波动 (R1967 8/R1970 7/R1971 6/R1972 7/R1973 6/R1976 2/R1977 3/R1978 6/R1979 5/R1983 4/R1984 5, 无恶化非趋势)。
- ms 救回: 3490/2370/5123/3299/3293ms (全成功)。
- **120s 跑满类本轮 0** (R1951 4 → R1953 2 → R1954 0 → R1956 0 → R1957 0 → R1967 0 → R1970 0 → R1971 0 → R1972 0 → R1973 0 → R1976 0 → R1977 0 → R1978 0 → R1979 0 → R1983 0 → R1984 0, 持续趋稳归零)。
- 注: 日志中 "saves ~120s" 是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/fallback 请求), **非 120s 跑满类**, 不要混淆。
- 全 5 条被 cc4101 在 75s 抢断切 ms, ms 全救回 → **0 条 fallback 失败 → CC 收 0 真 502**。
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → 确认 0 真中断。

**breaker**:
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**。
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **3** (但 state 全 CLOSED: ('CLOSED',1,0), ('CLOSED',2,0), ('CLOSED',2,0) — 只记 failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN)。
- R1983 BREAKER-FAIL 3 state CLOSED 本轮 3 state CLOSED 完全一致。
- breaker **OPEN 0 连续多轮**。
- 注: 日志见 `NV-MS-FB-SERVED ms_gw served glm5_2_nv fallback (state=CLOSED)` — 这是 nv_gw 内部 ms_fb 路径 (Point A/B) 记 breaker failure, state 仍 CLOSED, 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关。

**BUG-A 修复 (R1913) 在日志中真实生效确认**:
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求。
- 序列: R1952 6 / R1951 1 / R1953 5 / R1954 4 / R1956 2 / R1957 1 / R1967 2 / R1970 4 / R1971 5 / R1972 6 / R1973 5 / R1976 2 / R1977 2 / R1978 4 / R1979 5 / R1983 4 / **R1984 5**。R1913 阶段1.5 机制持续触发, 验证 BUG-A 修复长期生效 (本轮 5 次)。

## 验证

- env 无漂移 (与 R1983 完全一致; NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活)。
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)。
- docker ps 全 Up (nv_gw Up 8h, cc4101 Up 10h, ms_gw Up 2d, logs_db Up 3d)。
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933; docker inspect 核实)。
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926)。

## 介入四条全不满足 → NOP 无据不改 (连续第 33 轮冻结)

1. **SR 稳态**: 6h SR95.22% 大样本稳态 (与 R1983 95.07% +0.15pp 0 漂移微升), 30min 95.51% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线。
2. **502 全已知类**: 全 zombie_empty_completion / all_tiers_exhausted / stream_first_byte_timeout (与 R1983 完全 0 漂移), 非新可配置类。abs_cap 30min=0/6h=0 (DB 双重确认)。
3. **breaker OPEN 0**: 30min=0 连续多轮, nv_gw BREAKER-FAIL 3 条但 state=CLOSED 不 OPEN。
4. **fallback 0 真中断**: 5/30min 全 FALLBACK-OK 被 ms 兜住, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)。

**冻结理由 (连续第 33 轮仍成立)**: 半成品未经 in-vivo 验证 (env NVU_GLM52_EXP_BACKOFF 从未激活, 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口。当前链路稳态 (6h SR95.22% 与 R1983 +0.15pp 0 漂移 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 5 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结。

## 结论

**0 改动 0 restart, 连续第 33 轮 NOP 冻结指数退避**。链路稳态延续, 6h SR 与 R1983 +0.15pp 0 漂移, 502 全已知类与 R1983 完全 0 漂移, fallback 5/30min 全 FALLBACK-OK 0 真中断, breaker OPEN 0 连续多轮, BUG-A 修复真实生效 5 次/30min。等监督者再授权激活指数退避, 或数据恶化 (SR 连续 3+ 轮跌破 80% 且出现真正新可配置 502 类) 再动。
