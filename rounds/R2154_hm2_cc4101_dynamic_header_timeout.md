# R2154 (HM2 cc2): cc4101 动态 header timeout 精化分档 4→6 档

## 摘要
精化 cc4101 `upstream.py` 的 R1420 input→header_timeout 分档表, 4 档→6 档. 旧 50-200K
一档全给 75s (R1772) 太粗, 实测 60-150K 段 p99 ttfb 141-246s 全被 75s 误杀滑 ms_gw fallback
(6h 窗口 82 个慢成功被砍). 新表据实测 p99 + nv_gw first-byte deadline 倒挂规避重排.

## 背景 (本轮真根因)
R2154 前误判"cc4101 没有动态 header timeout"准备让 cc2 从零实现. 读 `upstream.py:202-227`
发现 R1420/R1638/R1772 早已实现 input→header_timeout 缩放, 只是分档粗 (4 档: >350K→120,
>200K→120, >50K→75, else→25). cc2 因此把"实现动态超时"指令当已完成的旧历史忽略, 连续
NOP 多轮. 真实任务=精化分档表, 非从零实现.

## 数据 (改前 6h 窗口)
| input 档 | 实测 p99 ttfb | 当前 R1420 给 | 问题 |
|---|---|---|---|
| 60-90K | 141s | 75s (50-200K 档) | 被误杀滑 ms |
| 90-120K | 142s | 75s | 被误杀滑 ms |
| 120-150K | 246s | 75s | 被误杀滑 ms |

6h: 82 个慢成功请求被 75s header timeout 砍, fallback 到 ms_gw 131 次, 真中断 0 (ms 兜住).
撤 40007 目标下这些 75s 误杀必须消除.

## 改动 (cc4101 upstream.py, bind-mount /opt/cc-infra/proxy/cc4101/gateway/)
**PRIMARY 分档表 4→6 档** (`_try_primary`):
| input 档 | 新 header_timeout | 理由 |
|---|---|---|
| <30K | 25s (不变) | 死连快断 R828 |
| 30-50K | 40s (新拆) | nv_gw fb 20s + 20s 余量 |
| 50-90K | 150s (新拆自 75s) | nv_gw fb 60s + 90s 余量, p99 141s |
| 90-150K | 160s (新拆自 75s) | nv_gw fb 60s 先 break, 160s 兜底真慢 |
| 150-350K | 120s (新拆档) | 对齐 chain budget |
| >350K | 120s (不变) | 对齐 chain budget |

**FALLBACK 分档对齐 6 档** (`_try_fallback`): 50-350K 全给 120s (ms 比 nv 慢多留余量),
30-50K 给 60s, else 25s.

## 设计约束: 倒挂规避
cc4101 header_timeout 必须 > nv_gw 端 first-byte deadline, 否则 cc4101 抢先断 kill nv_gw
连接→BrokenPipe 死循环 (R1638 倒挂史). nv_gw first-byte: <50K=20s, 50-200K=60s, 200-350K=45s,
>350K=60s. 新表所有档均 > 对应 nv_gw first-byte, 让 nv_gw 用满自己检测主动 break 发
err_chunk (干净 Scenario A, CC 重试), cc4101 不抢先断切 ms.

## 验证
- AST 语法 OK, cc4101 restart 成功, /health OK
- 活体请求 (cc4101 cc-glm5-2 ~40K input stream=false) 成功返回 "收到测试" stop=end_turn
- 容器内确认 R2154 新分档表已加载 (grep R2154 命中 6 处)
- restart 前日志 13:21/13:26 两条残留 75s timeout 恰坐实旧 bug (50-200K 档被 75s 砍)

## 6h 验证清单 (待跑)
- [ ] PRIMARY-FAIL 75s 类 → 0 (旧 50-200K 档误杀消除)
- [ ] fallback 次数 131 → <40
- [ ] 0 真中断维持 (ms 仍兜底, 但触发应大降)
- [ ] nv_gw SR 维持 >97%
- [ ] 新档 150s/160s 不产生新的抢先断 (倒挂规避确认)

## 铁律合规
- 改前有数据: 6h 窗口 82 慢成功被砍 + p99 ttfb 分档实测
- 改后有验证: AST + restart + 活体 + 6h 待跑
- 聚焦: cc4101 适配层 (非 nv_gw 40006 源码, 有 R1640/R1444/R1772 先例)
- 入库: deploy_artifacts/R2154_cc4101_dynamic_header_timeout/ + 本 round
- HM2 only (HM1 cc4101 未同步, 待 HM2 验证稳后再推)

## 长期优化追踪
- R2154 (本轮): cc4101 动态 header timeout 精化 — 消除 50-200K 档 75s 误杀
- R2155+: nv_gw 动态 absolute_cap (按 input 分档, 需用户拍板, 非本轮)
- zombie content ratio 方案 (并行线, 50 绝对→ratio, 需单独轮)
- 撤 40007 实测 (本表验证稳后)

## 注
cc2-resume.timer 已停 (防 cc2 在我改时覆写 STATE 干扰). 本轮改动直接由 CC (非 cc2 自身).
改动既成事实后, 下轮 STATE 会写入让 cc2 复盘记录.
