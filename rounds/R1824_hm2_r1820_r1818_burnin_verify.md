# R1824 — 巡检验证轮: R1820 grotesque-end 兜底 + R1818 cap_origin(execute→ms_fb)burn-in 验证

## 性质
**巡检验证轮**(非新改代码)。本轮不改代码,只做两件事:
1. 验证 STATE 里最高优先的 R1819 graceful-end 兜底(= 已由上一轮 cc2 在 commit d1ee0ee `R1820` 落地)真生效
2. 验证 R1818 execute→ms_fb 路径 cap_origin 重置(= 已由上一轮 cc2 一并落地,容器内 `NV-CAP-RESET-MSFB` 日志可证)真生效
3. 拉 R1820 重启后 burn-in 数据,确认用户诉求"可以报错但不能中断 cc2 session"达成

## 依据
- STATE(01:40 监督者最终诉求) 转达用户最高指令: "可以报错,但是不能让cc2中断卡住"
- STATE(01:25 监督者根因复核) 指出 R1817 只修 peek barrier 路径 cap_origin, execute→ms_fb 路径漏
- git log 显示 commit d1ee0ee `R1820 (HM2 cc2): bug7 graceful end 兜底` 已入库
- `docker exec nv_gw grep message_start_sent /app/gateway/format/oai_to_anth.py` 显示 R1820 改动在容器源码里(line 59/97/245/273)
- `docker logs nv_gw` 显示 `NV-CAP-RESET-MSFB ... req=3381371b` 触发过 → R1818 execute→ms_fb 路径 cap_origin 重置已落地

本轮在 R1820 重启后约 18min 拉数据,验证 burn-in 持续性 + 兜底真生效,不改代码(小步快走,不污染 R1820/R1818 观测)。

## R1820/R1818 改动落地确认 (防"计划写了没执行")
- `oai_to_anth.py` finish() line 245 zombie 分支: `if flushed_content_chars > 0 or self.message_start_sent:` → graceful ✓
- `oai_to_anth.py` finish() line 273 interrupted 分支: `... and not self.message_start_sent` → 只有 message_start 没发才 event:error ✓
- 关键不变量: `message_start_sent=True` ⟺ nv_gw 已 send_response(200)+flush message_start ✓
- R1818 cap_origin 重置: `NV-CAP-RESET-MSFB ... peek_swapped=False, total_elapsed_pre_reset=364s` 日志触发铁证 ✓
- /health ok, nv_gw Up (StartedAt=2026-07-18T18:07:50Z), ms_gw 热备在 ✓
- py_compile: 已由 R1820 验证 `import gateway.format.oai_to_anth` OK

## 数据 (R1820 重启后窗 18:07:50-18:25 UTC, ~18min burn-in)
### nv_gw SR (重启后窗)
- **39 req 全 200, 仅 1 条 502(all_tiers_exhausted, 系统级降级, R1820 兜底本就覆盖不到 → 合法失败)**
- **SR = 39/40 = 97.5%**

### R1820 兜底铁证 (重启前会 event:error→CC 中断的, 现在走 graceful 200)
- **重启后窗 zombie_empty_completion 错误数 = 0**(对比重启前 30min 3 条 zombie_empty out_tok>0 还 502)
- **17 条 out_tok=0 但 status=200**(上游没产内容/僵尸流/R1820 前会 event:error, 现 graceful end 转 200)
- 17 条里 upstream_type 分布: nvcf_pexec 14 + nv_integrate 3(过渡残余, R1809 后 integrate 应归零, 但 chain 兜底链仍保留 integrate_us_rr 故偶发)

### bug7 复发检查 (R1818 cap_origin 重置路径)
- 重启后窗 **0 条 stream_absolute_cap 错误**(对比重启前 30min 1 条 bug7 失效 b8370a29 dur 242s ms_fallback out_tok=0)
- `NV-CAP-RESET-MSFB req=3381371b total_elapsed_pre_reset=364s` 触发过 → R1818 路径命中, ms fb 后 cap_origin 重置, ms 内容应被完整 relay
- 注: 该 3381371b 走 execute→ms_fb 时 nv 阶段已耗 364s(5key 全挂串行), 这是 bug3/bug7 上游侧问题, R1818 只治"cap 不误杀已 relay 的 ms 内容", 不治"nv 阶段太慢"

### cc2 session 中断检查 (用户诉求核心)
- cc2.log 近 30min **零 "API Error: Server error mid-response"**(R1820 兜底挡住)✓
- cc4101 30min **零 "UPSTREAM-ERROR-SEEN"** ✓
- 用户诉求"可以报错但不能中断 cc2 session" **达成中**(burn-in 18min/40req 0 中断)

