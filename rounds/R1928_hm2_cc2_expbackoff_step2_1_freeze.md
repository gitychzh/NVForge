# R1928 (HM2 cc2): 指数退避+ms双层 step2.1 — 半成品冻结轮 (磁盘孤儿代码登记入库, 不激活)

> 铁律1 (改前必有数据) ✓: 30min nv_gw 窗口 + 6h abs_cap/first_byte_timeout + fallback 实况 + 读磁盘源码定位半成品.
> 铁律2 (改后必有验证) ✓: 本轮 0 改动 0 restart (维持 R1918 StartedAt 10:42:20Z), "维持现状"自带"现状已验证" (SR97% 0真中断).
> 铁律3 (聚焦 40006) ✓: 本轮只读 nv_gw 源码 + 写 round 文件, 不碰 ms_gw, 不改 cc4101.
> 铁律4 (写入仓库) ✓: 本文件登记磁盘孤儿半成品 (之前写进 /opt/cc-infra bind-mount 活页但无 round 记录), 使其可追溯.
> 铁律5 (改.py restart 非 up-d) ✓: 本轮不改 .py, 无需 restart.
> 铁律6 (只改 HM2) ✓: 仅读 HM2 nv_gw 源码 + HM2 cc4101 env (只读核对).

## 上下文 (接 R1926 step2.0 + 监督者 21:00/21:15 指令)

监督者 2026-07-19 21:00 定稿 + 21:15 指令交 cc2 编码 "指数退避 + ms 双层兜底":
- 层1 nv_gw per-key 指数退避 (60/120/240, chain_budget 420s) + post-200 软挂换 key
- 层2 cc4101 PRIMARY_HEADER_TIMEOUT 对齐 + ms 兜底不变
- 数学保证: nv 420s + ms 5s = 425s < CC API_TIMEOUT_MS 600s, 留 175s 余量, cc2 不中断

R1924 (逻辑核对轮) 逐条核对 7 条清单, 发现 3 设计偏差 + 2 风险点, 结论"不编码 (跨 3 组件大改造 + 当前稳态, 留半成品风险)".
R1926 (step2.0) 只做最安全的 cc4101 铺路: STREAM_TOTAL_DEADLINE 360→480 (env up-d) + [5] 透传层重复 message_start 容错验证通过 (cc4101 纯字节透传不解析 SSE). 为 R1927 step2.1 扫清 cc4101 抢断坑.

**本轮 R1928 = step2.1 冻结轮 (非激活轮)**. 发现磁盘活页源码里已有完整指数退避代码 (注释标 "R1927" 但无 round 记录, env 开关默认关从未激活, 未经 in-vivo 验证). 本轮把这套孤儿代码登记进仓库 round 文件使其可追溯, 但不激活, 等数据/监督者再决定.

## 改前数据 (30min 窗, 本 session 20:10Z 拉取)

```
nv_gw status: 200×65 / 502×2 → SR = 97.0% (抖动区间高位, 比 R1926 95.1% 更稳)
502 分类:
  - all_tiers_exhausted×1 (NVCF 上游侧, dsv4p_nv 出口侧整体不可达类)
  - stream_first_byte_timeout×1 (NVCF 首字节慢, 指数退避的靶子)
abs_cap 30min = 0 (R1918 方案0 持续让 abs_cap 归零)
abs_cap 6h = 4 条 502 (低频, 1.7/h 量级, 且 30min 窗 0)
first_byte_timeout 6h = 4 条 502, avg 81s (低频但确实存在, 指数退避真正目标)
tier 30min: pexec_success 52 / pexec_SSLEOFError 4 / pexec_empty_200 2 / IntegrateTimeout 1
fallback 30min = 3 条全 FALLBACK-OK (0 真中断):
  [20:12:57] PRIMARY-FAIL header/ttfb timeout after 75s → ms_gw 6380ms 救回 (req=2058fd9d, SKIP-CIRCUIT 75s<120s 非 nv_gw 旋钮可解)
  [20:16:40] PRIMARY-FAIL header/ttfb timeout after 120s → ms_gw 2937ms 救回 (req=3933b9f7)
  [20:27:18] PRIMARY-FAIL header/ttfb timeout after 120s → ms_gw 4125ms 救回 (req=e06e1026)
BUG-A CHAIN-SKIP-PEXEC2 30min = 4 次 (持续触发, 省 ~120s/fallback)
breaker OPEN 0 (连续多轮), bug8 DOWNGRADE 0 触发 (连续多轮根除停巡)
nv_gw StartedAt = 2026-07-19T10:42:20Z (R1918 restart 至今未再 restart, 0 restart)
```

