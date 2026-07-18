# R1798 (HM2 cc2) — 根因定位巡检轮:cap=150 治本失败 + SSE malformed 复发根因重定位

> **性质: 巡检/诊断轮, 不改代码**。R1797 (激活 NVU_STREAM_ABSOLUTE_CAP_S=150) 留两条验证线,
> 本轮按铁律拉数据: ①cap=150 是否生效+SR 回升 ②SSE flushed_content_chars 阈值盲点是否成主犯。
> 结论: **cap 微调彻底没治本 (SR 未回升, fallback 反飙升), 盲点假设被否定 (阈值不是根因),
> 真正根因锁定在 nv_gw-emit vs cc4101-passthrough 的 wire 边界未定, 本轮不贸然改 handlers.py。**

## 数据 (2026-07-18 22:30 拉, db 时间 = 本地 CST - 8h)

### nv_gw 成功率 (status 数值, 非 "success" 字符串)
- **30min 窗**: 200×42 / 502×6 = **87.5% SR** (42/48)
- **2h 窗**: 200×177 / 502×29 = **85.9% SR** (177/206)
- 对比 R1776 (15:46): 30min 88.7%, 2h 88.2% → **SR 没回升, 反略降 1-2pp, 远低于 95% 目标**

### 失败分类 (2h 窗, status>=400, 按 error_type)
| error_type | count | avg_ms | max_ms | first_ts(db) | last_ts(db) |
|---|---|---|---|---|---|
| all_tiers_exhausted | 7 | 50594 | 137952 | 12:42 | 14:26 |
| stream_first_byte_timeout | 7 | 74974 | 82212 | 12:37 | 13:55 |
| stream_no_content_gap | 7 | 136986 | 145039 | 13:36 | 14:26 |
| stream_absolute_cap | 6 | 130665 | 150000 | 12:51 | 14:13 |
| zombie_empty_completion | 2 | 8514 | 10229 | 13:05 | 13:05 |

(db ts +8h = 本地: first 20:37, last 22:26 → 失败持续到当前, 无缓和)

### 30min 失败细分
- stream_no_content_gap ×3 (avg 135s, max 143s)
- all_tiers_exhausted ×2
- stream_absolute_cap ×1 (max_ms=150000)

### cap=150 是否生效 (R1797 验证线①)
- env 已加载: `NVU_STREAM_ABSOLUTE_CAP_S=150` (docker exec nv_gw env 确认)
- nv_proxy.log: `[NV-ANTH-ABS-CAP] ... cap 150s exceeded (elapsed=150s, content_chars=1501/1012, gap_limit=120.0s)` ×2 (21:42, 22:13)
- **结论: cap=150 生效了, 但 stream_absolute_cap 失败仍在 (2h×6, 30min×1), max_ms 正好到 150000**
- **治本失败原因**: 这些请求是上游 NVCF 慢流 (content_chars=1501/1012 = 真在产内容但慢),
  cap 120→150 只是多等 30s, 结果还是超 → **把失败推迟 30s 没救回来, 反拉长延迟**.
  R1779 当时料到 "no_content_gap 疑似未受 TIER_TIMEOUT_BUDGET_S=180 约束", 本轮验证: 慢流病根
  在上游 NVCF, cap 微调治不了.

### fallback 率 (R1776 的负向核心指标) — **恶化**
- 30min fallback = **10 次** (R1776 是 1 次 + 8min 零)
- cc4101 日志: 全是 `[PRIMARY-FAIL] primary timeout status=0 after 75s: header/ttfb timeout`
  + `[PRIMARY-FAIL-SKIP-CIRCUIT] primary timeout after 75s < chain budget 120s, likely cc4101
  pre-empted nv_gw retry, NOT counted toward circuit`
- 含义: 10 次 fallback 全是 cc4101 在 75s 抢断 nv_gw (nv_gw 自己 TIER_TIMEOUT_BUDGET=180 还没到),
  甩给 ms_gw — 但 ms_gw 也 timeout (60s), 最终 `[FALLBACK-FAIL] returning error, CC will retry`
- **fallback 飙升 = 负向核心指标恶化, nv_gw 远没稳到不需要 fallback**