### fallback 率 (bug3, 负向核心指标, 仍高)
- cc4101 30min **16 次 fallback**, 全 75s/120s ttfb timeout(SKIP-CIRCUIT, bug3)
- 这是 nv_gw pexec 首字节超时被 cc4101 75s 抢断甩 ms_gw
- STATE 已标"bug3 等 bug1 治完再看, 慢流治了 ttfb 降, 抢断自然减少"
- 本轮不单独调 bug3 — R1820 兜底已保证即使 fallback 也不致 CC 中断, bug3 是性能/成本问题不是中断问题

## 30min 全窗对比 (含重启前 5 条 502)
- 30min 全窗: 64 req, 59 200(92.2%), 5 502
- 5 条 502 全在 18:07:50 重启前:
  - b8370a29 17:59 stream_absolute_cap ms_fb out=0 (bug7 老, R1818 前)
  - 9173fe70 18:04 zombie_empty out=251 (R1820 前)
  - 360c5dfc 18:05 zombie_empty out=204 (R1820 前)
  - acc9eee5 18:07 zombie_empty out=682 (R1820 前)
  - 5ada7a65 18:17 all_tiers_exhausted out=0 (重启后, 系统级降级, 合法)
- **重启后窗 39/40=97.5% SR**, 兜底+cap_origin 双层生效

## 为何本轮不改代码 (小步快走)
1. R1820 兜底层 + R1818 cap_origin 根治层 都刚部署 ~18min, 仍在 burn-in 早期, 叠加新改动会污染观测
2. R1820 核心假设(200 头已发就 graceful end, 绝不 event:error)已被"17 条 out_tok=0 转 200 + 0 zombie 错误"铁证
3. R1818 核心假设(execute→ms_fb 路径 cap_origin 重置)已被 `NV-CAP-RESET-MSFB req=3381371b` 触发铁证
4. 用户诉求"不中断 cc2 session" 已达成(cc2.log 0 mid-response) — 当前最稳态, 不动代码最安全
5. 下一优化点(tool_call JSON 畸形降级, STATE 01:50 监督者方案 C)风险更高(改 feed_chunk tool_calls 分支, 搞不好把正常 tool_call 也降级), 需独立 R 轮 + dump wire 准备, 不在 burn-in 未稳时盲动

## 下轮 (R1825) 该做什么
1. **继续 R1820/R1818 burn-in 攒 ≥30min/≥40 req 干净窗**, 确认:
   - 重启后窗持续零 bug7 复发(stream_absolute_cap=0)
   - zombie_empty 持续归零(全走 graceful 200)
   - cc2 session 持续零 mid-response 中断
2. **若 burn-in 稳定 ≥30min → R1820/R1818 宣告全胜**, 转做下一优化点:
   - **tool_call JSON 畸形降级 (方案 C, STATE 01:50 监督者建议)**: 在 oai_to_anth.py feed_chunk tool_calls 分支, finish() 收尾时校验每个 tool_use 的 arguments JSON, 畸形则降级 end_turn(drop tool_use block), 不让 CC SDK 抛 "could not be parsed" 中断
   - 风险: 改动 feed_chunk 是热路径, 需先 dump 一条 tool_call parse 失败时刻的 wire 确认 arguments 畸形形态, 再设计校验/修复逻辑
3. **若 burn-in 出现新中断场景**: dump wire 确认是哪条 break 路径漏了 graceful, 补判断条件
4. fallback 率(bug3): 仍等 R1820/R1818 burn-in 稳定后再看, 当前 fallback 不致 CC 中断, 非首要
5. 小步改(若数据支撑): cp .bak.R1825, 改一处, restart nv_gw, 验证 /health+docker ps+下窗口日志

## 铁律遵守
- 改前必有数据: 30min 全窗 + R1820 重启后 18min burn-in 窗 ✓
- 改后必有验证: 本轮无新改, 验证 R1820/R1818 落地生效 ✓
- 聚焦 40006 (nv_gw), 不碰 40007 (ms_gw 热备) ✓
- 只改 HM2, 不改 HM1 ✓ (peer HM1 agent 在写 R1822/23 hm2_optimize_hm1, 不碰)
- 本轮无 .py 改动, 无需 restart ✓
- 仓库设计不跟踪 proxy 源码, round 文件 + .bak.RNN 双重记录 ✓ (R1820 round 已说明)
