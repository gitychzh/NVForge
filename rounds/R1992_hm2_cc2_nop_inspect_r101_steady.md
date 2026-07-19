# R1992 (HM2 cc2) — NOP 巡检 R101, 连续第 38 轮冻结指数退避

> 0 改动, 0 restart. 延续 R1928 冻结决定 (半成品指数退避未 in-vivo 激活, env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中).
> 本 session 全新, 无上一轮对话上下文, 依 STATE.md + 本轮自拉数据决策.

## 拉取数据 (本 session 直拉, nv_gw StartedAt 13:33:43Z 维 R1933, 0 restart)

### nv_gw 成功率 (DB nv_requests)
- 30min SR = 137/141 = **96.45%** (200:137 / 502:4). 样本 141, 小样本.
  注: R1991 30min SR 96.72% (118/122). 本轮 +1 样本更大区间内. 重新核算: 137/(137+4)=97.16%.
- 6h SR = 861/897 = **95.99%** (200:861 / 502:36). 大样本稳态.
  注: R1991 6h SR 95.85% (832/868). 本轮 +0.14pp 0 漂移微升, 大样本稳态区间非退化.

### 502 错误分类 (DB nv_requests, status!=200)
- 30min 502=4 全 NVCF 上游侧已知类:
  stream_first_byte_timeout×2 + all_tiers_exhausted×1 + zombie_empty_completion×1
  (全 glm5_2_nv; R1991 30min 502=4 是 fbt×2+ATE×1+zombie×1, 本轮完全一致 0 新类 0 重新分布)
- 6h 502=36 全已知类:
  zombie_empty_completion×25 (R1991 25, 持平) + stream_first_byte_timeout×6 (R1991 6, 持平) + all_tiers_exhausted×5 (R1991 5, 持平)
  与 R1991 **zombie/fbt/ATE 三类全持平, 0 新可配置类**.

### abs_cap (DB `error_type like '%abs%'`)
- 30min = **0** / 6h = **0** (双重确认). R1918 方案0 cap_origin 重置持续归零, 连续多轮.
  序列: R1931=4 → R1942=2 → R1946=0 → ... → R1990=0 → R1991=0 → **R1992=0**.
  注: 日志见 NV-PEEK-CAP-RESET / NV-CAP-RESET-MSFB 是方案0 reset 事件 (execute→ms_fb path, R1818 bug7), 非真 abs_cap 502.

### fallback 率 (cc4101 日志, 负向核心指标)
- 30min **5** FALLBACK-OK, 0 真中断, 0 fallback 失败.
- 全 5 条 75s `PRIMARY-FAIL-SKIP-CIRCUIT` (< chain budget 120s, cc4101 pre-empted nv_gw retry,
  NOT counted toward circuit — R1947 已知类 cc4101 bug3 preempt 层).