### tier 级 (2h nv_tier_attempts)
- integrate_success 110, pexec_success 62 (健康主流)
- 500_nv_error ×7, pexec_empty_200 ×5 (tier failover 能吸收, 请求级不少仍 200)
- integrate_ConnectionResetError ×1, pexec_SSLEOFError ×1 (连接级偶发, 符合 R1776 判断已降)
- 30min tier: integrate_success 25, pexec_success 12, pexec_empty_200 ×2 (已被吸收)

### nv_gw 自身 breaker
- 30min `NV-ANTH-BREAKER-FAIL` ×4: 全 state=('CLOSED', N, 0), 失败密度不够 NVU_MS_FALLBACK_FAIL_THRESHOLD=5/300s 未 OPEN (正常, R1774 修复 B 设计)
- nv_gw 没误 OPEN, 也没永 CLOSED — breaker 语义本身没坏

### nv_gw /health + 容器
- /health: ok, passthrough, 5 keys, 3 tiers (kimi/dsv4p/glm5_2_nv), default dsv4p_nv
- docker ps: nv_gw Up About an hour (R1797 21:29 up -d 重创建后), ms_gw Up 34h (热备在), cc4101 Up 7h, logs_db Up 45h

## SSE malformed 复发 (R1797 验证线② + 监督者 17:30 盲点)

### 监督者假设被证实一半, 否定一半
- 监督者 (17:30) 观察: cc2.log 15:00-17:30 (2.5h) `Could not parse` + `mid-response` 复发 12 次,
  断言 "R1774 修复 A '2h 零复现' 不成立, 实际约 1 次/12min".
- **本轮验证 (cc2.log 当前 376 行, mtime 22:29)**:
  - `Could not parse` × **23** (含历史, 但本轮新 session 22:08/22:23/22:29 都有新复发)
  - `mid-response` × **7**
  - 复发持续到当前 (22:07/22:08/22:23/22:29 轮边界附近) → **复发非零, 监督者"非零"判断正确**
- **但监督者假设2 (阈值 N>0 太低, 应提到 ≥50c/≥100c) 被否定**:
  cc2.log 复发 chunk 形态 (精确):
  ```
  "event: content_block_delta",
  "data: {\"type\":\"content_block_delta\",\"index\":0,\"delta\":{\"type\":\"text_delta\",\"text\":event: content_block_stop"
  ```
  以及 `{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"了首批"}event: content_block_stop`
  - delta 的 JSON `data:` 帧在 `"text":` 字段值位置被 **`event: content_block_stop` 字符串截断嵌入**
  - 内容字符不全是 <50c: "了首批"=3c, "次错"=2c, "2 小"=2c, "了首批"} 等 — 有的是完整小片段
  - **真问题不是 "flushed_content_chars 阈值太低", 是两个 SSE event 被粘在同一帧且中间 JSON 帧被切**
  - 提阈值到 50/100c **不能**修复帧拼接 bug, 只是改变哪些走 graceful — 帧拼接坏照样坏

### 根因重定位 (本轮新发现, 推翻 R1776 "SSE 2h 零复现")
- **nv_proxy.log grep `content_block_delta` = 0 命中** — nv_gw 自身日志从不记录它 emit 了 malformed Anthropic event
  (它 log 上游 OpenAI chunk + NV-ANTH- 控制事件, 不 log emit 的 Anthropic 字节)
- 这意味着: malformed 字节要么是 (a) nv_gw wfile.write/finish() 拼接坏, 要么是 (b) cc4101 passthrough
  转发时粘包 (cc2 链路 = cc2→cc4101→nv_gw, CC 解析的是 cc4101 转发后字节)
- **本轮证据不足以区分 (a) vs (b)**: 需要下轮 dump 一条复发 req 的 nv_gw 原始 emit 字节序
  (从 cc4101 passthrough 日志或 nv_gw wfile 抓包), 才能决定改 nv_gw finish() 还是查 cc4101
- **关键否定**: 即使 finish() zombie+content>0 路径 (oai_to_anth.py L239-256) 的 _sse_bytes 帧本身完整,
  也不能排除 wfile.write(out_bytes)+flush (handlers.py:1270-1272) 与 finish() emit (L1306-1314) 之间
  的非原子性导致前 delta 帧尾 `}\n\n` 未落盘就拼了下个 event — 但同样可能是 cc4101 粘包

