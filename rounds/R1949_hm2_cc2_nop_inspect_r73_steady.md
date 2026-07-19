# R1949 (HM2 cc2): NOP 巡检 R73 — 稳态持续, 30min SR98.0% / 6h SR93.7% 0 真中断, 连续冻结第 11 轮延续

**铁律遵守**: 改前必有数据 / 改后必有验证 / 聚焦 nv_gw(40006) / 所有修改写入仓库 / 只改 HM2 不改 HM1 / 改 .py 必须 restart 非 up-d / 不碰 ms_gw(40007)

## 本轮性质: NOP 巡检 (0 源码改动 0 env 改动 0 restart)

新 session 接手, 读 STATE.md 棒 (R1947 已真正用 Write 覆写对齐 R1947 真实状态, 含 StartedAt 修正 R1933 13:33:43Z + 轮号基线推进 + 终结 R1930/R1942/R1943/R1946 反复出现的"声称覆写未落"老问题; 下半段监督者巡视历史逐字保留). git pull 后 origin/main 最新 = R1948 (peer HM1 已占 R1948 = `22a0dce`, HM2→HM1 轮, 前缀 `R1948_hm2_optimize_hm1`, 只改 HM1 对 HM2 0 影响). cc2 上一轮 = R1947 (fe725ad, NOP 巡检 R72). **本轮 cc2 从 R1949 起** (跳过 R1948 防 peer 撞号视觉混淆, 虽前缀区分). STATE.md 棒上半段已对齐 R1947 → 本轮职责:
1. 继续巡检 R1933 NameError 修复后稳态, 确认无回归无新 bug.
2. 维持 STATE.md 上半段对齐到 R1949 真实状态 (含本轮新鲜 30min 数据 + 轮号基线推进), 延续 R1947 已解决的"真正覆写"状态, 不回退.

## 数据 (本 session 拉取, DB 时钟 = 2026-07-19 16:54:07Z UTC = 00:54 CST, nv_gw StartedAt 13:33:43Z = 已起 ~3.3h)

### nv_gw 健康 + 源码状态
- nv_gw StartedAt = **2026-07-19T13:33:43Z** (= R1933 restart, R1933→R1949 未再 restart).
- cc4101 StartedAt = 2026-07-19T12:10:22Z (= R1926 step2.0 env up-d).
- /health ok (nv_num_keys=5, pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv, nv_default_model=dsv4p_nv, proxy_role=passthrough).
- docker ps 全 Up (nv_gw Up 3 hours / ms_gw Up 2 days / cc4101 Up 5 hours; docker ps "Up N" 是容器创建时刻非 restart, 精确以 inspect StartedAt 为准).
- **源码状态 = R1933 已验证后状态** (env 快照与 R1947 完全一致无漂移).
- **NVU_GLM52_EXP_BACKOFF env 未设=关** (R1928 半成品冻结, 从未 in-vivo 激活, 连续第 11 轮).

### 30min nv_gw 成功率 (本轮主窗口, 新鲜数据)
- SR = 49/50 = **98.0%** (200:49 / 502:1), 比 R1947 30min 92.9% 高 (小样本 50 条抖动), 抖动区间常态 (R1929 91.7 / R1930 92.5 / R1931 91.4 / R1941 92.5 / R1942 93.75 / R1943 94.7 / R1946 30min 78.9 小样本 / R1947 92.9 / R1949 98.0, 区间稳态非退化).
- 502 分类: zombie_empty_completion×1 (glm5_2_nv 出口 IP 段同源, R1907-R1909 起持续同段, 已知上游侧).
- **abs_cap 30min = 0** (R1918 方案0 cap_origin 重置让 abs_cap 持续归零, 连续多轮; 错误分类中无 abs_cap 出现).

### tier 30min
- pexec_success 43 / 500_nv_error×5 (NVCF 返 500 真错误, 其中 4 条被 retry 吸收到 200, 1 条漏网成最终 502 — nv_gw retry 机制正常吸收表现, 已知类) / pexec_empty_200×4 (glm5_2_nv 首字节快回空中间态被 retry 吸收到 200) / IntegrateTimeout×1 / pexec_SSLEOFError×1 (出口 IP 段 134.195.101.0/24 续抬头).
- 全已知类, 无新可配置错误类.

### 6h nv_gw 成功率 (大样本验证稳态)
- SR = 550/587 = **93.7%** (200:550 / 502:37), 与 R1939 (95.3%) / R1942 (95.2%) / R1943 (94.9%) / R1946 (93.8%) / R1947 (93.6%) 几乎完全一致区间, 稳态持续.
- 502 分类: zombie_empty_completion×21 / all_tiers_exhausted×12 / stream_first_byte_timeout×4. 全已知类, abs_cap 6h=0 (R1918 方案0 持续归零).

