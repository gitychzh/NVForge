# R1977 (HM2 cc2): NOP 巡检 R92 — 30min SR96.25%/6h SR94.96% 0 真中断, 与 R1976 6h 0 漂移, 连续冻结第 29 轮延续

> 新 session, 无上轮对话上下文。读 STATE.md (R1976 基线) → git pull → 拉数据 → 判断 → 写轮 → 覆写 STATE.
> 本轮 0 改动 0 restart. 介入四条全不满足 → NOP 无据不改.

## 数据 (本 session 拉取, 30min + 6h 窗口)

| 窗口 | 总请求 | 200 | 502 | SR |
|---|---|---|---|---|
| 30min | 80 | 77 | 3 | **96.25%** |
| 6h | 734 | 697 | 37 | **94.96%** |

### 30min 502=3 错误分类 (全 NVCF 上游侧已知类)
- zombie_empty_completion ×2 (glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空)
- stream_first_byte_timeout ×1 (首字节不来)

### 6h 502=37 错误分类 (全已知类)
- zombie_empty_completion ×24 (R1976 24, 一致)
- all_tiers_exhausted ×8 (R1976 9, -1 区间内波动)
- stream_first_byte_timeout ×5 (R1976 5, 一致)

### 与 R1976 对比 (0 漂移)
- 30min SR 96.25% (R1976 95.3%, +0.95pp 小样本偏稳, 区间内抖动非退化)
- 6h SR 94.96% (R1976 94.9%, +0.06pp 几乎一致 0 漂移)
- 30min 502: 3 (R1976 4, -1) — zombie×2 同 + first_byte_timeout×1 同 (ATE R1976 有 1, 本轮 30min 0)
- 6h 502: 37 (R1976 38, -1) — 仅 ATE -1, zombie/fbt 完全一致
- **abs_cap 30min=0 / 6h=0** (DB `like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零, 连续多轮 R1931→...→R1973→R1976→R1977)

## fallback (30min, 负向核心指标)

- fallback **3** FALLBACK-OK (0 真中断, 0 fallback 失败): 全 3 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- ms 救回: 2598ms / 2191ms / 3171ms (全 2-3s 救回)
- R1976 fallback 2×75s SKIP, 本轮 3×75s SKIP +1 (R1967 8/R1970 7/R1971 6/R1972 7/R1973 6/R1976 2/R1977 3 区间内波动, 无恶化)
- **120s 跑满类本轮 0** (R1951 4→R1953 2→R1954 0→...→R1976 0→R1977 0, 持续趋稳归零)
- 注: 日志中 "saves ~120s" 全是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/请求), 非 120s 跑满类, 不要混淆
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = **0** → 确认 0 真中断

## breaker

- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **1** (但 state=('CLOSED', 1, 0) — 只记 1 次 failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN; R1957 抖到 2 的同类抖动, 非 OPEN 事件)
- breaker **OPEN 0 连续多轮**
- 注: 日志见 `NV-MS-FB-SERVED state=CLOSED` 是 nv_gw 内部 ms_fb 路径记 failure 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关

## BUG-A 修复 (R1913) 真实生效确认

- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发
- 历史: R1952 6/R1951 1/R1953 5/R1954 4/R1956 2/R1957 1/R1967 2/R1970 4/R1971 5/R1972 6/R1973 5/R1976 2/R1977 2 — 本轮 2 次与 R1976 一致

## 验证

- env 无漂移 (与 R1976 完全一致; NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)
- docker ps 全 Up (nv_gw/cc4101/ms_gw/logs_db)
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (R1933 restart NameError 修复后, R1933→R1977 未再 restart; docker inspect 核实)
- cc4101 StartedAt = **2026-07-19T12:10:22Z** (R1926 step2.0 env up-d 后; 0 restart)
- 注: docker ps 显示 nv_gw "Up 7 hours" / cc4101 "Up 9 hours" 是 docker 显示口径, 精确 StartedAt 以 docker inspect 为准 — 与 STATE 记录的 R1933/R1926 值完全一致 = 0 restart

## nv_gw 参数快照 (无漂移)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_STREAM_ABSOLUTE_CAP_S=150
NVU_GLM52_EXP_BACKOFF=不在 env 中=关 (半成品冻结, 从未 in-vivo 激活, env 里根本无此变量)
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
TIER_COOLDOWN_S=25
```

## 介入四条全不满足 → NOP 无据不改

1. **SR**: 6h SR94.96% 大样本稳态 (与 R1976 94.9% +0.06pp 几乎一致 0 漂移), 30min 96.25% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线
2. **502 分类**: 全 zombie+ATE+first_byte_timeout 已知类 (与 R1976 几乎 0 漂移仅 ATE -1), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. **breaker**: OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 1 条但 state=CLOSED 1/0 未 OPEN
4. **fallback**: 3/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

## 决策: 继续冻结指数退避 (连续第 29 轮)

R1928 冻结理由仍成立:
- 半成品代码未经 in-vivo 验证 (env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中 → 从未激活)
- 激活需同步 4 个坑: (1) chain_budget 120→420 (2) cc4101 header 60→450 (3) post-200 软挂换 key 未实现 (4) abs_cap 150→250+ 容指数退避
- 当前链路稳态 (6h SR94.96% 0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 2 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 风险/收益不对等, 继续冻结
- 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动

## peer 协调

- 本轮 peer 已占 R1977 (commit bdc0272, 前缀 hm2_optimize_hm1, 改 HM1 侧 0 影响 HM2)
- cc2 用 R1977 前缀 hm2_cc2 (文件名 R1977_hm2_cc2_*, 与 peer R1977_hm2_optimize_hm1.md 独立不撞号)
- 下一轮 git pull 后看最新号 +1 (peer 可能到 R1978+, cc2 从 +1 起)

## commit

- 本轮 0 改动 0 restart, 仅写 round file + 覆写 STATE