## 为何本轮不改 (铁律: 改前必有数据, 根因未锁定不瞎改)
1. **cap=150 治本失败已用数据证明** — 但本轮的修复方向 (wire 拼接) 根因在 nv_gw-emit vs cc4101-passthrough
   之间未区分清, 贸然改 nv_gw finish() 可能无效 (若根因在 cc4101) 甚至引入新 bug
2. **违反小步快走** — R1779 已开 "诊断巡检不改代码" 先例, 本轮延续: 根因 dump 不够则不动
3. **监督者明确指示** "动 handlers.py 前先 dump 一条复发时刻的 nv_gw 原始 SSE, 看清 chunk 边界再决定"
   — 本轮刚定位到 1192 解析点 + finish() zombie 路径, 但没 dump 到一条具体 req 的 wfile 字节序
4. **fallback 飙升是负向核心指标恶化**, 有动作义务 — 但动作应是 "下轮精确 dump + 改对方向", 不是本轮瞎改
5. cap=150 已激活生效 (env 已加载, ABS-CAP 日志打 150s), 不需要回滚 (回滚到 120 只会更早杀慢流, 更糟)

## 下一轮该做什么 (R1799)
1. **精确 dump SSE malformed 根因 (决定改哪层)**:
   - 从 cc2.log 取一条 22:xx 复发的 req 上下文 (cc2.log 有 3 处 req= 标记, 找对 cc4101 req_id)
   - 查 cc4101 日志该 req 的 passthrough 转发字节 (cc4101 stream.py 是否粘包)
   - 查 nv_gw 是否能加一行 debug log 记录 finish() 前后 wfile 写出的字节序 (诊断性, 非生产逻辑)
   - 区分 (a) nv_gw emit 坏 vs (b) cc4101 passthrough 粘包
2. **若根因在 nv_gw finish()/wfile**: 小步改 handlers.py:1270-1314, 在 feed_chunk 写出后 + finish() emit 前
   加一次强制 flush barrier (确保前 delta 完整 JSON 帧 `}\n\n` 落盘再 emit 终止 events). cp .bak.R1799
3. **若根因在 cc4101 passthrough**: 不在 nv_gw 改 (cc4101 是另一层, 属 cc4101 优化域), 只记录结论
4. **cap=150 保留** (不回滚) — 慢流真病根在上游 NVCF, cap 微调治不了但至少不更糟
5. fallback 飙升的主因 (75s ttfb timeout, NVCF pexec 慢) 是上游, nv_gw 侧无可调点 (TIER_TIMEOUT_BUDGET=180
   已够, 是 cc4101 75s 抢断) — 记录但不在本轮动
6. commit+push R1799 + 覆写 STATE

## 本轮参数快照 (无漂移, R1797 部署后)
```
NVU_STREAM_ABSOLUTE_CAP_S=150  (R1797: 120→150, 已生效)
TIER_TIMEOUT_BUDGET_S=180  UPSTREAM_TIMEOUT=66  MIN_OUTBOUND_INTERVAL_S=0
KEY_COOLDOWN_S=25  TIER_COOLDOWN_S=25  NV_INTEGRATE_KEY_COOLDOWN_S=90
NVU_BIG_INPUT_FAIL_N=1  NVU_BIG_INPUT_COOLDOWN_S=180  NVU_BIG_INPUT_THRESHOLD=250000
NVU_MS_FALLBACK_ENABLED=1  NVU_MS_FALLBACK_FAIL_THRESHOLD=5  (R1774: 15→5)
NVU_MS_FALLBACK_SKIP_S=30  NVU_MS_FALLBACK_MODEL=glm5_2_ms
NVU_BREAKER_WINDOW_S=300  (源码默认)
CC4101_PRIMARY_FAIL_THRESHOLD=3  (R1774: 8→3)
CC4101_PRIMARY_SKIP_S=30  CC4101_BREAKER_WINDOW_S=300
```

铁律: 只改 HM2, 不改 HM1. 不碰 ms_gw (40007 是 restart 热备). 改 .py 必须 restart.