### fallback (负向核心指标, cc4101 视角)
- 30min = **7 条** (R1947=3, 本轮抬升但仍 <15/30min 介入线; 6h=81).
- 模式拆解 (30min 7 条):
  - 前 5 条全 **75s SKIP-CIRCUIT** 间歇 (PRIMARY-FAIL-SKIP-CIRCUIT primary timeout after 75082ms < chain budget 120s) → cc4101 pre-empted nv_gw retry (cc4101 bug3 preempt 层, 非 nv_gw 旋钮可解) → 全 FALLBACK-OK 被 ms 兜住 (ms 1.9-9.3s 救回).
  - 后 2 条 **120s timeout** (00:45:23 / 00:47:30) **无 SKIP-CIRCUIT 标记** → 120s ≥ chain budget, 被正常计入 circuit 计数 (NVCF 上游侧该请求 chain 跑满 120s 仍没回首字节才被 cc4101 判 header timeout 切走). 仍是首字节慢已知类, ms 都成功兜住.
- **0 真中断 0 fallback 失败**: 7 条全 FALLBACK-OK, CC 收 0 真 502. 用户诉求 "可以报错但不能让 cc2 中断" 仍达成.

### breaker
- nv_gw NV-ANTH-BREAKER-FAIL 30min = **0** / BREAKER-OPEN 30min = **0**.
- cc4101 PRIMARY-BREAKER-OPEN 30min = **0**.
- breaker **OPEN 0 连续多轮** (R1946 记录 6h=14 全集中 21:27-21:33 CST 旧突发自愈, 30min=0).

## 决策: NOP 巡检 (介入四条全不满足)

对照 STATE.md 介入四条:
1. **SR**: 6h SR 93.7% 大样本稳态区间 (R1939-R1947 93.6-95.3%), 30min SR 98.0% (小样本但远 >80%). 未达"连续 3+ 轮跌破 80%"介入线. ✅ 不触.
2. **502 分类**: 30min 502=1 zombie + 6h 502=37 全 zombie(21)+ATE(12)+first_byte_timeout(4) 已知类. abs_cap 30min=0/6h=0 (R1918 方案0 持续归零). 无新可配置错误类. ✅ 不触.
3. **breaker**: OPEN 30min=0 nv_gw BREAKER-FAIL 30min=0, 连续多轮 OPEN 0. ✅ 不触.
4. **fallback**: 30min=7 < 15/30min 介入线, 全 FALLBACK-OK 0 真中断 0 fallback 失败. 无新监督者激活指令. ✅ 不触.

R1928 冻结理由 (半成品未 in-vivo 验证 + 激活需同步 chain_budget 120→420 + cc4101 header 60→450 + post-200 软挂换 key 未实现 + 24h 观测窗口) 仍成立. 当前链路稳态 (SR93.7% 0 真中断) + 本轮无新监督者激活指令 → 继续冻结, NOP 无据不改.

## 本轮改动: 0 源码改动 0 env 改动 0 restart

- env 无漂移 (与 R1947 完全一致), 源码无改动, 不 restart.
- nv_gw StartedAt 维 2026-07-19T13:33:43Z (R1933 restart, R1933→R1949 未再 restart).
- cc4101 StartedAt 维 2026-07-19T12:10:22Z (R1926 step2.0 env up-d).

## 验证

- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: 全 Up.
- env 快照与 R1947 完全一致无漂移.
- nv_gw StartedAt 13:33:43Z / cc4101 StartedAt 12:10:22Z (0 restart).

## 下一轮

- 继续 NOP 巡检 R74. 拉新鲜 30min 数据看 SR/fallback/breaker 抖动是否仍在已知区间. 当前 SR 93.7% 是区间稳态, 链路稳 — 502 全 zombie+ATE+first_byte_timeout (出口 IP 段同源/已知上游侧), fallback 全 75s/120s 被 ms 兜住 0 真中断.
- **指数退避激活决策仍冻结 (连续第 11 轮)**: R1928 冻结理由仍成立. 等监督者再授权激活或数据恶化 (SR 连续 3+ 轮跌破 80%) 再动.
- **本轮新观察点**: 30min fallback 7 条比 R1947 (3 条) 抬升, 仍 < 15/30min 介入线. 后 2 条是 120s timeout 无 SKIP-CIRCUIT (正常计入 circuit), 模式与 75s SKIP-CIRCUIT 不同, 仍全被 ms 兜住 0 真中断. 下轮若 120s timeout 持续抬头或 fallback 突破 15/30min, 再评估是否动 breaker 阈值或 TIER_TIMEOUT_BUDGET — 当前抬不上来属 cc4101 bug3 preempt 层 (75s) 或 NVCF 上游首字节慢 (120s), nv_gw 单旋钮解不了.
- 沿用给监督者方向: abs_cap/zombie/empty200/all_tiers_exhausted 同源首字节慢/空/出口侧不可达是 NVCF 上游侧 + 出口 IP 段 (134.195.101.0/24 zombie 单点续; dsv4p_nv 出口 egress 空), 需换出口 IP 段 / 联系 NVCF 运维 / 核查 function 出口路由, 非 nv_gw 单参数可解.
- peer HM1 agent 持续在 HM1 侧收紧 (R1948 HM2→HM1 = 22a0dce, 只改 HM1 对 HM2 0 影响), 抢号区间, 写轮前必 git pull 看最新号 +1 防 peer 抢号. peer 的 hm2_optimize_hm1 序列号和 cc2 序列号独立计数会撞号, 但前缀不同 (cc2 用 R1NNN_hm2_cc2_, peer 用 R1NNN_hm2_optimize_hm1.md).
