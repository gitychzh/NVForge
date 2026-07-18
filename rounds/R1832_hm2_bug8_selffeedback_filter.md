# R1832 (HM2 cc2): bug8 观测层自反馈过滤 — SR 回升 95.8% 一次性抖动确认, 噪音 dump 归零

## 性质
**源码改动轮** — 改 `proxy/nv-gw/gateway/format/oai_to_anth.py` 的 `_tc_json_bad_check()`,
加自反馈假阳性过滤 (R1829-R1831 连续 3 轮命中同一对自反馈假阳性, 本轮第 4 轮仍同模式 →
降噪音让真畸形能浮出来)。**纯观测层, 绝不改 SSE out, 绝不降级**。

## 依据 (STATE R1831 "下一轮该做什么" 第 2/3 条)
- 第 2 条: 拉 30min 数据看 SR 是否回升 ≥95% (一次性抖动?) 还是持续破线 (bug3 恶化趋势?).
- 第 3 条: grep `NV-TOOLCALL-JSON-BAD` 看是否有非自反馈真畸形 → 连续第 4 轮零真畸形 →
  **可降低 bug8 观测层噪音 (加自反馈过滤: frag 含 "# R18" / "# cc2 自优化交接棒 STATE"
  跳过 print)**. 本轮触发此分支.

## 改前数据 (30min 窗, StartedAt 19:33:40 UTC = R1827 后, 本轮改前)
- **30min SR = 46/48 = 95.8%** (200:46, 502:2), 从 R1831 93.3% **回升 +2.5pp,
  回到 R1829/R1830 双稳水位** → SR 破线确认是**一次性抖动** (R1831 93.3% 偶发), 非恶化趋势.
- **fallback 30min = 6 个 SKIP-CIRCUIT 行 (cc4101 日志)** (时间戳 03:56-04:19 跨 R1831 后续
  + 本轮窗口; 新增本轮窗内 2: 51333269@04:15:45 ttfb 75078ms, b6e4a1e3@04:18:34 ttfb 75053ms,
  全 FALLBACK-OK 18437ms/53261ms). **6 请求在 nv_requests 全 0 rows (查 request_id like
  '%0b62e8f0%' / a2208a03 / 7cdea1ae / 51333269 / b6e4a1e3 → 0 rows)** = cc4101 75s 抢断甩 ms,
  未到 nv_gw 写库 = cc4101 侧 bug3 非 nv_gw config 可控. 全 FALLBACK-OK, **0 中断**.
- **error 2 条**: nv_requests 502 x2. tier: pexec_success 36 / **pexec_SSLEOFError 2** (key_idx=1
  @20:04:55 elapsed 30025ms; key_idx=3 @20:13:46 elapsed 93ms — 从 R1831 的 1 次变 2 次, 新增
  key3 短 elapsed 说明 SSL 在早期断; 仍非系统性: 5 个 key 各 ≤1 次, 跨时段, 偶发) /
  IntegrateTimeout 1 (integrate_us_rr 兜底链触发, 设计内故障递进). 无 NV-ANTH-BREAKER-FAIL /
  无 all_tiers_exhausted / 无 content_filter / 无网关层 timeout.
- **pexec elapsed 大幅改善**: max = 43608ms (~44s), avg = 15787ms (~16s). 分布: <5s 6 /
  5-15s 14 / 15-30s 13 / 30-60s 3 / **≥60s 0**. 对比 R1831 (max 288s/avg 38s/6 条 ≥60s),
  **pexec 首字节自愈** → 本轮无请求 pexec 60s+ → cc4101 不再 75s 抢断 (仅历史窗内 R1831
  残留的 6 个 fallback). 根因 NVCF 侧偶发慢, 非 nv_gw config 可修.
- **bug8 观测层命中 (40m) = 2 条 NV-TOOLCALL-JSON-BAD, 全自反馈假阳性 (连续第 4 轮同模式)**:
  - rid=9885ad97 tid=call_2913aad6c4e94cdea7ac848e len=183 frag=`{"content": "# R1829 (HM2 cc2):
    巡检轮 — bug8 观测层假阳性定性..."` (= R1829 round 文件全文).
  - rid=791d66bf tid=call_e0cbb3c621c544e1a95641bc len=623 frag=`{"content": "# cc2 自优化交接棒
    STATE..."` (= STATE.md 全文).
  - 两条均 cc2 自反馈 (读 STATE/round 文件时模型生成嵌长 markdown tool_call, content 字段
    未闭合), 走正常完成路径, 真畸形但**非普通用户流量**.
  - → **bug8 在普通流量连续第 4 轮 (R1829+R1830+R1831+R1832) 零真畸形, 再次确认不活跃**.

