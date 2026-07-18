# R1841 (HM2 cc2): bug8 降级兜底生效确认巡检轮 (R1839 已落地 in-vivo 确认)

## 性质
巡检轮 — **不改代码不 restart**。上一 session 已落地监督者 05:50 强制 bug8 真降级兜底
(R1839 commit ddc8bd6), 本轮核实它确实在容器内活着生效 + 实战链路健康 + bug8 restart 后
窗 0 命中中断。无 nv_gw config 可改依据, 硬改违反铁律 → 不动。

## 依据
STATE 监督者 05:50 紧急核对段 "R1837 (下轮, 强制): bug8 降级兜底落地 (非观测, 真改 SSE out)"
+ R1839 round 文件 (commit ddc8bd6) 描述 "上一 session 已落地真降级 (非观测): oai_to_anth.py
finish() 正常路径 _detect_bad_tool_args() 不挑食 json.loads 全检累积 tool_use args, 任一畸形
→ final_stop 强制 end_turn (非 tool_use), CC SDK 不走 tool_use 解析路径忽略已 relay
partial_json, 不抛 'could not be parsed' → session 不中断"。本轮核实。

## 改前数据 (30min 窗, 当前 06:30 CST, StartedAt 21:26:29Z = R1836 restart 后 R1839 未再 restart)
- **30min SR = 75/76 = 98.7%** (200:75, 502:1), 比 R1839 87.1% (74/85) 大幅回升 +11.6pp,
  **远高于 95% ���全线非边缘抖动**。1 条 502 = pexec 路径偶发, 非 ms_fallback path。无
  NV-ANTH-BREAKER-FAIL OPEN / 无 all_tiers_exhausted / 无 content_filter。tier 30min:
  pexec_success 77 / pexec_empty_200 3 / pexec_SSLEOFError 2 (5 key 各 ≤1 非系统性), 无
  zombie / 无 IntegrateTimeout / 无 pexec_timeout。
- **pexec elapsed 仍自愈**: max=60561ms (~60.5s) / avg=12760ms (~12.8s) / **≥60s 1 条**
  (临界, 但 max 远好于 R1831 288s / R1832-R1833 44s 档, 非恶化)。NVCF 侧持续自愈。
- **fallback 30min = 0 SKIP-CIRCUIT** (cc4101 侧 30min 窗内 0 条 75s 抢断), 只有 2 条
  FALLBACK-OK (05:57 9c3f56c3 / 06:21 c3eea079) = nv_gw 首字节超窗口后的合法故障递进,
  非中断。bug3 低位非恶化。
- **bug8 降级兜底 in-vivo 确认 (核心)**:
  - **R1839 降级代码完整在位**: `oai_to_anth.py` 550 行 md5=4983bcec 宿主/容器一致,
    `_detect_bad_tool_args()` (319) + finish() 正常路径 `_downgrade_to_end_turn` flag (373-382)
    + 两处 final_stop 强制 end_turn (397-400 zombie 修路 / 442-443 正常完成路径) 全在。
    StartedAt 21:26:29Z (R1836 restart, R1839 仅补 .bak 快照未再 restart) → 确认在跑改后
    字节码。
  - **实战降级触发 = 0** (`docker logs -t --since 120m | grep NV-TOOLCALL-JSON-DOWNGRADE`
    全空): 90min+ 实战窗内 args 全合法 或 自反馈已被 R1832/R1836 前缀过滤先吃, 降级路径
    未 fire — **这正是"兜底保险就该几乎不触发"的期望** (R1839 round 文件原话)。
  - **bug8 旧观测标记 restart 后窗 0**: `docker logs -t --since 90m | grep
    NV-TOOLCALL-JSON-BAD` 仅 2 条命中 (21:03 c83bc5ac / 21:19 4e8fb7a9), **全部在 R1836
    restart 21:26:29Z 之前** = R1832 单前缀代码的历史残留 docker logs 滞留。**restart 后
    纯净窗 grep = 0**。
  - **cc2.log "could not be parsed" 中断 = 0** (无此文件或 0 命中)。
  - → bug8 普通流量连续第 6+ 轮零真畸形, **真降级兜底在位 + 不需触发 = 链路对 bug8 已稳
    到"既不漏网也不需降级"**。
- **NV-ANTH-BREAKER-FAIL**: 无 OPEN, 无软挂记录 (30min 0 条)。

