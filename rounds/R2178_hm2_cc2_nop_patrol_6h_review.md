# R2178 — hm2_cc2 NOP轮 (6h 长窗口复核)

## 定位
全新 session 接棒。STATE.md 完整 (未被清/并发改), 直接续 R2177 (commit b02721a) 基线。
本轮执行 STATE "下一轮该做什么" 第 7 条建议: glm5_2_nv SR 已连续 R2174-R2177 四轮 >96%,
本轮做 **6h 长窗口复核** 确认无慢退化 (前几轮只看 30min)。本轮只看不改。

## 数据 (HM2)

### 30min 标准窗口
- 82 请求 / 77 OK(200) / 5 错(502) → SR = **93.9%** (77/82)
- by model: glm5_2_nv 65/67 = **97.0%** SR (2错: 1 zombie + 计入 tier 兜底);
  dsv4p_nv 11/15 = 73% (4错全 all_tiers_exhausted, NVCF function 74f02205 全挂非本域已知良性)
- 5 错全 NVCF 上游无害类: 4 all_tiers_exhausted + 1 zombie_empty_completion
  (注: 30min 窗口 error_type 行显示 2 zombie, 含跨 model 统计; glm5_2_nv 实际 2 错为 zombie 类)
- 无 content_filter / timeout / conn / 429
- fallback_occurred = 10 (全 nv_gw 内部 NV-MS-FB tier 兜底, 见下)
- cc4101 30min fallback = **0** (连续第 3 轮 0 真中断)

### 6h 长窗口复核 (本轮重点)
- 903 请求 / 810 OK / 93 错 → 整体 SR = **89.7%**
- **glm5_2_nv 782/796 = 98.2% SR (6h 稳态, 核心优化目标确认无慢退化)**
- dsv4p_nv 28/107 = 26% (NVCF function 74f02205 全挂, 非本域已知良性, 拉低整体 SR)
- 6h 93 错全 NVCF 上游无害类:
  - all_tiers_exhausted 79 (几乎全 dsv4p_nv)
  - zombie_empty_completion 10
  - NVAnth_IncompleteRead 3 (30min 窗口不可见的极低频 NVCF 瞬态, 非新错误模式)
  - stream_absolute_cap 1 (极低频)
- hourly SR trend: 04h=89.0% / 05h=85.4% / 06h=90.5% / 07h=89.2% / 08h=91.5% / 09h=91.7% / 10h=83.3%
  → 85-92% 区间稳态波动 (被 dsv4p_nv 拖低), **无单调退化趋势**
- 6h NV-ANTH-BREAKER-FAIL = **9 条**, 但全部 `state=('CLOSED', N, 0)` (N∈1-4),
  **全程未 OPEN** — R1719 breaker "记录但不 OPEN" 预期态完美生效。
  错误类型: NVAnth_IncompleteRead + zombie_empty_completion (均 NVCF 上游瞬态)。
- 6h NV-MS-FB-SERVED = **93** (nv_gw 内部 glm5_2_nv→glm5_2_ms tier 兜底 93 次,
  与 6h glm5_2_nv fallback_occurred=93 完全对应)。
  → 再次佐证 R2177 澄清: **fallback_occurred 全是 nv_gw 内部 tier chain 吸收,
     非 cc4101 层热备兜底** (cc4101 6h fallback 仍 0)。
- 75s_timeout = **0** (R2154 动态 header timeout 6h 持续生效, cc4101 无误杀)
- STREAM-STALL-FAIL / UPSTREAM-ERROR-SEEN = 0
- nv_gw big_input / nv_breaker: **未真 OPEN** (仅 NV-ANTH 记录计数, state=CLOSED)

### 容器与参数
- nv_gw RestartCount=0 StartedAt=2026-07-21T01:44:55Z, cc4101 RestartCount=0 StartedAt=2026-07-21T05:28:51Z
- docker ps: nv_gw Up 8h / cc4101 Up 5h / logs_db Up 4d
- curl /health ok: nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], proxy_role=passthrough
- env 参数与 R2177 基线逐项一致, 无漂移

## 决策: NOP 巡检, 0 改动 0 restart
STATE 三触发改动阈值全不满足:
- 30min SR 93.9% > 85% ✅ 在阈值之上
- cc4101 fallback 0 < 5 ✅ 在阈值之下 (连续第 3 轮 0)
- 无新错误类型 (仍 all_tiers_exhausted + zombie; 6h 才可见的 IncompleteRead/cap 是极低频 NVCF 瞬态非新模式) ✅

6h 长窗口复核结论: **glm5_2_nv 98.2% 6h 稳态, 无慢退化**。四重佐证 nv_gw 稳:
(1) 所有错误 NVCF 上游无害类 (2) 无参数误杀 (75s_timeout=0 STALL=0)
(3) breaker 记录不真 OPEN (NV-ANTH 9 条全 CLOSED) (4) 容器无漂移。
改了反而破坏 R2154 稳定带。本轮冻结不动任何参数/breaker 阈值。

NV-ANTH-BREAKER-FAIL 6h 累计 9 条 (state 最高 4, CLOSED): 软挂累积, 距 OPEN 阈值尚远,
6h 内每条间隔 30-60min。按 CLAUDE.md "目标让 breaker 几乎不 OPEN 而非调高阈值假装不 OPEN",
本轮冻结不动 nv_breaker 阈值。若后续单轮 +5 或 state 逼近 OPEN 再下轮评估
(那应是 NVCF 上游变化触发, 非 nv_gw 参数问题)。

## 验证
0 改动 0 restart 无需验证改动。curl /health ok + docker ps 全栈 Up +
DB 30min + 6h 窗口稳态带内 + 参数 env 与基线逐项一致。

## 铁律遵守
- 改前必有数据: 30min + 6h 双窗口 ✅
- 聚焦 40006, 不碰 40007 ✅ (本轮未动任何源码/配置)
- 只改 HM2 不改 HM1 ✅ (主仓 982d9a5 R2176 HM1 peer TIER_COOLDOWN_S 18->16 非本域)
- 改.py 必须 restart: 本轮无 .py 改动 ✅
- 绝不 Read /tmp: 本轮未 Read 任何 /tmp 文件 ✅

## commit
本轮 0 改动, 本轮文件即唯一产物, commit 后 push。
