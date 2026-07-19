# R1991 (HM2 cc2): NOP 巡检 R100 — 30min SR96.72%/6h SR95.85% 0 真中断, 与 R1990 6h -0.04pp 0 漂移, 连续冻结第 37 轮延续

> cc2 自优化轮次。HM2 only, 聚焦 40006 (nv_gw), 不碰 40007 (ms_gw 重启窗口热备)。
> 本轮 = NOP 巡检 R100, 连续第 37 轮冻结指数退避 (R1928 冻结 → ... → R1990 → R1991)。
> 改前必有数据, 改后必有验证, 数据驱动。

## 数据 (本 session 拉取, nv_gw StartedAt 13:33:43Z 维 R1933, 0 restart)

### 30min 窗口
- nv_gw 30min SR = 118/122 = **96.72%** (200:118 / 502:4), 小样本偏稳
  (R1990 95.97 / R1989 95.87 / R1987 95.06 / R1984 95.51 / R1983 96.12, 区间稳态非退化, +0.75pp vs R1990 微升)。
- 30min 502=4 全 NVCF 上游侧已知类: **stream_first_byte_timeout×2 + all_tiers_exhausted×1 + zombie_empty_completion×1**
  (全 glm5_2_nv, 出口 IP 段 134.195.101.0/24 同源快回空)。
  R1990 30min 502=5 是 zombie×3+ATE×1+fbt×1, 本轮 zombie 持平-2 / fbt +1 单条微调, **0 新类**。

### 6h 窗口
- nv_gw 6h SR = 832/868 = **95.85%** (200:832 / 502:36), 大样本稳态区间
  (R1960-1991 94.0-96.1% 区间内非退化, **与 R1990 6h 95.89% -0.04pp 0 漂移微降**)。
- 6h 502=36 全已知类: zombie×25 (R1990 25, 持平) + stream_first_byte_timeout×6 (R1990 5, +1) + all_tiers_exhausted×5 (R1990 5, 持平)。
  与 R1990 **zombie 持平 / ATE 持平 / fbt +1 微调, 全已知类无新可配置类**。

### abs_cap (DB 双重确认)
- **abs_cap 30min=0 / 6h=0** (DB `error_type like '%abs%'` 0 rows 双重确认; R1918 方案0 cap_origin 重置持续归零, 连续多轮:
  R1931=4→R1942=2→R1943=2→R1946=0→R1947=0→R1949=0→R1951=0→R1952=0→R1953=0→R1954=0→R1956=0→R1957=0→R1960=0→
  R1961=0→R1964=0→R1966=0→R1967=0→R1970=0→R1971=0→R1972=0→R1973=0→R1976=0→R1977=0→R1978=0→R1979=0→R1983=0→R1984=0→
  R1987=0→R1989=0→R1990=0→R1991=0; 日志中 NV-PEEK-CAP-RESET 是方案0 reset 事件非真 abs_cap 502)。

### tier 层 30min (nv_tier_attempts)
- pexec_success×70 + pexec_conn_RemoteDisconnected×4 (无新可配置类)。

### fallback (负向核心指标)
- fallback **4** /30min 全 FALLBACK-OK (0 真中断, 0 fallback 失败):
  全 4 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry,
  NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层)。
  R1990 fallback 3×75s SKIP, 本轮 4×75s SKIP +1
  (R1967 8/R1970 7/R1971 6/R1972 7/R1973 6/R1976 2/R1977 3/R1978 6/R1979 5/R1983 4/R1984 5/R1987 3/R1989 2/R1990 3/R1991 4 区间内波动, 无恶化)。
- **120s 跑满类本轮 0** 持续趋稳归零 (R1951 4 → R1953 2 → R1954 0 → ... → R1990 0 → R1991 0)。
  注: 日志中 "saves ~120s" 是 `NV-GLM52-CHAIN-SKIP-PEXEC2 ... go all_keys_exhausted -> ms_fb`
  (BUG-A 修复路径省约 120s/fallback 请求), **非 120s 跑满类**, 不要混淆。
