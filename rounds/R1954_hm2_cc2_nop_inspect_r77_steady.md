# R1954 (HM2 cc2): NOP 巡检 R77 — 30min SR98.3%/6h SR93.7% 0 真中断, 连续冻结第 14 轮延续

> 模式: nv 直连 (cc4101→nv_gw), 指数退避+ms 双层方案**半成品冻结** (env NVU_GLM52_EXP_BACKOFF 未设=关, 从未 in-vivo 激活).
> 本轮: NOP 巡检 R77, 连续第 14 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1954 NOP), 0 改动 0 restart.

## 数据 (本 session ~17:42Z UTC 拉取, nv_gw 已起 elapsed ~4h, cc4101 elapsed ~5h)

### nv_gw 成功率
- 30min: 200:57 / 502:1 → **SR = 98.3%** (小样本偏优; R1953 91.7 / R1952 88.9 / R1951 89.3 / R1949 98.0 / R1947 92.9 / R1946 78.9 / R1943 94.7, 区间稳态非退化, 本轮高位)
- 6h: 200:553 / 502:37 → **SR = 93.7%** (大样本稳态区间; R1953 93.3 / R1952 93.2 / R1942-1953 93.0-95.2% 区间内, 本轮略升无退化)

### 502 分类
- 30min 502=1 全 NVCF 上游侧已知类: **stream_first_byte_timeout×1** (glm5_2_nv; R1953 30min 此类=1, 本轮 1 一致)
- 6h 502=37 全已知类:
  - zombie_empty_completion×20 (R1953 23, 本轮 20, 下降 3 无恶化)
  - all_tiers_exhausted×12 (全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类; R1953 12, 本轮 12 一致)
  - stream_first_byte_timeout×5 (全 dsv4p_nv; R1953 5, 本轮 5 一致)
- **abs_cap 30min=0 / 6h=0** (R1918 方案0 cap_origin 重置持续归零连续多轮: R1931=4 → R1942=2 → R1943=2 → R1946=0 → R1947=0 → R1949=0 → R1951=0 → R1952=0 → R1953=0 → R1954=0; 6h 502 分类中无 stream_absolute_cap)

### fallback 率 (负向核心指标)
- **8** FALLBACK-OK/30min (0 真中断, 0 fallback 失败):
  - **7×75s SKIP-CIRCUIT** (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层). R1953 30min fallback 7 条全 75s SKIP, 本轮 7 条 75s SKIP 一致.
  - **1×PRIMARY-FAIL (unknown)** (req=196c59ca, 非 75s timeout, ms 3776ms 救回 → FALLBACK-OK). 此类 R1953 0, 本轮 1, 单条无恶化.
  - ms 救回耗时 2.0-9.7s (3776/4115/3221/2075/9651/3844/2253/2001ms)
- 全 8 条被 cc4101 抢断切 ms, ms 2.0-9.7s 救回 → **0 条 fallback 失败 → CC 收 0 真 502**
- `grep 502` 真实命中 = 0, `both failed`/`ms.*fail` 搜索结果为空 → 确认 0 真中断

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **0**
- breaker **OPEN 0 连续多轮** (R1947→R1954 持续 CLOSED)

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发
- 历史: R1952 6 次 / R1951 1 次 / R1953 5 次 / R1954 4 次 → 长期生效确认

## 验证
- env 无漂移 (与 R1947/R1949/R1951/R1952/R1953 完全一致):
  - nv_gw: UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, NVU_GLM52_EXP_BACKOFF=未设=关, MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_AUTHFAIL_COOLDOWN_S=60
  - cc4101: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)
- docker ps: 全 Up (nv_gw Up 4h, cc4101 Up 6h, ms_gw Up 2d, logs_db Up 3d)
- nv_gw StartedAt = 2026-07-19T13:33:43Z (R1933 restart NameError 修复后, R1933→R1954 未再 restart; docker inspect 核实 elapsed ~4h @ 17:42Z UTC)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后; elapsed ~5h @ 17:42Z UTC)
- commit: 待写 (本轮 NOP 0 改动, 仅 round 文件)

## 介入四条全不满足 → NOP 无据不改
1. **SR**: 6h SR93.7% 大样本稳态区间, 30min 98.3% 小样本偏优, 非"连续 3+ 轮跌破 80%"介入线 → 不改
2. **502 分类**: 30min 502=1 全 stream_first_byte_timeout (NVCF 上游侧已知类), 6h 502=37 全 zombie+ATE+first_byte_timeout (已知类), abs_cap 30min=0/6h=0, 非新可配置类 → 不改
3. **breaker**: OPEN 30min=0 连续多轮, NV-ANTH-BREAKER-FAIL 30min=0 → 不改
4. **fallback**: 8/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 → 不改

## 指数退避激活决策仍冻结 (连续第 14 轮)
- R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立
- 当前链路稳态 (6h SR93.7% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 4 次/30min) + 本轮无新监督者激活指令 → 继续冻结
- 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动

## 铁律遵守
- ✅ 改前有数据 (本轮 30min/6h 窗口 SR/error/fallback/breaker 全拉)
- ✅ 聚焦 40006 (只查 nv_gw + cc4101, 不碰 ms_gw 源码/配置)
- ✅ 只改 HM2 (peer HM1 由另一 agent 维护)
- ✅ 写入仓库 (round 文件 R1954)
- ✅ 0 改动 0 restart (NOP 巡检, env 无漂移, StartedAt 维 R1933/R1926 无 restart)
- ✅ 不撤 40007 (ms_gw 是 restart 窗口热备, 本轮 8 条 FALLBACK-OK 全靠它兜住 0 真中断)
