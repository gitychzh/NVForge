# R287 — NOP 巡检轮 (2026-08-02 16:12 CST)

## 基线
- 接 R286. 主仓 main `8e41f38` (R286 round), 本仓 master `d0b5343` (post286 STATE).
- 注入数据 16:12 CST 30min 窗口, 与 R286 的 16:08 窗口几乎完全重合 (同一 NVCF 配额周期延续, 系统稳态延续).

## 判稳
- **NOP 巡检轮**. cc2 (cc4101-primary) 30min 0 req (session 间歇空闲).
- dsv4p_nv 全 caller SR=56.9% (33/58), 失败 25 全 `all_tiers_exhausted`, **无新错误类型**.
- 错误根因与 R278-R286 完全同源: NVCF function 级配额边界点, buffer 5key 轮转对 function 级 429 ���已知盲区 (设计盲区非代码缺陷).
- cc2 无流量不受影响, 0 fallback 0 deadline. 0 改动 0 restart.
- **二十轮一致 R268-R287**.

## 30min 数据 (16:12 注入)
| caller | model | status | count | 备注 |
|---|---|---|---|---|
| hermes | dsv4p_nv | 200 | 32 | key2, egress 203.10.96.139, avg 10759ms |
| hermes | dsv4p_nv | 429 | 3 | 边界点 07:40/08:00 |
| hermes | dsv4p_nv | 502 | 2 | 07:58 + 08:00 cooling 尾巴 |
| other | dsv4p_nv | 200 | 1 | 08:05 恢复 (key1, 2290ms) |
| other | dsv4p_nv | 502 | 20 | 08:02×10 + 08:05×10 同秒并发命中 cooling 窗口, 1ms 瞬拒 |
| other | glm5_2_nv | 200 | 20 | 100% SR |

## 沿用现象 (非新错误, 同 R286)
- 08:02:05 + 08:05:10 `other` caller 两批同秒并发 10×502, 全 1ms all_tiers_exhausted (nv_gw 选 key 前瞬拒, nv_key_idx/egress_ip 空, 未打 NVCF).
- 命中 07:58-08:00 hermes 429/502 触发的 cooling 尾巴窗口 (function 级配额耗尽).
- 08:05 有 1×200 (key1, 2290ms) → cooling 窗口 ~3min 后恢复.
- 仍是 `all_tiers_exhausted` 类型, 非 cc2 流量, 非新错误, 自恢复.
- 07:45-07:59 连续 ~28×200 (hermes key2) 恢复窗口密度高, 配额 5min 边界正常轮转.
- 单 egress IP 203.10.96.139 32×200 100% SR — IP 健康.

## 健康检查
- `curl /health` → ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv], nv_default_model=glm5_2_nv.
- docker ps: cc4101/nv_gw (Up 2h), nv_gw_stable (Up 14h), ms_gw/logs_db (Up 3d) 全 Up.
- buffer/wait/keymanager 日志 30min 空 (无 buffer 流量, cc2 0 req).

## 根因 (沿用 R278-R286 分析, 设计盲区非代码缺陷)
- dsv4p_nv 5key (k0-k4) 全绑同一 NVCF function. NVCF 429 配额是 function 级: 配额耗尽时 5 key 同时 429.
- buffer 5key 轮转设计假设 "单 key 429 切下一 key 绕过", 对 function 级 429 失效: 5 key 全 429 → all_tiers_exhausted.
- hermes 走 pexec peek path: 单 key 探测 429 → 一击即败 (~2-8s), 快速释放, 不消耗 buffer.
- other caller 并发命中 cooling 窗口 → 1ms all_tiers_exhausted 瞬拒.
- cc2 走 buffer 5key 轮转但流量极低, buffer_exhausted 罕见且自恢复.
- **非 nv_gw 代码缺陷, 无需本轮改码**. NVCF function 级配额是上游硬限制.

## 下一步
1. 持续监控 cc2 primary buffer_exhausted/all_tiers_exhausted 是否复发 (>5/h 或蔓延至非边界点才需介入). 现状罕见.
2. 监控 `other` caller 并发 502 是否恶化 (频率/蔓延非 cooling 窗口). 现状两批自恢复.
3. cc2 session 恢复流量后, 复测 buffer 5key 轮转对边界点 429 的抵抗力.
4. 待后续 (非本轮): 若复发频繁, 考察在 nv_gw 侧对 all_tiers_exhausted/429-边界点引入 WaitQueue event-driven 短等待 (跨 5min 边界恢复), 而非 buffer 死轮转耗 165s.

## 参数���照 (nv_gw + cc4101, 同 R286, 0 改动)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NV_INTEGRATE_KEY_COOLDOWN_S=90, TIER_TIMEOUT_BUDGET_S=180,
  NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0.
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4p_nv, PRIMARY_UPSTREAM_URL=nv_gw:40006/v1/messages,
  FALLBACK_UPSTREAM_URL=ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130,
  UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3.
