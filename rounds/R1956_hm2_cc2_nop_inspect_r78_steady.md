# R1956 (HM2 cc2): NOP 巡检 R78 — 30min SR97.7%/6h SR94.0% 0 真中断, 连续冻结第 15 轮延续 + 交接棒修复

> 模式: nv 直连 (cc4101→nv_gw), 指数退避+ms 双层方案**半成品冻结** (env NVU_GLM52_EXP_BACKOFF 未设=关, 从未 in-vivo 激活).
> 本轮: NOP 巡检 R78, 连续第 15 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1956 NOP), 0 改动 0 restart.
> **本轮额外**: 上一 session (R1954) 写了 round file + push 但**漏覆写 STATE.md** (棒仍停在 R1953), 交接棒断裂. 本轮修复: 把 STATE.md 推进到 R1956 真实状态, 补回 R1954/R1955 间隔.

## 数据 (本 session ~18:01Z UTC 拉取, nv_gw 已起 elapsed ~4h28min, cc4101 elapsed ~6h)

### nv_gw 成功率
- 30min: 200:84 / 502:2 → **SR = 97.7%** (小样本偏优; R1954 98.3 / R1953 91.7 / R1952 88.9 / R1951 89.3 / R1949 98.0 / R1947 92.9 / R1946 78.9 / R1943 94.7, 区间稳态非退化, 本轮高位, 样本量 86 较大)
- 6h: 200:597 / 502:38 → **SR = 94.0%** (大样本稳态区间; R1954 93.7 / R1953 93.3 / R1952 93.2 / R1942-1954 93.0-95.2% 区间内, 本轮略升无退化)

### 502 分类
- 30min 502=2 全 NVCF 上游侧已知类: **zombie_empty_completion×2** (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空; R1954 30min 502=1 是 first_byte_timeout, 本轮 zombie×2, 抖动非恶化)
- 6h 502=38 全已知类:
  - zombie_empty_completion×21 (R1954 20, 本轮 21, 微抖 +1 无恶化)
  - all_tiers_exhausted×12 (全 dsv4p_nv all_tiers_failed_in_mapped_tier 子类; R1954 12, 本轮 12 一致)
  - stream_first_byte_timeout×5 (全 dsv4p_nv; R1954 5, 本轮 5 一致)
