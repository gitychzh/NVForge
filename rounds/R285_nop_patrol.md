# R285 — NOP 巡检轮 (2026-08-02 16:05 CST)

## 结论: NOP 巡检轮, 0 改动 0 restart

- cc2 (cc4101-primary) 30min 0 req, 不受影响, 0 fallback 0 deadline.
- dsv4p_nv 30min SR=68.1% (32/47), 失败 15 全 `all_tiers_exhausted` (function 级配额).
- **新现象 (非新错误)**: 08:02:05 UTC `other` caller 同秒并发 10 请求, 全 1ms 502
  (nv_gw 在选 key 前 all_tiers_exhausted 拒绝, nv_key_idx/egress_ip 空).
  命中 08:00:14-08:00:31 hermes 429/502 之后的 cooling 尾巴窗口.
  08:05:10 `other` caller 恢复 200 (key_idx=1, 2290ms) → cooling ~3min 后恢复, 配额周期正常.
- 07:45-07:59 连续 ~28×200 (hermes, key2, 单 egress 203.10.96.139 100% SR) — 恢复窗口密度高.
- 错误类型无新增, 全 `all_tiers_exhausted`, 与 R278-R284 一致.

## 数据 (30min, 2026-08-02 07:35-08:05 UTC)

### cc2 (cc4101-primary): 0 req
- 同 R275-R284, session 间歇空闲, 链路空闲健康.

### dsv4p_nv 全 caller: SR=68.1% (32/47)
| caller | status | count | avg_ms | 备注 |
|---|---|---|---|---|
| hermes | 200 | 32 | 10759 | key2, egress 203.10.96.139, 100% SR |
| hermes | 429 | 3 | 2686 | 边界点 07:35/07:40/08:00 |
| hermes | 502 | 2 | 17382 | 07:58 (34762ms) + 08:00 (1ms) |
| other | 200 | 1 | 2290 | 08:05 恢复 |
| other | 502 | 10 | 1 | 08:02:05 同秒并发, cooling 窗口 |

### 08:02:05 突发 10×502 根因
- `other` caller (未识别, 非 cc2 非 hermes) 同秒并发 10 请求.
- 此时全 key 处于 cooling (08:00:14 hermes 429 触发 function 级配额耗尽, 08:00:31 hermes 502).
- nv_gw 选 key 前 all_tiers_exhausted (1ms 瞬拒, nv_key_idx/egress_ip 空, 未打 NVCF).
- **非新错误类型**, 仍是 `all_tiers_exhausted`; **非 cc2 流量**; **自恢复** (08:05 other 200).
- 与 hermes 边界点 429 同源 (function 级配额), 仅并发量集中.

### 恢复证据
- 07:45-07:59 连续 ~28×200 (hermes, key2) — 配额 5min 边界恢复后连续成功.
- 08:05:10 `other` caller 200 (key_idx=1, 2290ms) — cooling 窗口 ~3min 后恢复.
- 单 egress IP 203.10.96.139 35×200 100% SR — IP 健康.

## 根因 (沿用 R278-R284, 无变化)
- dsv4p_nv 5key 全绑同一 NVCF function, 429 配额是 function 级.
- 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- buffer 5key 轮转对 function 级 429 失效 (设计盲区, 非 nv_gw 代码缺陷).
- cc2 流量极低 (本轮 0 req), 命中概率低, 不达介入阈值.

## 健康检查
- `curl /health` → ok, nv_num_keys=5, models=[kimi_nv,dsv4p_nv,glm5_2_nv].
- docker ps: nv_gw/cc4101/logs_db/ms_gw/nv_gw_stable 全 Up.

## 判稳
- NOP 巡检轮. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- 08:02 10×502 是 `other` caller 并发命中 cooling 窗口一次性事件, 非 cc2, 非 nv_gw 缺陷, 自恢复.
- 错误类型无新增, 全 all_tiers_exhausted, 与 R278-R284 一致.
- 十八轮一致 R268-R285.

## 下一步
1. 持续监控 cc2 primary buffer_exhausted/all_tiers_exhausted 是否复发. 现状罕见 (本轮 0 req).
2. 监控 `other` caller 并发 502 是否恶化 (频率/蔓延非 cooling ���口). 现状一次性自恢复.
3. cc2 session 恢复流量后复测 buffer 5key 轮转对边界点 429 抵抗力.

## 参数快照 (nv_gw + cc4101, 同 R284)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150.
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3.