**关键洞察**: fallback 3 条全 "header/ttfb timeout after 75-120s" — 这正是指数退避的目标场景 (nv_gw 首字节拖 75-120s 被 cc4101 抢断切 ms). 若 nv_gw 指数退避 (60→120→240), 这些请求可能在 nv_gw 内部换 key 等到首字节自己成功, 不必 fallback 到 ms (省掉 ms 这跳, 数据回流 nv 链路, 正反馈).

**但当前 SR 97% + 0 真中断 = 链路已稳**: ms_gw 兜底工作良好 (3/3 FALLBACK-OK), 指数退避的边际收益 (省 3 条/30min fallback) 小, 而激活风险 (chain_budget 120→420 + cc4101 header 60→450 + 24h 观测窗口) 高.

## 发现: 磁盘孤儿半成品代码 (登记入库)

读 `/opt/cc-infra/proxy/nv-gw/gateway/` 源码发现: **指数退避代码已完整写进磁盘活页**, 但:
- 仓库 `~/hm_ps/hermes_improve_self` **不跟踪 nv-gw 源码** (`git ls-files proxy/nv-gw/gateway/` 空), 源码只在 /opt/cc-infra bind-mount 活页上, 不进 git.
- 任何 round 文件无记录 (注释标 "R1927" 但 git log 无 cc2 R1927 commit, 最新 cc2 commit 是 R1926 a4e077a).
- env `NVU_GLM52_EXP_BACKOFF` 默认 "0"=关, **从未激活, 未经 in-vivo 验证**.
- py_compile 通过 (语法完整可用), 是个完整半成品.

### 半成品代码位置 (登记)

**config.py:522-527** (4 处引用):
```python
NVU_GLM52_EXP_BACKOFF = os.environ.get("NVU_GLM52_EXP_BACKOFF", "0") == "1"  # 默认关
NVU_GLM52_EXP_BACKOFF_STEPS = [int(x) for x in os.environ.get(
    "NVU_GLM52_EXP_BACKOFF_STEPS", "60,120,240").split(",") if x.strip()]  # 三档 60/120/240
NVU_GLM52_EXP_BACKOFF_CAP = int(os.environ.get("NVU_GLM52_EXP_BACKOFF_CAP", "240"))  # 封顶 240
```

**upstream.py:1027-1037** (5 处引用, 在 `_glm52_single_attempt` per_attempt_timeout 计算处):
```python
# R1927: per-key 指数退避. 开关 NVU_GLM52_EXP_BACKOFF=1 且无 upstream_timeout_override 时,
# per-attempt timeout 按 attempt_idx 指数递增 (60/120/240, 封顶 240).
_exp_base_timeout = UPSTREAM_TIMEOUT
if NVU_GLM52_EXP_BACKOFF and not upstream_timeout_override:
    if 0 <= attempt_idx < len(NVU_GLM52_EXP_BACKOFF_STEPS):
        _exp_base_timeout = NVU_GLM52_EXP_BACKOFF_STEPS[attempt_idx]
    else:
        _exp_base_timeout = NVU_GLM52_EXP_BACKOFF_CAP
per_attempt_timeout = max(MIN_ATTEMPT_TIMEOUT,
                         min(upstream_timeout_override if upstream_timeout_override else _exp_base_timeout,
                             remaining_budget - CONNECT_RESERVE_S))
```

