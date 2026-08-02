# R289 — NOP 巡检轮 (2026-08-02 16:20 CST)

## 基线
- 接 R288. 主仓 main `4d910c2` (R288 round), 本仓 master `3e45ffc` (post288 STATE).
- 注入数据 16:20 CST 30min 窗口, 与 R288 的 16:16 窗口几乎完全重合 (同一 NVCF 配额周期延续, 系统稳态延续).

## 判稳
- **NOP 巡检轮**. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲, DB 实测确认).
- dsv4p_nv 全 caller SR=53.6% (30/56), 失败 27 全 `all_tiers_exhausted`, **无新错误类型**.
- 错误根因与 R278-R288 完全同源: NVCF function 级配额边界点, buffer 5key 轮转对 function 级 429 是已知盲区 (设计盲区非代码缺陷).
- cc2 无流量不受影响, 0 fallback 0 deadline. 0 改动 0 restart.
- **二十二轮一致 R268-R289**.

## 30min 数据 (16:20 注入, DB 实测复核)
| caller | status | count | 备注 |
|---|---|---|---|
| hermes | 200 | 23 | key2, egress 203.10.96.139 |
| hermes | 429 | 5 | 边界点 |
| hermes | 502 | 2 | cooling 尾巴 |
| other | 200 | 21 | glm5_2_nv 20 + dsv4p 1 |
| other | 502 | 20 | 08:02×10 + 08:05×10 同秒并发命中 cooling 窗口, 1ms 瞬拒 |

- nv_tier_attempts 30min 0 条 (无 buffer 流量, 全部 pexec peek 一击即败).
- cc_requests stream_total_deadline 6h 0 条 (DB 实测确认).
- nv_requests status!=200 错误分类: `all_tiers_exhausted × 27` (唯一类型, 无新增).

## 沿用现象 (非新错误, 同 R278-R288)
- 08:02:05 + 08:05:10 `other` caller 两批同秒并发 10×502, 全 1ms all_tiers_exhausted (nv_gw 选 key 前瞬拒, nv_key_idx/egress_ip 空, 未打 NVCF).
- 命中 07:58-08:00 hermes 429/502 触发的 cooling 尾巴窗口 (function 级配额耗尽).
- 08:05 有 1×200 (key1, 2290ms) → cooling 窗口 ~3min 后恢复.
- 仍是 `all_tiers_exhausted` 类型, 非 cc2 流量, 非新错误, 自恢复.
- 07:45-07:59 连续 ~28×200 (hermes key2) 恢复窗口密度高, 配额 5min 边界正常轮转.
- 单 egress IP 203.10.96.139 29×200 100% SR — IP 健康.

## 健康检查
- `curl /health` → ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- docker ps: cc4101/nv_gw (Up 2h), nv_gw_stable (Up 14h), ms_gw/logs_db (Up 3 days) 全 Up.
- cc2 (cc4101-primary) 30min 0 req (DB 实测确认).
- cc_requests stream_total_deadline 6h 0 条 (DB 实测确认).
- buffer/wait/keymanager 日志 30min 空 (无 buffer 流量, cc2 0 req).

## 根因 (沿用 R278-R288 分析, 非本轮新发现)
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function, NVCF 429 配额是 function 级: 配额耗尽时 5 key 同时收 429.
- buffer 5key 轮转设计针对 key/IP 级隔离, 对 function 级 429 失效 (设计盲区非代码缺陷).
- hermes 走 pexec peek path 单 key 探测 429 → 一击即败快速释放; other caller 并发命中 cooling 窗口 → 1ms all_tiers_exhausted 瞬拒.
- cc2 走 buffer 5key 轮转, 流量极低命中概率远低于 hermes, buffer_exhausted 罕见且自恢复.
- **非 nv_gw 代码缺陷, 无需本轮改码**. NVCF function 级配额是上游硬限制.

## 本轮动作
- 0 改动 0 restart. 仅数据采集 + 健康检查 + 文档.

## 下一步
- 继续 NOP 巡检. 关注: (1) cc2 流量恢复后 buffer_exhausted 是否复发; (2) dsv4p_nv function 级配额是否有新边界点; (3) 是否出现新错误类型.
- 若 cc2 流量恢复且 buffer_exhausted 复发高频, 再考虑介入 (如 function 级配额检测/等待策略).

## 参数快照 (沿用 R288, 无变更)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4p_nv, UPSTREAM_TIMEOUT=130
- settings.json: API_TIMEOUT_MS=600000, contextWindow=170000, autoCompactWindow=155000
