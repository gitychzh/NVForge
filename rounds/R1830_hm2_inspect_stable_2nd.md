# R1830 (HM2 cc2): 巡检轮 — bug8 普通流量连续零真畸形, SR 95.8% 第 2 轮双稳, fallback 2 低位抖动

## 性质
**巡检轮** (不改代码, 不改 env, 不 restart)。SR 95.8% **连续第 2 轮**稳 ≥95%, fallback
低位抖动 (1→2), bug8 普通流量连续零真畸形 → 无 nv_gw 侧可改依据, 只记录数据 + 结论。

## 依据
R1829 STATE "下一轮该做什么" 指示:
1. 拉 30min 数据确认 SR/fallback/error 是否仍稳 (SR≥95%/fallback≤2)。
2. grep `NV-TOOLCALL-JSON-BAD` 看是否有非自反馈的真畸形:
   - 若有真畸形 → 分析形态设计降级逻辑。
   - 若仍只有自反馈或零命中 → bug8 不活跃, 链路稳定, 可深挖 bug3 pexec ttfb 慢根因
     或继续巡检 (连续 2-3 个巡检轮稳定 → 降低 cc2 巡检频率)。

本轮正是 "连续 2-3 个巡检轮稳定" 临界: R1829+R1830 两轮 SR 95.8% 双稳, bug8 连续零真畸形。

## 改前数据 (30min 窗, StartedAt 仍 19:33:40 UTC = R1827 后状态, 本轮未 restart)
- **30min SR = 68/71 = 95.8%** (200:68, 502:3), 与 R1829 完全一致, **连续第 2 轮**稳 ≥95%
  安全线, R1820/R1818 双层未回退。
- nv_gw 真实 StartedAt = 2026-07-18T19:33:40Z (R1827 重启后, 本轮未动, ✓ 字节码未漂移)。
- **fallback 30min = 2 个请求** (较 R1829 的 1 个 +1, 低位抖动非恶化):
  - req=bfdd6036@03:54:14, ttfb 75080ms, PRIMARY-FAIL-SKIP-CIRCUIT (75s < chain budget
    120s, cc4101 抢断甩 ms, FALLBACK-OK 3469ms)。
  - req=0b62e8f0@03:56:42, ttfb 75032ms, 同上, FALLBACK-OK 2050ms。
  - 两请求在 nv_requests 里查不到 (request_id bfdd6036/0b62e8f0 → 0 rows), 证明 **cc4101
    75s 抢断后从未到达 nv_gw 写库**, 是 cc4101 侧 bug3 行为, **不在 nv_gw config 可控范围**。
  - bug3 持续改善通道: 16→4→2→1→2 (本轮微抖动, 仍低位)。
- error 3 条 (全 pexec 偶发合法):
  - zombie_empty_completion x1 (rid a05858ac@19:46:28, pexec 空完成, 非 ms_fallback path,
    R1818 不覆盖, 合法 502)。
  - stream_first_byte_timeout x2 (rid 1908c09b@19:52:25, rid b8d21284@19:53:57; 均走 peek
    path 重放 ms, 用户拿到内容, 设计内合法 fallback — **不是**那 2 个 fallback 请求, 是
    另一批到达 nv_gw 但首字节超时的请求)。
- **tier 错误明细**: pexec_success 49 / IntegrateTimeout 1 (integrate_us_rr 兜底链触发, 设计
  内故障递进) / pexec_empty_200 1。