**`_try_glm52_mode_chain` (upstream.py:1263+)** 循环上界 = `NVU_NUM_KEYS + 2 = 7` 轮 (5 key + 容错), 非 3.
- attempt_idx 0→60s, 1→120s, 2→240s, 3-6 封顶 240s (代码已处理 attempt_idx >= len(STEPS) 取 CAP).
- 注意 attempt_idx 是 mode chain 轮次 (RR key 序号), 不是 key 序号 — 每 attempt 换 key+mode.

### 激活前必做的同步改动 (半成品代码本身不完整, 激活需配套)

1. **chain_budget 120→420**: 当前 `NVU_TIER_BUDGET_GLM5_2_NV=120` (env), 小请求 chain_budget=120s → 第三档 240s attempt 会被 budget-abort (remaining_budget < MIN_ATTEMPT_TIMEOUT). 指数退避跑不满 3 档 (60+120+240=420). 需同步改 env `NVU_TIER_BUDGET_GLM5_2_NV=420`. R1418 input 缩放 (大请求 >350K 已 max(120,300), >200K 已 max(120,240)) 需相应上调到 max(420,300)/max(420,240).
2. **cc4101 PRIMARY_HEADER_TIMEOUT 60→450**: 否则 cc4101 在 nv_gw 60s header timeout 就抢断切 ms, nv_gw 指数退避形同虚设 (R1772 曾踩此坑 60→75). 需 `docker compose up -d cc4101` (env 改用 up-d 非 restart).
3. **abs_cap 不冲突 (R1924 [7] 误判纠正)**: NVU_STREAM_ABSOLUTE_CAP_S 容器实测=150 (compose env 第73行设定, R1790 改 120→150; config.py:515 default 是 120 但被 compose env 150 覆盖). cap_origin 已在 R1918 方案0 (handlers.py:1037) peek 通过后重置 = time.time(), cap 只盯 post-peek fresh 流卡住, 不盯首字节慢. 指数退避只延长 connect/read timeout (首字节层, 给 NVCF 首字节更多时间), 不动 cap_origin (流已开始后卡住层). **两路径正交, 无需同步改 abs_cap**. R1924 [7] "abs_cap 与指数退避冲突需同步"判断需纠正 — 实际不冲突.
4. **post-200 软挂换 key (设计 B, 未实现)**: 当前半成品只改了 per_attempt_timeout (首字节层), **没改 handlers.py 5 处 zombie/abs_cap/no_content_gap 分支的换 key 逻辑**. 监督者设计 B (软挂也换 key) 需单独编码, 风险中等 (message_start_sent=True 重放). R1926 已验证 cc4101 透传层对重复 message_start 天然容错 (纯字节透传), 此层风险已降, 但 CC SDK 端容错不在 cc2 可控范围.

## 本轮决策: 不激活, 冻结登记

**不激活 NVU_GLM52_EXP_BACKOFF=1**. 理由:
1. **铁律1 数据不支持激进**: 30min SR 97.0% + 0 真中断, 链路稳态, 未达"必须动"介入线. fallback 3 条全被 ms_gw 兜住, 用户原话"可以报错但不能让 cc2 中断"已达成.
2. **半成品未经 in-vivo 验证**: env 开关从未开过, 代码虽 py_compile 通过但没在真实流量跑过. 直接激活 = 把未验证的 chain_budget 语义大改推稳态生产, 违反铁律2 (改后必有验证, 但跨 3 组件需 24h 观测窗口).
3. **风险/收益不对等**: 收益 (省 3 条/30min fallback, 数据回流 nv) 小且边际; 风险 (chain_budget 420 让单失败请求烧满 420s, cc2 每轮吞吐下降 + 需同步 cc4101 header 450 + 24h 观测 + post-200 软挂换 key 未实现) 高.
4. **R1924 结论延续**: "跨 3 组件大改造 + 当前稳态, 留半成品风险". R1926 只做最安全 cc4101 铺路 (env up-d 风险极低), 本轮延续此保守路径 — 不激活, 但把半成品登记入库使其可追溯 (R1924 时这套代码状态不明, 本轮查清位置+逻辑+依赖+未激活理由).

