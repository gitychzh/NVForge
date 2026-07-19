# R1976 (HM2 cc2) — NOP 巡检 R91, 连续第 28 轮冻结指数退避

> 轮号: R1976 | 主机: HM2 (100.109.57.26) | agent: cc2 | 模式: nv 直连 (cc4101→nv_gw)
> 上一轮: R1973 (cc2, 3e66317) NOP R90 | peer HM1 agent 已占 R1974/R1975 (HM2→HM1 前缀, 不碰 HM2 nv_gw)
> 本轮决策: **NOP 巡检 R91, 0 改动 0 restart**, 连续第 28 轮冻结指数退避 (R1928 冻结延续)

## 数据 (本 session 拉取, nv_gw 已起 elapsed ~43h+)

### 30min 窗口 (样本 86, 偏稳)
- nv_gw 30min SR = 82/86 = **95.3%** (200:82 / 502:4)
- 502=4 全 NVCF 上游侧已知类:
  - zombie_empty_completion ×2 (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空)
  - all_tiers_exhausted ×1 (NVCF 上游 tier 全失败)
  - stream_first_byte_timeout ×1 (首字节不来)
- abs_cap 30min=0 (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零)

### 6h 窗口 (样本 744, 大样本稳态)
- nv_gw 6h SR = 706/744 = **94.9%** (200:706 / 502:38)
- 502=38 全已知类: zombie×24 (R1973 23, +1 区间内波动) + ATE×9 (R1973 9, 一致) + first_byte_timeout×5 (R1973 4, +1 区间内波动)
- abs_cap 6h=0 (DB 双重确认)
- 与 R1973 (6h SR94.7%) **+0.2pp 微升, 区间内正常抖动, 0 漂移**

### fallback (负向核心指标, 30min)
- **2** FALLBACK-OK (0 真中断, 0 fallback 失败)
- 全 2 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry, NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)
- ms 救回: 3182ms / 3979ms
- 120s 跑满类本轮 **0** (R1951 4→R1953 2→R1954 0→...→R1973 0→R1976 0, 持续趋稳归零)
- 注: 日志中 2 条 "saves ~120s" 全是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb` (BUG-A 修复路径省约 120s/请求), **非 120s 跑满类**, 不要混淆
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → 确认 0 真中断
- 注: 日志见 `NV-MS-FB-SERVED ms_gw served glm5_2_nv fallback (state=CLOSED)` — 这是 nv_gw 内部 ms_fb 路径 (Point A/B) 记 breaker failure, state 仍 CLOSED (计数未达 5/300s), 非 NV-ANTH-BREAKER-FAIL 事件

### breaker (30min)
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **1** (但 state=('CLOSED', 1, 0) — 只记 1 次 failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN; R1957 抖到 2 的同类抖动, 非 OPEN 事件)
- breaker **OPEN 0 连续多轮**

### BUG-A 修复 (R1913) 真实生效
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **2 次** (R1973 5, 区间内波动)
- R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发

## 决策: NOP 无据不改

介入四条全不满足:
1. 6h SR94.9% 大样本稳态 (与 R1973 94.7% +0.2pp 微升 0 漂移), 30min 95.3% 小样本偏稳非"连续 3+ 轮跌破 80%"介入线
2. 502 全 zombie+ATE+first_byte_timeout 已知类 (与 R1973 几乎 0 漂移仅 zombie+1), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)
3. breaker OPEN 30min=0 连续多轮, nv_gw BREAKER-FAIL 1 条但 state=CLOSED 1/0 未 OPEN
4. fallback 2/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线, 无新监督者激活指令 (R1928 冻结理由仍成立)

**R1928 冻结理由仍成立**: 半成品未经 in-vivo 验证 (env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中) + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口. 风险/收益不对等.

## 验证

- env 无漂移 (与 R1973 完全一致; NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活)
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv)
- docker ps 全 Up (nv_gw Up 7h / cc4101 Up 9h / ms_gw Up 2 days / logs_db Up 3 days)
- nv_gw StartedAt = 2026-07-19T13:33:43Z (0 restart, 维 R1933, elapsed ~43h+)
- cc4101 StartedAt = 2026-07-19T12:10:22Z (0 restart, 维 R1926, elapsed ~44h+)

## commit

- 0 改动 0 restart, 仅 round 文件入库
- git add + commit + push origin/main

## nv_gw 参数快照 (R1976 拉取, 无漂移)

```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=180
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_STREAM_ABSOLUTE_CAP_S=150
NVU_GLM52_EXP_BACKOFF=不在 env 中=关 (半成品冻结, 从未 in-vivo 激活)
MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25
KEY_AUTHFAIL_COOLDOWN_S=60
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_COOLDOWN_S=180
NV_INTEGRATE_KEY_COOLDOWN_S=90
TIER_COOLDOWN_S=25
```
