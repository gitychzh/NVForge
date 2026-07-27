# R2408: R-nvonly — 纯 glm5_2_nv 链路重构, 去掉 ms_gw fallback

**日期**: 2026-07-28
**主机**: HM2 (部署)
**目标**: 仅用 5key + 5美国IP + glm5_2_nv (NVCF pexec), SR ≥ 95%, 彻底不滑到 glm5_2_ms

## 背景

与本机 ChatGPT 两轮讨论后的共识方向。数据(3h 窗口):
- nv_gw SR=66.7% (114成功, 44 all_tiers_exhausted, 12 buffer_exhausted)
- cc4101 SR=79.7% (96 primary + 53 fallback 成功, 29 stream_total_deadline)
- 0 次 429, 7 次 RemoteDisconnected, per-key 成功率全 100%
- 失败全因 key cooling (RemoteDisconnected 走 30→60→120s 冷却)

ChatGPT 核心判断: 瓶颈不是 NVCF 能力,而是 KeyManager 对瞬时故障的误判和误冷却。

## 改动 (4 phase 一次部署)

### Phase 1: RemoteDisconnected 错误分类修复 (⭐⭐⭐⭐⭐)

**文件**: `gateway/key_manager.py`, `gateway/upstream.py`

`key_manager.py`:
- 新增 `mark_transport_error(tier_model, key_idx, error_type)` 方法
- RemoteDisconnected / ConnectionReset / ConnectionRefused → penalty **5s**, **不增 conn_count**
- SSLEOFError / SSLError → penalty **10s**, **不增 conn_count**
- 新增配置: `NVU_KEYMGR_TRANSPORT_PENALTY_S=5` (默认), `NVU_KEYMGR_SSL_PENALTY_S=10` (默认)
- 原 `mark_conn_error` (30→60→120s) 仍保留给 `socket.timeout`

`upstream.py`:
- 新增 `_km_mark_transport` helper
- `_glm52_single_attempt` 中:
  - `except (ConnectionRefusedError, http.client.RemoteDisconnected)` → 调 `_km_mark_transport` (原 `_km_mark_conn`)
  - `except Exception` 中 SSL 类 → 调 `_km_mark_transport` (原 `_km_mark_conn`)

### Phase 3: 统一 deadline 三层 (⭐⭐⭐⭐☆)

| 层级 | 旧值 | 新值 |
|---|---|---|
| buffer attempt 每次 | 150s | **90s** |
| buffer total deadline | 600s | **380s** (90×4=360+20) |
| cc4101 stream_total_deadline | 800s | **400s** (buffer 380+20) |

层级: UPSTREAM(90s) < TIER_BUDGET(120s) < buffer(90×4=360s) < buffer_total(380s) < cc4101(400s)

### Phase 4: 禁用 cc4101 ms_gw fallback (⭐⭐⭐☆☆)

`docker-compose.yml` cc4101 service:
- `FALLBACK_UPSTREAM_URL=none` (原 `http://ms_gw:40007/v1/messages`)

cc4101 adapter 的 `_try_fallback` 会 `return False` when URL is None, 不再走 ms_gw。

### Phase 2: Caller 固定 preferred key (待后续)

当前 buffer 层的 key 轮转表是硬编码 k2→k5→k3→k4, 已有 `NVU_CALLER_KEY_MAP` 逻辑。
Phase 2 计划改为动态首选 caller key, 暂未部署。

## 配置变更

`docker-compose.yml` (HM2):
```yaml
# nv_gw:
NVU_BUFFER_TIMEOUT_STAIRS: 90,90,90,90     # was 150,150,150,150
NVU_BUFFER_TOTAL_DEADLINE_S: 380            # was 600

# cc4101:
CC4101_STREAM_TOTAL_DEADLINE_S: 400         # was 800
FALLBACK_UPSTREAM_URL: none                 # was http://ms_gw:40007/v1/messages
```

## 验证

- `curl /health` → 200, 5 keys, glm5_2_nv
- `docker exec nv_gw python3 -c "from gateway.key_manager import KeyManager; print(hasattr(KeyManager, 'mark_transport_error'))"` → True
- `docker exec cc4101 env | grep FALLBACK_UPSTREAM_URL` → none
- E2E test: `curl cc4101 /v1/messages stream=true` → 200, glm5_2_nv SSE 流式返回
- `cc_requests` 查询: `fallback_triggered=f` (0 fallback)

## 预期效果

1. RemoteDisconnected 不再冻 key 30-120s, 5s 后重新可用 → 大幅减少 all_tiers_exhausted
2. buffer 90s×4 + cc4101 400s → 不再有 887s 超长挂死
3. ms_gw fallback 彻底关闭 → cc4101 只走 nv_gw
4. 风险: 若 NVCF 真的持续故障, 无 ms_gw 兜底, SR 会暂时下降

## 回滚

```bash
cd /opt/cc-infra
cp docker-compose.yml.bak.R-nvonly docker-compose.yml
# key_manager.py / upstream.py 在 bind-mount 中, 需恢复:
cp proxy/nv-gw/gateway/key_manager.py.bak.R-nvonly proxy/nv-gw/gateway/key_manager.py
# upstream.py 需手动恢复 (无 .bak, 但改动可逆)
docker compose up -d nv_gw cc4101
```