- **abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` 0 rows 确认; R1918 方案0 cap_origin 重置持续归零连续多轮: R1931=4 → R1942=2 → R1943=2 → R1946=0 → R1947=0 → R1949=0 → R1951=0 → R1952=0 → R1953=0 → R1954=0 → R1956=0; 日志中 3 条 `NV-PEEK-CAP-RESET` 是方案0 reset 事件非真 abs_cap 502)

### fallback 率 (负向核心指标)
- **5** FALLBACK-OK/30min (0 真中断, 0 fallback 失败):
  - 全 5 条 **75s SKIP-CIRCUIT** (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
  - R1954 fallback 8 条 (7×75s SKIP + 1×PRIMARY-FAIL unknown), 本轮 5 条全 75s SKIP (PRIMARY-FAIL unknown 类本轮 0, 下降无恶化)
  - **120s 跑满类本轮 0** (R1954 0, R1953 2, R1951 4 — 持续趋稳下降, R1951 担心点持续反证)
  - ms 救回耗时 2.0-6.0s (3844/2253/2001/4505/6054ms)
- 全 5 条被 cc4101 在 75s 抢断切 ms, ms 2.0-6.0s 救回 → **0 条 fallback 失败 → CC 收 0 真 502**
- `grep 502` 真实命中 = 0, `both failed`/`ms.*fail` 搜索结果为空 → 确认 0 真中断

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0** (breaker CLOSED 连续多轮)
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **4** (2 条是 NV-MS-FB-SERVED 后 breaker 记 failure; 2 条是 zombie mid-stream soft-fail → breaker recorded state=('CLOSED', 2, 0)/('CLOSED', 1, 0); **breaker state 仍 CLOSED**, 计数 1-2 未达阈值 5/300s)
- 注: R1953 棒记 "BREAKER-FAIL 30min=0", 本轮 30min=4 属小样本抖动, 仍是 CLOSED 不 OPEN, 符合已知 pattern (稀疏长尾故障下 breaker 数学不可达, R1918/BUG-B 方案0 已从 abs_cap 侧根治)
- breaker **OPEN 0 连续多轮** (R1947→R1956 持续 CLOSED)

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次** (req=29134934 / req=2222e5c9), skip _try_tier_keys 第二轮省约 ~120s/fallback 请求
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发
- 历史: R1952 6 次 / R1951 1 次 / R1953 5 次 / R1954 4 次 / R1956 2 次 → 长期生效确认

## 验证
- env 无漂移 (与 R1947/R1949/R1951/R1952/R1953/R1954 完全一致):
  - nv_gw: UPSTREAM_TIMEOUT=66, TIER_TIMEOUT_BUDGET_S=180, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, NVU_GLM52_EXP_BACKOFF=未设=关 (env 中根本不存在该变量, 确认半成品从未激活), MIN_OUTBOUND_INTERVAL_S=0, KEY_COOLDOWN_S=25, TIER_COOLDOWN_S=25, NVU_BIG_INPUT_FAIL_N=1, NVU_BIG_INPUT_COOLDOWN_S=180, NV_INTEGRATE_KEY_COOLDOWN_S=90, KEY_AUTHFAIL_COOLDOWN_S=60
  - cc4101: PRIMARY_HEADER_TIMEOUT=60, CC4101_STREAM_TOTAL_DEADLINE_S=480 (R1926 改), CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv)
- docker ps: 全 Up (nv_gw Up 4h, cc4101 Up 6h, ms_gw Up 2d, logs_db Up 3d)
- nv_gw StartedAt = 2026-07-19T13:33:43Z (R1933 restart NameError 修复后, R1933→R1956 未再 restart; docker inspect 核实 elapsed ~4h28min @ 18:01Z UTC)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (R1926 step2.0 env up-d 后; elapsed ~6h @ 18:01Z UTC)
- commit: 待写 (本轮 NOP 0 改动, 仅 round 文件 + STATE.md 覆写)

## 介入四条全不满足 → NOP 无据不改
1. **SR**: 6h SR94.0% 大样本稳态区间, 30min 97.7% 小样本偏优, 非"连续 3+ 轮跌破 80%"介入线 → 不改
2. **502 分类**: 30min 502=2 全 zombie (NVCF 上游侧已知类), 6h 502=38 全 zombie+ATE+first_byte_timeout (已知类), abs_cap 30min=0/6h=0 (DB 确认), 非新可配置类 → 不改
3. **breaker**: OPEN 30min=0 连续多轮, NV-ANTH-BREAKER-FAIL 30min=4 全 CLOSED 不 OPEN (计数 1-2 未达 5/300s) → 不改
4. **fallback**: 5/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 低于 15/30min 介入线, 无新监督者激活指令 → 不改

## 指数退避激活决策仍冻结 (连续第 15 轮)
- R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测) 仍成立
- env `NVU_GLM52_EXP_BACKOFF` 根本不存在于容器 env 中 → 半成品代码从未激活, 冻结决定物理成立
- 当前链路稳态 (6h SR94.0% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 2 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结
- 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动

## 铁律遵守
- ✅ 改前有数据 (本轮 30min/6h 窗口 SR/error/fallback/breaker 全拉 + DB abs_cap 双重确认)
- ✅ 聚焦 40006 (只查 nv_gw + cc4101, 不碰 ms_gw 源码/配置)
- ✅ 只改 HM2 (peer HM1 由另一 agent 维护, 本轮 peer 已推到 R1955)
- ✅ 写入仓库 (round 文件 R1956)
- ✅ 0 改动 0 restart (NOP 巡检, env 无漂移, StartedAt 维 R1933/R1926 无 restart)
- ✅ 不撤 40007 (ms_gw 是 restart 窗口热备, 本轮 5 条 FALLBACK-OK 全靠它兜住 0 真中断)

## 交接棒修复说明 (本轮特殊)
- 上一 session (commit 938adbc, R1954) 写了 round file + push 成功, 但**漏了覆写 STATE.md** (棒仍停在 R1953 "上一轮发生了什么" 段). 这违反了"本轮所有结论必须最终落进 STATE.md" 的交接棒铁律.
- 本轮 (R1956) 修复: 覆写 STATE.md, 把 "上一轮发生什么" 推进到 R1954→R1955(peer)→R1956 真实状态, 补回 R1954 间隔, 最近 5 轮摘要更新到 R1956/R1954/R1953/R1952/R1951.
- 教训: 下个 session 务必确认 STATE.md 的轮号基线与 git log 最新一致, 若不一致说明上轮漏覆写, 优先修复.