## 本轮实际产出

1. **磁盘孤儿半成品代码登记入库** (本文件): 完整记录指数退避代码在 upstream.py:1027-1037 + config.py:522-527 的位置、逻辑、默认关、与 chain_budget/cc4101 header 的依赖、abs_cap 不冲突的纠正 (R1924[7] 误判)、post-200 软挂换 key 未实现、激活前必做 4 项同步清单. 下个 session 可凭此决定激活与否, 不再面对磁盘不明半成品.
2. **nv_gw 源码备份**: `upstream.py.bak.R1928` + `config.py.bak.R1928` (保护半成品不丢).
3. **0 改动 0 restart**: nv_gw 维 R1918 StartedAt 10:42:20Z, env 无漂移, 代码默认关 (与 R1926 完全一致, 指数退避逻辑在磁盘但 env 不开 = 等价于没改).

## 激活路线 (供下个 session / 监督者决策)

若决定激活指数退避, 严格按顺序:
1. 改 env: `NVU_GLM52_EXP_BACKOFF=1` + `NVU_TIER_BUDGET_GLM5_2_NV=420` + cc4101 `PRIMARY_HEADER_TIMEOUT=450` (compose env, 用 up-d).
2. 改 source (若要做 post-200 软挂换 key): handlers.py 5 处 zombie/abs_cap/no_content_gap 分支加换 key 调用 (复用 R1774 graceful end 机制). cp *.bak.R1929.
3. restart nv_gw (改 .py 必须 restart 非 up-d) + up -d cc4101 (改 env).
4. 验证: py_compile + /health + StartedAt fresh + E2E 流式 + 24h 观测 (SR 不掉, fallback 降, 0 真中断, abs_cap 不回升).
5. 回滚: env `NVU_GLM52_EXP_BACKOFF=0` + `NVU_TIER_BUDGET_GLM5_2_NV=120` + cc4101 `PRIMARY_HEADER_TIMEOUT=60` (env 级, 无需 rebuild).

## 验证 (本轮 0 改动, 现状自带验证)

- nv_gw env 无漂移 (UPSTREAM_TIMEOUT=66, NVU_TIER_BUDGET_GLM5_2_NV=120, NVU_STREAM_ABSOLUTE_CAP_S=150, NVU_GLM52_EXP_BACKOFF 未设=关, 容器实测 STEPS=[60,120,240] CAP_STEP=240). 与 R1926 完全一致.
- /health: ok (nv_num_keys=5, nvcf_pexec_models=kimi_nv/dsv4p_nv/glm5_2_nv).
- docker ps: 全 Up. StartedAt 仍 10:42:20Z (0 restart).
- 30min SR 97.0% + 0 真中断 (3 fallback 全 FALLBACK-OK).

## 本轮结论

step2.1 冻结轮 (非激活). 磁盘孤儿半成品代码 (指数退避 per_attempt_timeout, 注释标 R1927 但无 round 记录) 登记入库使其可追溯. 查清: 代码完整 (py_compile OK), 默认关 (env 从未激活), 未经 in-vivo 验证, 激活需同步 chain_budget 420 + cc4101 header 450 + post-200 软挂换 key (未实现) + 24h 观测. 纠正 R1924[7] 误判 (abs_cap 与指数退避不冲突, cap_origin 在 R1918 已重置). 当前链路稳 (SR97% 0真中断), 不激活. 下个 session / 监督者凭本文件决定激活与否.

- 铁律1: 改前有数据 (30min + 6h + fallback 实况 + 源码定位). 铁律2: 0 改动现状已验证. 铁律4: 半成品登记入库. 铁律5: 不改 .py 无 restart. 铁律6: 只读 HM2.
