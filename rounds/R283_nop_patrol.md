# R283 — NOP 巡检轮 (2026-08-02 15:58 CST)

## 数据 (30min 实时 DB + 链路分析注入 ~15:57 CST)

### cc2 (cc4101-primary) 30min 0 req
- 同 R275-R282, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- nv_tier_attempts 30min 0 条; cc_requests stream_total_deadline 6h 0 条.

### dsv4p_nv 30min SR=92.0% (23/25), 失败全 hermes 边界点
| min (UTC) | caller | status | count | dur_ms |
|---|---|---|---|---|
| 07:30 | hermes | 200 | 3 | 10691 avg |
| 07:35 | hermes | 429 | 1 | 2003 |
| 07:40 | hermes | 429 | 1 | 2003 |
| 07:45 | hermes | 200 | 2 | — |
| 07:46 | hermes | 200 | 1 | — |
| 07:50 | hermes | 200 | 3 | — |
| 07:51 | hermes | 200 | 4 | — |
| 07:55 | hermes | 200 | 2 | — |
| 07:56 | hermes | 200 | 6 | — |
| 07:57 | hermes | 200 | 2 | — |

- 5min 等间隔, 全 %5==0 边界点, duration 2003ms 快速失败 (pexec peek path 非 buffer).
- 全 `all_tiers_exhausted` (5key 全 429, function 级配额).
- 07:30 三连 200 + 07:45-07:57 连续 13×200: 配额 5min 边界恢复后 hermes 连续抢到成功,
  恢复窗口密度 (13 个 200) 高于 R282 (10 个), 印证配额周期正常轮转非恶化.
- 200 finish_reason: tool_calls 20, stop 3 — 无 zombie.
- 200 延迟: avg 11043ms / max 20658 / min 4609 / ttfb 10649 — 健康.
- per-key: key2 23×200 (100% SR), 2×429 来自未映射 key.
- per-egress: 203.10.96.139 23×200 100% SR — 单 IP 健康.

### 健康检查
- `curl /health` → ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- docker ps: nv_gw/cc4101/logs_db/ms_gw/nv_gw_stable 全 Up.
- buffer/wait/keymanager 日志 30min 空 (无 buffer 流量, cc2 0 req).

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- dsv4p_nv 失败全在 hermes caller 打 NVCF 5min 配额边界, 非 nv_gw 代码缺陷.
- 边界点 (07:35/07:40) 落在 R279-R282 稳态区间 (07:15-07:40) 内, 配额周期稳态非恶化.
- 07:30-07:57 恢复窗口 13 个 200 (R282 10 个) — 恢复密度提升非恶化, 印证配额周期正常轮转.
- SR 92.0% 高于 R282 81.3%, 恢复窗口更密, 非恶化.

## 根因 (沿用 R278-R282, 设计盲区非代码缺陷)
- dsv4p_nv 5key 全绑同一 NVCF function `12acbc62`, NVCF 429 配额是 function 级 (非 key 级).
- buffer 5key 轮转对 key/IP 级 429 有效 (R268-R282 验证), 对 function 级 429 是已知盲区.
- hermes pexec peek path 一击即败 ~2s 快速释放, cc2 buffer 5key 轮转但流量极低命中边界点概率低.
- R278 06:28-06:32 一次性 5×502 buffer_exhausted 已自恢复 (9h+ 全 200), 不达介入阈值.
- **非 nv_gw 代码缺陷, 无需本轮改码**.

## 改动
- 0 改动 0 restart. 十六轮一致 R268-R283.

## 下一步
- 继续 NOP 巡检. 监控 cc2 流量恢复后 dsv4p_nv SR 是否维持 99%+ (buffer 5key 轮转对 function 级 429 盲区已知).
- 若 cc2 流量恢复且 buffer_exhausted 复发频率上升 (≥2/h), 再评估是否引入 function 级 429 短惩罚 (整 function cooldown 而非单 key), 暂不动.

## 参数快照 (R-nvonly, 未变)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_TOTAL_DEADLINE_S=450,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- cc4101: FALLBACK_UPSTREAM_URL=ms_gw:40007, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130