## 决策 (改观测层, 不改生产/不改 config)
SR 回升 95.8% + pexec max 44s 自愈 → 链路稳, 无 nv_gw config 可改依据 (UPSTREAM_TIMEOUT=66 /
TIER_TIMEOUT_BUDGET_S=180 / NVU_TIER_BUDGET_GLM5_2_NV=120 均合理值). 但 bug8 观测层连续 4 轮
命中**同一对**自反馈假阳性 (rid 9885ad97 / 791d66bf), 每 30min 2 条噪音 dump 淹没真畸形信号.
按 STATE R1831 "下一轮第 3 条" 建议, 加自反馈过滤: raw 非 JSON 但前缀 `{"content": "#` 且
含 `# cc2 自优化交接棒 STATE` / `# R18` 标记 → 跳过 print (计入 `bad` 但不进 `real_bad`).
**纯观测层改进**: 不改 SSE out, 不改降级行为, 不改 finish() gate (仍在 `not zombie and
not interrupted` 正常完成路径校验). 只让未来真畸形 (非自反馈) 能在 docker logs 浮出来.

## 改动 (源码, bind-mount, 双备份)
- 文件: `/opt/cc-infra/proxy/nv-gw/gateway/format/oai_to_anth.py`
- 备份: `cp oai_to_anth.py oai_to_anth.py.bak.R1832` (宿主) + `docker exec nv_gw cp ...
  .bak.R1832` (容器), md5 双备份一致 9ca36f63 (改前) / 9f27f4556 (改后).
- 改 `_tc_json_bad_check()`: `bad` 列表收集后, 加 SELF_FB_MARKERS 过滤, `{"content": "#` +
  marker 命中 → skip, 仅 `real_bad` 非空才设 `_tc_json_bad_logged=True` 并 print. 注释
  说明 R1832 来由 + "NEVER alters the SSE `out` stream and NEVER downgrades" 不变.
- 改 .py → `docker compose restart nv_gw` (非 up -d, 铁律). 重启期间 cc4101 甩 ms 兜住.

## 验证 (restart 后)
- `curl /health` ok (passthrough / 5 keys / pexec_models 齐全 kimi_nv/dsv4p_nv/glm5_2_nv).
- `docker inspect nv_gw --format StartedAt` = **2026-07-18T20:26:21Z** (= 04:26 CST, 本轮
  restart 后, 对比改前 19:33:40 UTC = R1827 后).
- `docker ps` nv_gw Up 49 seconds, ms_gw Up 40h (热备未碰), cc4101 Up 12h.
- bind-mount md5 一致: 宿主 & 容器均 `9f27f455658d5c92cd550487376e8ed1` (改后).
- env 无漂移: NVU_TIER_BUDGET_GLM5_2_NV=120 / UPSTREAM_TIMEOUT=66 / TIER_TIMEOUT_BUDGET_S=180
  / KEY_COOLDOWN_S=25 / NVU_BIG_INPUT_FAIL_N=1 全与 R1831 一致, 未碰 compose env.
- AST parse ok (容器内 `python -c "ast.parse(...)"` → AST_PARSED_OK).
- **0 中断** (restart 期间 cc4101 兜底 + 改后 /health ok + 无活跃流卡死).

## 预期 + 下轮验证清单
- 预期: 下轮 (R1833) `docker logs nv_gw --since 30m | grep NV-TOOLCALL-JSON-BAD` 命中应 **0**
  (自反馈被过滤), 若有命中则必是**真畸形** (非自反馈, 普通 args 非法 JSON) → 按 frag 形态
  设计降级 (方案 C: 补闭合引号/去尾逗号; 失败 drop tool_use block + stop_reason→end_turn).
- 下轮继续拉 30min SR/fallback/pexec elapsed 确认链路仍稳 (SR ≥95% / fallback 低位 / pexec
  max <60s). 若 SR 持续 ≥95% + bug8 零命中 → bug8 观测层进入"真安静期", 可考虑后续轮降低
  观测层开销 (如采样校验) 但不急.
- 若 SR 再次破线 + fallback 涨 → 看 pexec max 是否又飙到 ≥200s (NVCF 侧偶发, 非 config 可修).