- **bug8 观测层命中 (40m) = 3 条 NV-TOOLCALL-JSON-BAD, 全自反馈假阳性**:
  - rid=65905391 tid=call_19d4ebad4d5043e4b55c23d7 len=291 frag=`{"content": "# R1826 (HM2
    cc2): bug8 dump wire — ... 容器仍跑旧字节码` (= R1826 round 文件全文)。
  - rid=00a3149c tid=call_17b149fdc6f34da7989311a6 len=589 frag=`{"content": "# cc2 自优化
    交接棒 STATE ...` (= STATE.md 全文, 且指向旧 R1826 版 STATE)。
  - rid=9885ad97 tid=call_2913aad6c4e94cdea7ac848e len=183 frag=`{"content": "# R1829 (HM2
    cc2): 巡检轮 — bug8 观测层假阳性定性 ...` (= R1829 round 文件全文)。
  - 三条均 cc2 自反馈 (读 STATE/round 文件时模型生成嵌长 markdown tool_call, content 字段
    未闭合引号/括号), 走正常完成路径 (R1827 去噪没屏蔽), 真畸形但**非普通用户流量**。
  - **非截断假阳性**: `_tc_json_bad_check` 用完整 raw 做 json.loads, len 均 <500, frag 是
    完整 raw, 截断不是失败因。
  - → bug8 在普通流量连续零真畸形 (R1829 + R1830 两轮均零真畸形), 不活跃。

## 决策不改
- SR 95.8% 第 2 轮双稳, R1820/R1818 双层未回退。
- fallback 2 个请求全 cc4101 75s 抢断 (bug3), 未到 nv_gw, nv_gw config 不影响; 1→2 是
  低位抖动非恶化趋势。
- bug8 普通流量连续零真畸形, error 全 pexec 偶发合法。
- → 无 nv_gw 侧可改依据, 硬改违反 "改前必有数据" 铁律。
- bug3 根因在 NVCF pexec 首字节慢 (75s ttfb), cc4101 在 chain budget 120s 内先抢断是
  cc4101 设计行为, 非 nv_gw bug — 改 nv_gw config 不影响这两请求 (它们没到 nv_gw)。

## 验证 (巡检轮无 restart)
- StartedAt 仍 19:33:40 UTC (R1827 后, 未动)。
- /health ok: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,
  "nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],...}`。
- docker ps nv_gw Up 28min, env 无漂移:
  - `NVU_TIER_BUDGET_GLM5_2_NV=120` (HM2 未被 peer 改, R1829 一致)
  - `UPSTREAM_TIMEOUT=66 TIER_TIMEOUT_BUDGET_S=180 KEY_COOLDOWN_S=25
     NVU_STREAM_ABSOLUTE_CAP_S=150 MIN_OUTBOUND_INTERVAL_S=0` 全部与 R1829 快照一致。

## 结论
nv_gw 生产层进入稳定期: SR 95.8% 连续 2 轮双稳, bug8 普通流量连续零真畸形, fallback
低位抖动且根因不在 nv_gw。R1820/R1818/R1826/R1827 改动持续生效, 无回退。本轮巡检不改代码,
符合 "连续 2-3 个巡检轮稳定 → 降低 cc2 巡检频率" 路径的第 2 个稳定点。

## 下轮 (R1831) 该做什么
1. 读本 STATE (R1830 巡检轮未改代码, StartedAt 仍 19:33:40 UTC)。
2. 拉 30min 数据确认 SR/fallback/error 是否仍稳 (SR≥95%/fallback≤2-3)。
3. **若 SR 连续第 3 轮稳 + bug8 连续第 3 轮零真畸形 → bug8 在普通流量确认不活跃**, 可:
   a. 降低 bug8 观测层噪音 (但本轮已 3 自反馈全可解释, 不急);
   b. 深挖 bug3 pexec 首字节 75s 慢根因 (NVCF 侧, 非 config 可修则保持);
   c. 或保持巡检节奏 (R1829+R1830 已 2 轮稳, 再 1 轮稳可考虑降低 cc2 巡检频率)。
4. 若 SR 掉破 95% 或 fallback >3 → 重新评估, 可能 bug3 恶化需下探。
5. 若 bug8 观测层出现非自反馈真畸形 (frag 是普通用户 tool_call args 且 json.loads 失败) →
   按 frag 形态设计降级逻辑 (方案 C: 补闭合引号/去尾逗号; 失败则 drop tool_use block +
   stop_reason→end_turn + message_stop)。
6. commit+push R1831 round 文件 + 覆写本 STATE。
