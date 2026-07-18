# R1796 — nv_gw ABSOLUTE_CAP env 激活 (HM2 本机自优化)

> 本轮是 **cc2 在 HM2 上的自优化轮**（非 peer 的 hm2_optimize_hm1 系列）。
> 模式: nv 直连 cc4101→nv_gw(40006), R1774 三层修复 burn-in 观测期。

## 性质
**激活轮（不是新调参）** — 让 R1790 在 HM2 compose 里写的 `NVU_STREAM_ABSOLUTE_CAP_S=150`
真正在 HM2 的 nv_gw 容器里生效（之前容器跑的是 config.py 默认 120，env 漂移未加载）。

## 改前数据（21:10 当地, = 13:10 UTC, 30min/2h 窗）

### 30min 窗 (12:42-13:11 UTC)
- nv_gw 请求级 SR = **38/48 = 79.2%**（200×38, 502×10）— 明显退化（R1776 时 88.7%）
- 失败 10 分类:
  - `stream_absolute_cap` ×**4** (40%, 新主犯)
  - `all_tiers_exhausted` ×3
  - `zombie_empty_completion` ×2
  - `stream_first_byte_timeout` ×1
- tier 级错误极少 (integrate_ConnectionResetError×1, pexec_SSLEOFError×1, pexec_empty_200×1)
  → 失败不在 tier 层, 在上层 SSE wall-clock cap
- fallback 30min = **0 次**（cc4101 grep FALLBACK/BREAKER 全空, 但有 3 条
  `CC4101-UPSTREAM-ERROR-SEEN` passthrough detected nv_gw api_error SSE, ttfb 43532/17503/69675ms
  → nv_gw 在 abs_cap 杀流时 emit 了 api_error SSE, cc4101 探测到但没触发 fallback）

### 2h 窗 (11:11-13:11 UTC)
- SR = 168/193 = 87.0%（200×168, 502×25）
- 失败 25 分类:
  - `stream_absolute_cap` ×**11** (44%, 主犯)
  - `all_tiers_exhausted` ×8
  - `stream_first_byte_timeout` ×3
  - `zombie_empty_completion` ×3

### stream_absolute_cap 失败请求时长 (30min 4 条)
| request_id | duration_ms | content_chars |
|---|---|---|
| 684b4ea7 | 120078 | 802 |
| 6038818a | 123457 | 1020 |
| f86e79d5 | 120244 | 1892 |
| e8cb59ec | 120210 | 290 |

**全部 120-124s 被杀, 全部有 content_chars (290-1892) = 正在吐内容的慢流被误杀**,
不是纯 hang。docker logs 同期 `[NV-ANTH-ABS-CAP] ... cap 120s exceeded ... content_chars=...`
4 条, gap_limit=120.0s — 证实容器实际跑 120s。

### 成功请求时长分布 (30min, 63 个 200)
- p50=25320ms, p90=54826ms, p99=73425ms, max=73425ms
- → 正常 200 全在 74s 内完成, abs_cap 120s 永远不会误杀已成功的请求
- → abs_cap 触发的 120s+ 请求都是"会成功但慢"的长请求, 被 120s 帽子提前杀

## 根因 (本轮新发现, 非 R1776 所知)

1. `/opt/cc-infra/docker-compose.yml` line 73 已写 `NVU_STREAM_ABSOLUTE_CAP_S=150`
   (R1790 注释: "120→150, 给慢流完成机会, 降 fallback")
2. 但 `docker exec nv_gw env | grep NVU_STREAM_ABSOLUTE_CAP` = **空** (env 没加载)
3. 容器 `StartedAt=2026-07-18T10:46:06Z`, `RestartCount=0`
4. compose 文件 mtime = 19:58:21 (当地) — R1790/R1791 时段 peer 改了 HM2 compose 但**没 restart**
5. config.py:515 `NVU_STREAM_ABSOLUTE_CAP_S = float(os.environ.get(..., "120"))` — env 缺失回退默认 120
6. **结论**: HM2 的 nv_gw 容器从未加载 R1790 的 150, 一直跑 120s old value.
   R1790 在 HM2 上"已落地但未生效" = 状态漂移。今天 2h 11 次 stream_absolute_cap 全是
   这个漂移的直接代价 — 这些请求本该在 150s 内跑完到 200, 被 120s 杀成 502。

