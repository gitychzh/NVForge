# R1973 (HM2 cc2): NOP 巡检 R90 — 30min SR95.5%/6h SR94.7% 0 真中断, 与 R1972 6h 0 抖动, 连续冻结第 27 轮延续

> NOP 巡检 R90。连续第 27 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1967/R1970/R1971/R1972/R1973 NOP)。
> 0 改动, 0 restart, 0 env 漂移。本轮依据 30min/6h 窗口数据 (本 session 拉取, nv_gw 已起 elapsed ~43h+)。

## 数据 (本 session 拉取, 改前必有数据)

### nv_gw 成功率
- **30min SR = 63/66 = 95.5%** (200:63 / 502:3), 小样本偏稳
  (R1972 94.7 / R1971 96.6 / R1970 98.2 / R1967 98.2 / R1966 97.1, 区间稳态非退化)
- **6h SR = 644/680 = 94.7%** (200:644 / 502:36), 大样本稳态区间
  (R1972 94.8% / R1971 94.8% / R1970 94.9% / R1967 94.9% / R1966 95.0%, 区间稳态非退化; **与 R1972 94.8% 几乎一致, 0.1pp 微降属区间内正常抖动 0 漂移**)

### 502 错误分类 (全 NVCF 上游侧已知类)
- 30min 502=3 全已知类:
  - **all_tiers_exhausted×2** (NVCF 上游 tier 全失败)
  - **zombie_empty_completion×1** (glm5_2_nv 出口 IP 段 134.195.101.0/24 同源快回空)
  - 与 R1972 完全一致 (R1972 也是 ATE×1+zombie×1, 本轮 ATE +1, 同已知类非新类)
- 6h 502=36 全已知类:
  - zombie×23 (R1972 23, 一致)
  - ATE×9 (R1972 8, +1 区间内波动)
  - first_byte_timeout×4 (R1972 4, 一致)
  - 与 R1972 几乎 0 漂移 (仅 ATE +1)

### abs_cap 双重确认 (R1918 方案0 cap_origin 重置持续归零)
- 30min abs_cap = **0** (DB `error_type like '%abs%'` 0 rows)
- 6h abs_cap = **0**
- 连续多轮归零: R1931=4 → R1942=2 → R1943=2 → R1946=0 → ... → R1970=0 → R1971=0 → R1972=0 → **R1973=0**
- 日志中 NV-PEEK-CAP-RESET 是方案0 reset 事件非真 abs_cap 502

### fallback (负向核心指标, 0 真中断)
- fallback **6** FALLBACK-OK / 30min (R1972 是 7, 本轮 6, -1 无恶化)
- 全 6 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- ms 救回 2.2-4.0s
- **0 条 fallback 失败 → CC 收 0 真 502**
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → 确认 0 真中断
- **120s 跑满类本轮 0** (R1951 4 → R1953 2 → R1954 0 → ... → R1972 0 → **R1973 0**, 持续趋稳归零)
- 注: 日志中 5 条 "saves ~120s" 全是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/请求), **非 120s 跑满类**, 不要混淆
- 注: 日志见 `NV-MS-FB-SERVED ... state=CLOSED` 是 nv_gw 内部 ms_fb 路径记 breaker failure, state 仍 CLOSED (计数未达 5/300s), 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **0**
- (R1957 抖到 2, R1967/R1970/R1971/R1972/R1973 均 0, 连续多轮 CLOSED 不 OPEN)
- breaker **OPEN 0 连续多轮**

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **5 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求
- (R1952 6 / R1951 1 / R1953 5 / R1954 4 / R1956 2 / R1957 1 / R1967 2 / R1970 4 / R1971 5 / R1972 6 / **R1973 5**)
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发, 验证 BUG-A 修复长期生效

## 验证
- env 无漂移 (与 R1972 完全一致; NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv)
- docker ps 全 Up
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933, elapsed ~43h+)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926, elapsed ~44h+)

## 介入四条 (全不满足 → NOP 无据不改)
1. **SR**: 6h SR94.7% 大样本稳态 (与 R1972 94.8% 0 抖动), 30min 95.5% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线 → 不满足
2. **502 分类**: 全 zombie+ATE+first_byte_timeout 已知类 (与 R1972 几乎 0 漂移仅 ATE+1), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认) → 不满足
3. **breaker**: OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 30min=0 全 CLOSED 不 OPEN → 不满足
4. **fallback**: 6/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立) → 不满足

## 冻结理由 (连续第 27 轮仍成立)
- 半成品未经 in-vivo 验证 (env 开关从未激活, NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中)
- 激活需同步: (1) chain_budget NVU_TIER_BUDGET_GLM5_2_NV 120→420 (2) cc4101 PRIMARY_HEADER_TIMEOUT 60→450 (3) post-200 软挂换 key 未实现 (handlers.py 5 处) (4) abs_cap NVU_STREAM_ABSOLUTE_CAP_S 150→250+ 容指数退避
- 风险/收益不对等 (当前 6h SR94.7% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 5 次/30min, 120s 跑满类持续趋零, 边际收益小)
- 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动

## 本轮操作
- 0 改动, 0 restart, 0 env 漂移
- 仅记录数据 + 结论, 延续 R1928 冻结决定 (NOP 巡检 R90, 连续第 27 轮冻结指数退避)

## commit
- 70c9de9 (R1972) → R1973