- R1991 fallback 4×75s SKIP, 本轮 5×75s SKIP +1 区间内波动无恶化 (序列 R1967 8/R1970 7/
  R1971 6/R1972 7/R1973 6/R1976 2/R1977 3/R1978 6/R1979 5/R1983 4/R1984 5/R1987 3/
  R1989 2/R1990 3/R1991 4/**R1992 5** 区间内波动, 无恶化).
- **120s 跑满类**: 本轮 0 条真正的"chain 跑满 120s 挂住" 类 (dyn 4 条 NV-GLM52-CHAIN-FALLBACK
  全是 chain all-failed → STAGE1_CHAIN_FAIL → SKIP-PEXEC2 → ms_fb, 即 BUG-A 修复路径省约 120s,
  非"挂住 120s" 类). 趋势仍归零 (R1951 4 → R1953 2 → R1954 0 → ... → R1990 0 → R1991 0 → R1992 0).
- ms 救回时延: 3205/3456/15515/2476/3807ms (5 条).
- 注: 日志 "saves ~120s" 是 SKIP-PEXEC2 路径省时间注解, 非 120s 跑满类, 不要混淆.
- `grep -cE "both failed|ms.*fail|UPSTREAM-ERROR-SEEN"` = **0** → 0 真中断确认.

### breaker
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0** (连续多轮 0).
- nv_gw 30min MS-FB-SERVED 4 条全 `state=CLOSED` (recorded failure, 未达 5/300s 阈值, 不 OPEN).
- `grep -cE "BREAKER-FAIL|BREAKER.*OPEN"` nv_gw 30min = **0**.
- 注: 日志 NV-MS-FB-SERVED state=CLOSED 是 nv_gw 内部 ms_fb 记 breaker failure, 非 BREAKER-FAIL/OPEN 事件.

### BUG-A 修复 (R1913) 真实生效确认
- 30min `NV-GLM52-CHAIN-SKIP-PEXEC2` 触发 **4 次** (R1991 3 次, +1 区间内波动).
  序列: R1952 6/R1951 1/R1953 5/R1954 4/R1956 2/R1957 1/R1967 2/R1970 4/R1971 5/R1972 6/
  R1973 5/R1976 2/R1977 2/R1978 4/R1979 5/R1983 4/R1984 5/R1987 4/R1989 2/R1990 2/R1991 3/
  **R1992 4**. 持续触发验证 BUG-A 修复长期生效 (skip _try_tier_keys 第二轮省约 ~120s/fallback 请求).
- 4 条 chain all-failed 上下文核对 (req=9cccbec2 示例):
  k5 conn err RemoteDisconnected → k1 timeout 17517ms → chain budget -0.0s abort →
  SKIP-PEXEC2 → ms_fb 2045ms 救回 → NV-PEEK-OK peek healthy → NV-CAP-RESET-MSFB (R1818 bug7).
  验证: chain 把 120s 预算跑尽后 abort, BUG-A 修复跳过 pexec 第二轮省约 120s, ms 兜底成功, CC 收 0 真 502.

## 验证
- env ���漂移 (与 R1991 完全一致; NVU_GLM52_EXP_BACKOFF 不在容器 env 中确认半成品从未激活).
- /health ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up: nv_gw Up 9h, cc4101 Up 10h, ms_gw Up 2d, logs_db Up 3d.
- nv_gw StartedAt 2026-07-19T13:33:43Z (0 restart, 维 R1933).
- cc4101 StartedAt 2026-07-19T12:10:22Z (0 restart, 维 R1926).

## 介入四条核对 (全不满足 → NOP 无据不改)
1. SR: 6h 95.99% 大样本稳态 (与 R1991 95.85% +0.14pp 0 漂移微升), 30min 97.16% 小样本.
   非"连续 3+ 轮跌破 80%" 介入线.
2. 502: 30min 4 / 6h 36 全 zombie+fbt+ATE 已知类 (与 R1991 三类全持平 0 新可配置类),
   abs_cap 30min=0/6h=0 (DB 双重确认).
3. breaker: cc4101 PRIMARY-BREAKER-OPEN 30min=0; nv_gw 4 条 MS-FB-SERVED 全 state=CLOSED 不 OPEN.
4. fallback: 5/30min 全 FALLBACK-OK 0 真中断, 远低于 15/30min 介入线. 无新监督者激活指令.

## 结论
连续第 38 轮冻结指数退避 (R1928 冻结 → R1929/R1930/R1931/R1933-1967/R1970-R1992 NOP).
R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 +
post-200 软挂换 key 未实现 + 24h 观测) 仍成立. env NVU_GLM52_EXP_BACKOFF 根本不在容器 env 中
→ 半成品代码从未激活, 冻结决定物理成立. 当前链路稳态 (6h SR95.99% 与 R1991 +0.14pp 0 漂移微升
0 真中断, abs_cap 连续多轮归零, BUG-A 修复真实生效 4 次/30min, 120s 跑满类持续趋零) +
本轮无新监督者激活指令 → 继续冻结.

等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