- 全 4 条被 cc4101 在 75s 抢断切 ms, ms 救回 3205/3456/15515/2476ms → **0 条 fallback 失败 → CC 收 0 真 502**。
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = 0 → 确认 0 真中断。
- 注: 日志见 `NV-MS-FB-SERVED ms_gw served glm5_2_nv fallback (state=CLOSED)` — 这是 nv_gw 内部 ms_fb 路径
  (Point A/B) 记 breaker failure, state 仍 CLOSED, 非 NV-ANTH-BREAKER-FAIL 事件, 与 breaker OPEN 无关。

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**;
- nv_gw 30min breaker 日志 6 条全 `state=CLOSED` (recorded failure, 未达 5/300s 阈值, 仍 CLOSED 不 OPEN;
  R1957/R1978/R1979/R1983/R1984/R1987 抖到 2-3 同类, R1991 仍 CLOSED 不 OPEN)。
- breaker **OPEN 0 连续多轮**。

### BUG-A 修复 (R1913) 真实生效确认
- 30min 内 `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **3 次**, skip _try_tier_keys 第二轮省约 ~120s/fallback 请求。
  R1913 阶段1.5 补全 `_chain_failed=True` + `if _chain_failed:` 跳过 pexec 第二轮的机制持续触发, 验证 BUG-A 修复长期生效
  (R1952 6/R1951 1/R1953 5/R1954 4/R1956 2/R1957 1/R1967 2/R1970 4/R1971 5/R1972 6/R1973 5/R1976 2/R1977 2/
   R1978 4/R1979 5/R1983 4/R1984 5/R1987 4/R1989 2/R1990 2/R1991 3)。

## 验证
- env 无漂移 (与 R1990 完全一致; `NVU_GLM52_EXP_BACKOFF` 根本不在容器 env 中确认半成品从未激活)。
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough)。
- docker ps 全 Up (nv_gw Up 9h, cc4101 Up 10h, ms_gw Up 2d, logs_db Up 3d)。
- nv_gw StartedAt 13:33:43Z (0 restart, 维 R1933); cc4101 StartedAt 12:10:22Z (0 restart, 维 R1926)。
- **0 改动 0 restart**。

## 决策: 介入四条全不满足 → NOP 无据不改
1. 6h SR95.85% 大样本稳态 (与 R1990 95.89% -0.04pp 0 漂移微降), 30min 96.72% 小样本偏稳
   非"连续 3+ 轮跌破 80%"介入线。
2. 502 全 zombie+ATE+fbt 已知类 (与 R1990 微调无新类), 非新可配置类, abs_cap 30min=0/6h=0 (DB 双重确认)。
3. breaker OPEN 30min=0 连续多轮, nv_gw breaker 6 条但 state=CLOSED 不 OPEN, cc4101 PRIMARY-BREAKER-OPEN=0。
4. fallback 4/30min 全 FALLBACK-OK 被 ms 兜住 0 真中断, 远低于 15/30min 介入线,
   无新监督者激活指令 (R1928 冻结理由仍成立)。

## 指数退避冻结 (连续第 37 轮)
- R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 +
  post-200 软挂换 key 未实现 + 24h 观测) 仍成立。
- env `NVU_GLM52_EXP_BACKOFF` 根本不在容器 env 中 → 半成品代码从未激活, 冻结决定物理成立。
- 当前链路稳态 (6h SR95.85% 与 R1990 -0.04pp 0 漂移 0 真中断, abs_cap 连续多轮归零,
  BUG-A 修复真实生效 3 次/30min, 120s 跑满类持续趋零) + 本轮无新监督者激活指令 → 继续冻结。
- **等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动**。

## 下一步
- 继续渐进。下一轮拉 30min 数据看 SR/fallback/breaker 抖动是否仍在已知区间。
- 关注: 120s 跑满类是否持续低位 (当前连续多轮 0 持续趋稳归零), breaker 是否开始 OPEN (当前仍 CLOSED)。
- 若连续 3+ 轮 SR 跌破 80% **且** 502 分类出现真正新可配置类, 再考虑动 env。
- 沿用给监督者方向: abs_cap/zombie/empty200/all_tiers_exhausted 同源首字节慢/空/出口侧不可达是
  NVCF 上游侧 + 出口 IP 段 (134.195.101.0/24 zombie 单点续), 需换出口 IP 段 / 联系 NVCF 运维 /
  核查 function 出口路由, 非 nv_gw 单参数可解。
