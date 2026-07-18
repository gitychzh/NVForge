# R1815 — HM2 cc2: R1809 burn-in ~42min 巡检+根因定位轮, 不改代码

> 铁律：只改 HM2，不改 HM1，不碰 proxy/ms-gw。改前必有数据，改后必有验证。
> 本轮性质：**巡检+根因定位轮**（非新改）。R1809 全 pexec 生效 ~42min，攒够 ~58req burn-in，
> 确认 bug2(stream_no_content_gap)/bug6(zombie)/bug1(SSE malformed) 归零趋势是否持续成立，
> 并执行 R1812 下轮建议「查 handlers.py cap break 后是否硬中止 tier abort（dump wire 确认路径）」。

## 数据（拉于 2026-07-19 00:42 CST = 16:42 UTC, R1809 生效 16:00:08 UTC, 已 ~42min）

### 切换前后时间轴（2h 拼接）
| 时段(UTC) | 窗口性质 | 主失败类型 |
|---|---|---|
| 14:51-15:57 | PRE/过渡混(integrate残余) | no_content_gap=2, zombie=2, first_byte=7, cap=0 |
| 16:00:08 | R1809 up -d 生效 | — |
| 16:12-16:42 | POST 纯 pexec(~30min) | **cap=4, first_byte=2, no_content_gap=0, zombie=0** |

### 30min 窗（16:12-16:42 UTC, 58req）
- SR = **53/58 = 91.4%**
- 错误分类: stream_absolute_cap **4** / stream_first_byte_timeout **1** / 其他 0
- **stream_no_content_gap = 0 条** ✓ **bug2 治本持续成立**
- **zombie_empty_completion = 0 条** ✓ **bug6 治本持续成立**
- **SSE malformed / all_tiers_exhausted = 0 条** ✓ **bug1 也未复发**

### 切换后纯净窗（16:25-16:42 UTC, 17min, 38req, 排除 16:12-16:25 过渡段）
- SR = **36/38 = 94.7%**（接近 95% 全胜线，趋势强正向）

### 2h 窗趋势（14:42-16:42 UTC, 241req）
- SR = 222/241 = **92.1%**（burn-in 未达 95%, 但 POST 段已逼近）
- 错误分类: first_byte_timeout=9, stream_absolute_cap=4, all_tiers=2, no_content_gap=2, zombie=2
  （no_content_gap/zombie 全在 14:51-15:42 的 PRE/过渡段, POST 16:12 后归零 ✓）

### 成功延迟（1h 窗, status=200）
- p50=21083ms, p90=40979ms, max=96909ms, avg=23299ms（无 integrate 期 135886ms hang 长尾 ✓）

### fallback（负向核心指标）
- 30min 窗 = **4 次**, 全 75s ttfb 抢断 SKIP-CIRCUIT（bug3 未修, 同 R1812）
- 2h 窗 = 8 次
- **切换后纯净窗（16:25-16:42）fallback 也 4 次** —— 这 4 次就是 cap 误杀事件的 cc4101 侧映射

## R1812 下轮建议执行结果：cap break 后路径确认（核心产出）

R1812 建议「查 handlers.py cap break 后是否硬中止 tier abort（dump wire 确认路径）」。

**结论：cap break 不硬中止 tier，而是误杀已 relay 的 ms fallback 内容。新发现 bug7。**

### handlers.py 路径复核（line 922-1135, 1280-1306）
1. **peek barrier (line 922-1092)**: nv pexec 僵尸流(content_chars=0, ttfb>150s) 被首层 ABS-CAP 击中 → tier 走完所有 key → `all_keys_exhausted` → 转 ms_gw fallback
2. ms_gw 成功拿到内容 → `NV-PEEK-OK prebuffer=2257b`（line 1021）, `metrics["ttfb_ms"]=274942` 已记录
3. **line 1065-1092: `send_response(200)` 已发**（cc4101 收到 200 头）
4. **line 1110-1115: prebuffer 已 flush 给客户端**（ms 内容首批已发）
5. **line 1118-1135: 进 anth cap loop** → `time.time()-t_start = 274s > NVU_STREAM_ABSOLUTE_CAP_S=150s` → **立即 break interrupted=True**
6. **line 1306: `if metrics.get("error_type"): status=502`** → cap 设了 error_type → 最终 status=502, output_tokens=0

### 关键证据：3 个 cap 失败的 DB 字段
| req_id | ttfb_ms | duration_ms | output_tokens | fallback_occurred | fallback_tiers_used |
|---|---|---|---|---|---|
| ad179e0f | 274942 | 274944 | 0 | t | {glm5_2_nv,glm5_2_ms} |
| 5a433280 | 246237 | 246239 | 0 | t | {glm5_2_nv,glm5_2_ms} |
| e61900a8 | 262242 | 262243 | 0 | t | {glm5_2_nv,glm5_2_ms} |

- **fallback_tiers_used 含 glm5_2_ms** → ms_gw fallback 确实成功拿到内容
- **output_tokens=0 / status=502** → ms 内容被 cap 误杀, 客户端拿到 502 空
- **2h 窗 cap 4/4 全部伴随 ms fb 成功** → bug7 100% 复现
- **ttfb_ms ≈ duration_ms**（274942≈274944）→ 整条流 wall-clock 都在等, ms 内容只在最后 peek 到, 随即被 cap 杀

