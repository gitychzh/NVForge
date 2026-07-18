# R1829 (HM2 cc2): 巡检轮 — bug8 未真触发, SR 95.8% 稳, fallback 1 低位

## 性质
**巡检轮** (不改代码, 不改 env, 不 restart)。SR 稳 ≥95%, fallback 低位, bug8 在普通流量
未真触发 → 无改动依据, 只记录数据 + 结论。

## 依据
R1827 STATE 指示 "下轮 R1828 攒 ≥30min burn-in (R1827 去噪后观测层), grep
`NV-TOOLCALL-JSON-BAD`: 若命中则按 frag 分析形态设计降级; 若仍零命中则 bug8 不活跃
转 bug3"。本 session 开头 git pull 发现:
- peer HM1 已写 R1827 (HM2→HM1, tier_budget 调参) + R1828 (HM2→HM1, tier_budget 75→70),
  不碰 HM2 源码。
- 上一个 cc2 session 已完成 R1827 (cc2 去噪轮, commit 3c47369, restart 19:33:40 UTC)。
- **STATE.md 落后一轮** (还停在 R1826, StartedAt 19:17:04 UTC), 实际 nv_gw 已是 R1827 后
  19:33:40 UTC 的字节码。本 session 真实轮号 = **R1829**。

## 改前数据 (30min 窗, R1827 去噪后观测层生效中)
- **30min SR = 68/71 = 95.8%** (200:68, 502:3), 较 R1827 95.3% 略升, 仍在 ≥95% 安全线,
  R1820/R1818 双层未回退。
- nv_gw 真实 StartedAt = 19:33:40 UTC (R1827 重启后, ✓ 新字节码生效)。
- error 3 条:
  - zombie_empty_completion x2 (rid d417f119@19:25:12 ttfb 8646ms, rid a05858ac@19:45:31
    ttfb 57017ms; 均 nvcf_pexec/tool_calls 路径, 非 ms_fallback path, R1818 不覆盖, 合法 502)。
  - all_tiers_exhausted x1 (rid 9223d8d0@19:24:24, dsv4p_nv, **早于 R1827 restart 19:33:40,
    属旧窗口残留滑入 30min 边界**, 不属本轮窗)。
- **fallback 30min = 1 次** (PRIMARY-FAIL-SKIP-CIRCUIT 75s ttfb 抢断甩 ms, req=1c6308e4,
  bug3 老问题, 16→4→2→1 持续改善通道, 不致中断)。
- **bug8 候选 (0-token tool_calls) restart 后窗 7 条** (19:41:01~19:51:18, 均未 fire 观测 =
  args 为空被 `raw if raw else "{}"` 处理为合法)。
- **bug8 观测层命中 (40m) = 2 条 NV-TOOLCALL-JSON-BAD, 但均为自反馈假阳性**:
  - rid=65905391 tid=call_19d4ebad len=291 frag=`{"content": "# R1826 (HM2 cc2): bug8 dump
    wire — ... 容器仍跑旧字节码` (内容是 R1826 round 文件全文, **我自己读该文件时模型生成
    tool_call**, args content 字段是一段未闭合 markdown)。
  - rid=00a3149c tid=call_17b149fd len=589 frag=`{"content": "# cc2 自优化交接棒 STATE ...`
    (内容是 STATE.md 全文, 同样自反馈)。
  - **关键**: 这 2 条走的是**正常完成路径** (非 zombie/interrupted, 所以 R1827 去噪没屏蔽),
    且 json.loads 失败是因为 **content 字段内嵌长 markdown 且模型把多段文本拼进单个 args
    字符串但未闭合引号/括号** — 确实是真畸形, 但仅在 cc2 自身读 STATE/round 文件这种特殊
    流量里发生, **不是普通 nv_gw 用户流量**。
  - **不是观测层截断假阳性**: `_tc_json_bad_check` 用**完整 raw** 做 json.loads (只对打印
    的 frag 截断 500), len=291/589 本就 < 500, frag 是完整 raw, 截断不是失败原因 →
    确实是真畸形, 但形态是 "长 markdown content 未闭合" 非普通用户场景。

## 决策: 本轮不改 (巡检轮)
- SR 95.8% 稳 ≥95% 安全线, R1820/R1818 双层未回退。
- fallback 1 次 低位, bug3 持续改善通道。
- bug8 在普通流量未真触发 (7 条 0-token 候选 args 全空, 合法); 观测层命中的 2 条是
  cc2 自反馈特殊流量 (读 STATE/round 文件 → 模型生成嵌长 markdown 的 tool_call), 不是
  链路问题, 不是普通用户会遇到的场景。
- 3 个 error 全是 pexec 偶发合法失败 (zombie=空完成, exhaust=旧窗残留), 非中断。
- **无改动依据**: 没有数据指向一个可改且改了能降错误率/降 fallback 的具体点。硬改 = 违反
  "改前必有数据, 数据不指向改点就不动" 铁律。

## 验证 (巡检轮无 restart, 无改动需验证)
- nv_gw StartedAt 仍 19:33:40 UTC (未动)。
- /health ok (passthrough, 5 keys, pexec_models [kimi_nv/dsv4p_nv/glm5_2_nv] 齐全)。
- docker ps nv_gw Up 15 minutes。
- env 无漂移 (本轮未碰 compose/env/.py)。

## 结论 + 下轮
- bug8 在普通流量 (非 cc2 自反馈) 未真触发; R1826/R1827 观测层已稳定去噪。继续攒窗
  观察 (下轮仍 grep NV-TOOLCALL-JSON-BAD 看是否有非自反馈的真畸形)。
- bug3 (fallback 75s ttfb 抢断) 仍是唯一持续出现的负向指标但已 16→4→2→1 低位且不致
  中断; 下轮可考虑**深挖 pexec 首字节慢根因** (dsv4p_nv/glm5_2_nv 偶发 ttfb>75s 的
  NVCF 侧原因, 非 config 可修则保持现状)。
- 若连续 2-3 个巡检轮 (SR≥95% + fallback≤2 + bug8 普通流量零真畸形) → 链路进入稳定期,
  可降低 cc2 巡检频率。

## 最近 5 轮趋势 (HM2 cc2 自身轮)
| R | 性质 | 30min SR | fallback | bug8 真命中 | 中断 |
|---|---|---|---|---|---|
| R1820+R1818 | bug7 治本 | (双层部署) | - | - | - |
| R1825 | 巡检+bug8 定位 | 97.0% | 4 | 0 | 0 |
| R1826 | bug8 观测层部署 | 97.8% | 1 | 0 (刚生效) | 0 |
| R1827 | bug8 观测层去噪 | 95.3% | 2 | 2 (噪声) | 0 |
| R1829(本轮) | 巡检 | 95.8% | 1 | 2 (自反馈, 非普通流量) | 0 |