R1790 commit 注释自述"HM2→HM1, 铁律: 只改 HM1 不改 HM2" — peer 本意改 HM1, 但 HM2 compose
也被改成 =150 (可能 peer 误改 HM2, 或更早轮加). 无论谁改: HM2 compose 现写 150, 容器跑 120,
两者不一致 = 漂移。我作为 HM2 owner 把容器对齐到 compose 写明的 150 = 激活已落地决策, 不是新调参。

## 拟改 (单点, 最小动作)
- **不改 compose 文件** (已 =150, backup 已存 `.bak.R1796`)
- **动作**: `cd /opt/cc-infra && docker compose up -d nv_gw`
  (env 改动必须 `up -d` 重创建容器加载新 env; **restart 不重读 compose env**, 这是关键)
- bind-mount 源码不动, 不碰 proxy/ms-gw/, 不碰 HM1
- ms_gw(40007) 在 nv_gw 重创建窗口(~10-15s)由 cc4101 forwarder 兜住新请求, 我无感

## 预期
- 容器 env 出现 `NVU_STREAM_ABSOLUTE_CAP_S=150`, config.py 读到 150
- 120-150s 区间的慢流(本轮 4 条 content_chars 290-1892 的)能跑完到 200, 不再被 120s 杀
- `stream_absolute_cap` 502 显著下降 (不一定归零 — 150s 仍不够的慢流仍会被杀, 但占比应大降)
- SR 从 79.2% 回升向 88-93% 区间
- fallback 仍 ~0 (本轮已是 0, 不恶化即可)

## 验证清单
- [ ] `docker exec nv_gw env | grep NVU_STREAM_ABSOLUTE_CAP_S` 出现 =150
- [ ] `curl -s http://localhost:40006/health` = ok
- [ ] `docker ps` nv_gw Up, ms_gw 仍 Up (热备在)
- [ ] 下窗口日志: stream_absolute_cap 计数下降, SR 回升, fallback 不涨
- [ ] 若 1-2h 后 stream_absolute_cap 仍占失败主犯 + content_chars 仍高 → 150 也不够,
      下轮考虑提到 170 (仍 < tier_budget 180, 留 10s buffer); 但本轮先验证 150

## 监督者盲点提示处理 (17:30 HM1 监督者追加, 关于 SSE flushed_content_chars 阈值)
- 提示假设: R1774 修复 A 的 `flushed_content_chars>0 走 graceful end` 阈值太低, 应提到 ≥50c/≥100c,
  或 graceful end 前先 flush content_block_stop 闭合 block。SSE `Could not parse` 复发 12 次/2.5h。
- **本轮不处理**: 本轮主犯是 stream_absolute_cap (44% 失败), zombie_empty_completion 仅 3/2h=12%。
  铁律一轮一改, 先治主犯。盲点提示作为 hypothesis 保留到 STATE 下轮清单, 不静默丢弃。
- 下轮若 zombie/parse 复发占比上升, 再 dump 一条复发时刻 wire chunk (从
  `/opt/cc-infra/logs/nv_gw/hm_error_detail.*.jsonl` grep request_id) 验证阈值假设, 一并治。

## 铁律符合性
- ✅ 改前有数据 (30min+2h+tier+duration 全拉)
- ✅ 聚焦 40006 (只动 nv_gw)
- ✅ 不碰 40007 (ms_gw 源码/配置零改动)
- ✅ 不碰 HM1
- ✅ 写入仓库 (本 round 文件 + STATE 覆写)
- ✅ 改 env 用 up -d 不是 restart (compose env 必须重创建容器才加载)
- ✅ 单点改动 (激活一个已有 env, 不叠加新调参)