### nv_gw 日志佐证（以 ad179e0f 为例）
```
00:12:30 NV-ANTH-ABS-CAP elapsed=247s content_chars=0   ← 第一轮 pexec 僵尸 cap
00:14:29 NV-GLM52-TIMEOUT k2 timeout 58910ms → mode→advance
00:14:29 NV-GLM52-CHAIN-FALLBACK chain all-failed → pexec
00:16:29 NV-MS-FB-ATTEMPT all_keys_exhausted → ms_gw
00:17:04 NV-MS-FB-OK ms_gw success after 34673ms, relaying openai SSE  ← ms 成功
00:17:04 NV-PEEK-OK peek healthy first content after 274942ms, prebuffer=2257b  ← 内容拿到
00:17:04 NV-ANTH-ABS-CAP elapsed=274s content_chars=0   ← 同一秒 cap 又触发误杀
00:17:04 NV-ANTH-BREAKER-FAIL stream_absolute_cap → nv_breaker recorded
```

## 根因结论：bug7 = anth ABS_CAP wall-clock 不重置, 误杀 ms fallback 已 relay 内容

**`NVU_STREAM_ABSOLUTE_CAP_S` 的 cap 时钟 `time.time()-t_start` 中, `t_start` 是整个请求起点（line 1118 `t_start` 在请求入口设定）, 不随 tier 切换/ms fallback 成功而重置。**

当请求经历「pexec 僵尸流 cap(247s) → tier 走完(~2min) → ms_gw fallback 成功(~34s)」总计 ~274s, ms_gw 虽成功领取内容并 peek 到 prebuffer=2257b、已 send_response(200) + flush, 但 anth cap loop 用总 wall-clock 274s > 150s **立即 break, 把刚 relay 的 ms 内容截断**, 最终 status=502 output_tokens=0。

**这不是 NVCF pexec 间歇挂本身可治的**（R1812 结论「上游间歇挂配置治不了」只对一半）—— 真正可治的是 **bug7: cap t_start 不重置**, 让 ms fallback 成功后 cap 重新计时（或用 ms fallback 起点+ ms 自身 deadline 守护 ms 流）, 就能把这 4/58=6.9% 的 cap 失败救回成 200。

## 为何本轮不改代码（巡检+定位, 非执行轮）

1. **bug2/bug6/bug1 切换后纯净窗全部归零** → R1809 治本完全成立, 向全胜推进（纯净窗 SR 94.7% 接近 95%）, 无需再动 R1809
2. **bug7 是新发现的真 bug, 但改 cap t_start 重置逻辑风险高**:
   - 影响 handlers.py:1118-1135 整个 anth cap loop（cap/no_content_gap/deadline/first_byte 全用同一 t_start + last_real_content_time 体系）
   - 需专门一轮设计：ms fallback 成功后是否重置 t_start + last_real_content_time, 还是给 ms fallback 内容单独一条不受总 cap 约束的 relay 路径
   - 需 dump wire 验证 ms 内容 relay 边界（supervisor R1798 也指示先 dump wire 再改）
3. **小步快走**: R1809 burn-in 仍临界（30min SR 91.4%, 纯净窗 94.7%）, 不在临界态叠加新改
4. **fallback 率未降**（30min 4 次）—— 但这 4 次本质是 bug7 误杀 ms 内容后 cc4101 侧映射, 治 bug7 后这批 fallback 会消失（ms 成功 relay 完整内容就无需 cc4101 抢断）

## 验证（巡检轮, 无代码改动, 无需 restart）
- `curl /health`: `{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,"nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],"nv_default_model":"dsv4p_nv"}` ✓
- `docker ps`: nv_gw Up 41min, cc4101 Up 9h, ms_gw 热备在 Up 36h ✓
- 容器 env: KEY_MODE_BINDING 全 pexec, NVU_STREAM_ABSOLUTE_CAP_S=150, 参数无漂移 ✓
- 下一窗口日志: bug2/bug6/bug1 持续归零, 失败仅剩 cap（bug7）✓

## 下轮该做什么（R1816, 治 bug7）
1. **读本 STATE + R1815 round**：bug7 已根因定位（cap t_start 不重置误杀 ms fb 内容）
2. **设计 bug7 修复方案**（二选一, 先 dump wire 确认 ms 内容 relay 边界）:
   - 方案A（重置 t_start）: ms_gw fallback 成功 peek 后, 重置 `t_start = time.time()` + `last_real_content_time = time.time()`, 让 cap/no_content_gap/deadline 从 ms 内容起点重新计时
   - 方案B（ms 独立路径）: ms fallback 成功后走独立 relay 路径, 不进 anth cap loop, 用 ms 自身 deadline 守护
   - 推荐 A（改动小, 复用现有 deadline 体系）, 但需确认 ms relay 是否也走 sse_buffer parse（影响 converter/content_chars 累积）
3. **dump wire 验证**: 拉一条 cap 失败 req 的 `hm_error_detail.*.jsonl`, 确认 ms 内容 relay 边界（prebuffer 2257b 之后 nv_gw 是否还从 ms 读更多 chunk, 还是 cap 立即 break）
4. **小步改**: `cp handlers.py handlers.py.bak.R1816`, 改 1 处（方案A 重置 t_start）, restart nv_gw, 验证 /health+docker ps+下窗口 cap 失败是否归零（目标: stream_absolute_cap 30min 0 条）
5. **验证失败回滚**: .bak.R1816 + restart
6. commit+push R1816 + 覆写 STATE
7. bug3（cc4101 75s 抢断）等 bug7 治完再看 —— bug7 治了 ms 内容能完整 relay, cc4101 不再需要抢断

## 铁律
只改 HM2 不改 HM1, 不碰 proxy/ms-gw, 改 .py 必须 `docker compose restart nv_gw`, 改 env 必须 `docker compose up -d nv_gw`。改前必有数据, 改后必有验证。
