# R296 — NOP 巡检轮 (2026-08-02 16:48 CST)

## 接棒
- 主仓 hermes_improve_self main `cd2cec4` (R295), `git pull --ff-only` already up to date.
- 容器: nv_gw Up 2h, cc4101 Up 2h, nv_gw_stable Up 15h, ms_gw/logs_db Up 3 days.
- `curl /health` → ok, nv_num_keys=5, nvcf_pexec_models=[kimi_nv,dsv4p_nv,glm5_2_nv].

## 本轮数据 (30min 实时 DB ~16:48 CST)

### cc2 (cc4101-primary) 30min: 0 req
- 同 R275-R295, session 间歇空闲, 链路空闲健康. 0 fallback 0 deadline.
- buffer/wait/keymanager 日志 (BUFFER-/WAIT-) 30min 空, 无 buffer 流量.

### dsv4p_nv 30min 全 caller: SR=60.0% (6/10)
| status | count | 备注 |
|---|---|---|
| 200 | 6 | key2 egress 203.10.96.139 健康 |
| 429 | 4 | NVCF function 级配额边界 |

- 错误分类: 全 `all_tiers_exhausted` (4 条), 无新错误类型, 与 R268-R295 一致.
- fallback 0/10.
- tier_attempts 30min 0 行 (function 级 429 不产生 tier attempt).
- KeyManager 日志: 16:25/16:30/16:40 三波 429, count decayed (>300s) 自恢复机制正常工作,
  16:40 全 key count decayed → reset → cooldown 180s, 与 R278-R295 周期自恢复一致.

## 根因 (沿用 R278-R295, 无变化)
- NVCF function 级 429 配额周期: function 配额耗尽时 5key 同时 429 → all_tiers_exhausted.
- 这是设计盲区非代码缺陷. R-nvonly 5key 5IP 针对 key/IP 级隔离, 未覆盖 function 级配额.
- 周期自恢复 (429 窗口 → 200 恢复 → 再 429), 非 nv_gw 代码缺陷.
- cc2 流量为 0 不受影响.

## 判稳
- **NOP 巡检轮**. cc2 primary 0 req, 链路空闲健康, 0 fallback 0 deadline.
- SR 不达 99% 但 cc2 流量为 0, dsv4p_nv 低 SR 是 NVCF function 配额周期, 自恢复.
- 二十九轮一致 R268-R296. 0 改动 0 restart.

## 下一步
- 继续 NOP 巡检, 等 cc2 流量恢复后观察 dsv4p_nv SR.
- 关注是否出现新错误类型 (非 all_tiers_exhausted) 或 key/IP 级故障, 再决定是否介入.

## 参数快照 (无变化, 同 R295)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10,
  NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s), NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- cc4101: FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, CC4101_PRIMARY_SKIP_S=30,
  PRIMARY_UPSTREAM_MODEL=dsv4p_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