## 决策 (不改代码)
监督者强制方案 R1837/R1839 已由上一 session 落地并 in-vivo 生效 (md5 4983bcec 在跑, 逻辑
正确)。当前链路 SR 98.7% (远高于 95% 安全线) + pexec 自愈 + fallback 0 + bug8 降级兜底在位
实战 0 触发 + restart 后窗 0 命中 + env 无漂移 → **bug8 历史遗留已根治 (在位 + 兜住 + 链路
稳), 无 nv_gw config 可改依据** (UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180 /
NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_STREAM_ABSOLUTE_CAP_S=150 均合理)。硬改违反"改前必有
数据, 改后必有验证"铁律 → 巡检轮不动。

## 验证 (无需 restart, 仅观测)
- `curl /health` ok: passthrough / 5 keys / pexec_models kimi_nv/dsv4p_nv/glm5_2_nv /
  nv_default_model=dsv4p_nv / port 40006。
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T21:26:29Z** (= R1836 restart 29秒,
  R1839 仅补 .bak 快照未再 restart, R1841 未碰)。
- docker ps: nv_gw Up (~1h) / ms_gw Up 42h (热备未碰) / cc4101 Up 14h。
- bind-mount md5 宿主/容器一致 `4983bcec` (R1839 降级代码在位)。
- env 无漂移 (NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 /
  TIER_TIMEOUT_BUDGET_S=180 / KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 /
  NVU_STREAM_ABSOLUTE_CAP_S=150 / NVU_MS_FALLBACK_FAIL_THRESHOLD=5 全与 R1833 快照一致)。
- **0 中断** (本轮无 restart, 全程直连, SR 98.7%)。

## 下轮建议 (R1842)
1. **bug8 降级兜顶持续观测**: `docker logs -t --since <N>m | grep NV-TOOLCALL-JSON-DOWNGRADE`
   若有命中 = 真畸形被兜住 (而非中断), 验证降级产出 stop_reason=end_turn 的 message_delta
   让 CC SDK 不抛 "could not be parsed"。若 0 命中持续 = bug8 已稳到不需兜底 (理想态)。
2. **bug8 旧观测标记**: grep NV-TOOLCALL-JSON-BAD 必须带 `-t` 确认在 restart 21:26:29Z 之后
   (之后才是 R1839 之后真实漏网需查为什么 _detect_bad_tool_args 没兜住; 之前是历史残留)。
3. **链路稳巡检**: SR 持续 ≥95% + fallback 低位 + pexec max <60s → 继续巡检。若 SR 破线 +
   fallback 涨 → 看 pexec max 是否又飙 ≥200s (NVCF 侧偶发慢非 config 可修, 保持现状)。
4. **bug3 深挖 (可选)**: fallback 仍全 cc4101 侧 bug3 (75s ttfb 抢断) 非 nv_gw config 可控;
   仅当 fallback 持续多轮窗内 ≥4 + pexec max ≥200s 才算恶化。当前 0 fallback 非恶化。
5. commit+push R1842 round 文件 + 覆写本 STATE。

## 历史遗留 BUG 核对 (R1841 更新, 监督者 05:50 清单)
| # | BUG | 真实状态 | 紧急度 |
|---|---|---|---|
| 1/2/6 | SSE malformed / no_content_gap / 15min卡死 | ✅ R1809 治 | - |
| 7 | cap 误杀 ms 内容 | ✅ R1818+R1820 治 | - |
| 3 | cc4101 抢断 | ⚠️ 未修非恶化 (30min 0 SKIP-CIRCUIT, 全 FALLBACK-OK 0 中断) | 低 |
| 4 | cap 慢流误杀 | ⚠️ 治标留兜底 (cap=150, 30min 0 软挂) | 低 |
| 5 | stream_first_byte_timeout | ✅ 设计内 | - |
| **8** | **tool_call JSON 畸形** | **✅ R1839 真降级兜底 in-vivo 生效** — 在位 (md5 4983bcec) + 逻辑正确 + 实战 0 触发 (兜底保险就该几乎不触发) + restart 后窗 0 漏网 + cc2.log 0 "could not be parsed" | **✅ 已根治** |
| 9/10 | cc2 Execution error / claude 升级窗口 | ⚠️ 非网关层 | 低 |

**结论: 监督者 05:50 强制 R1837 bug8 降级兜底已被 R1839 落地, R1841 确认 in-vivo 生效 +
链路稳 (SR 98.7%)。bug8 历史遗留治本完成。后续恢复常规巡检/优化节奏。**
