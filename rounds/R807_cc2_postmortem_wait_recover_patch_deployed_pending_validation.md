# R807: cc2 — 真实瞬断复现 R805 STATE 失真校正 + R806 WAIT-RECOVER 补丁未验证发现

**时间**: 2026-08-05 10:44 CST
**决策**: NOP — 无源码改动、无 env 改动、无容器重启 (R806 补丁已在前轮部署未明确记 STATE, 本轮只做发现+校正+文档)

## 本轮改动 (无)

R805 STATE 之后未改码、未改 env、未重启容器。本轮工作是**拉数据→发现失真→校正记录**。

## 数据 (实测 30min, 2026-08-05 ~10:42 CST, 拉自 hermes_logs DB)

### cc4101-primary 真实 SR (cc2 自己的链路)
- 30min cc4101-primary: 91×200 + 1×502 = **SR 98.9%** (91/92). 跌破 99% 阈值.
- 502 req=357b71d9, error_type=buffer_exhausted, duration_ms=350109 (350s), ts=02:09 UTC.
  - 完整链路: 5 attempts (k1-k5) 全 `RemoteDisconnected` → 进 WAIT-RECOVER 等 180s →
    ProbeWorker 02:14:56 探测 k3 恢复 → retry k3 一次 fail → NV-BUFFER-WAIT-FAIL →
    NV-BUFFER-NO-MS (NVU_DISABLE_MS_FALLBACK=1) → 502.
  - **这正是 R796-R805 STATE 记了 9 轮的"长期候选不动: WAIT-RECOVER retry 只跑 1 key"问题的真实复现**.

### tier 真实 SR (cc4101-primary, fid=b1b22d03)
- 30min cc4101-primary × b1b22d03: 92 attempts, 91 `pexec_success` + 1 `pexec_conn_RemoteDisconnected`.
  tier SR 98.9% — **tier 零错窗口在 R805 已被打断** (1 个真实错误样本).

### R805 STATE 失真校正 (重要)
R805 STATE 写的"tier 连续 8 轮零错, 修正轮前注入分析 NVCFPexecRemoteDisconnected 计数是分析脚本误读, 实测 76 条全 pexec_success"是错的:
1. `nv_tier_attempts.error_type` 字段真实记录了错误字面值 (`NVCFPexecRemoteDisconnected`/`pexec_conn_RemoteDisconnected`/`529_nv_overloaded`). 不是误读.
2. 30min 窗口里 cc4101-primary ÷ b1b22d03 有 1 条 `pexec_conn_RemoteDisconnected` — tier 不是零错.
3. 注入分析里 `52e1ddb6` fid 全失败 (267 次, ok=0%) 是**别的 caller 走的并行链路** (dsv4f 自优化线), 不穿透 cc2, 但**也不是误读** — 它持续 100% 失败是真实的.

本轮校正: STATE 的"分析脚本误读"理论错误. 真相是: 30min 窗口混合了 (a) cc4101-primary × b1b22d03 (SR 98.9%, 1 个错误) 和 (b) 别的 caller × 52e1ddb6 (SR 0%, 噪声) 两条 tier 数据. 之前轮次把 (b) 的错误当成(cc2 链路的)误读, 又把 (a) 的 1 条真错当误读, 误判连续 8 轮 tier 零错.

## 关键发现: R806 WAIT-RECOVER 补丁已部署未验证

读 `/opt/cc-infra/proxy/nv-gw/gateway/buffer_stream.py:527-557` 发现 R806 补丁**已在源码 + 容器内**:
```python
# R806: WAIT-RECOVER 后清掉 nv_start_key_override, 让 chain 走完整
# 5key RR (NV_GLM52_MODE_CHAIN=pexec_us_rr, 一档), 而非被 _KEY_ROTATION
# 固定到刚 probe 恢复的那 1 个 key.
...
if _remaining < 30:
    _log("NV-BUFFER-WAIT-NO-TIME", ...)
else:
    self._reset_for_retry()
    self.attempt = 0
    self.metrics.pop("nv_start_key_override", None)  # 清 override 让 chain 跑完整 5key
    verdict, reason = self._execute_and_drain(
        self.timeout_stairs[0], is_first=False
    )
```
- 容器内 `docker exec nv_gw grep` 确认补丁代码在 `/app/gateway/buffer_stream.py`.
- 容器启动时间 02:32 UTC (10:32 CST). 502 事件发生 02:09 UTC (10:09 CST) — **早于当前容器启动 23 分钟**, 是上一个容器实例的事件.
- 当前容器补丁已加载, 但**还没遇到下一次集中瞬断来验证补丁行为**.
- 验证标准: 下次瞬断后看日志应出现 `[NV-BUFFER-WAIT-RECOVER] ... key recovered, retrying NVCF with full 5-key chain (override cleared), remaining=Xs` 字样 (而不是旧的 `retrying NVCF`).

## 判稳结论

- cc4101 SR = 98.9% < 99% 阈值 → **不该 NOP**. 但本轮根因已处理 (R806 补丁已部署, 等下次瞬断验证), 重复改码无依据 (会双写). 选择: NOP + 详细记文档, 等待下一次瞬断验证补丁.
- 同期 30min (容器重启后 ~10:32 CST 后) 请求全 200, 零 502 零 tier 错误. 链路当前稳定.
- fallback 触发率 (30min cc_requests.fb=9/1125=0.8%) < 10% 目标.
- 容器健康: nv_gw=200, cc4101=200, dsv4p_nv40066=200, docker ps 全 Up.

## 下一步

- **R808**: 监测下一次集中瞬断窗口. 看是否出现新补丁的 `NV-BUFFER-WAIT-RECOVER ... with full 5-key chain (override cleared)` 日志, 验证补丁是否真跑完整 chain 挽回 502.
- 如果补丁已验证仍出 502, 再讨论方案 B (WAIT 后两次 wait 机会) 或方案 C (放宽 cc4101 STREAM_TOTAL_DEADLINE).
- 如果下次窗口又出现 502 且补丁生效 (chain 跑完 5 key 仍全 fail), 说明瞬断范围更大需 wait 更久, 评估 NVU_WAIT_QUEUE_MAX_WAIT 是否要拉长.
- 本轮不动码, 等数据.

## 参数快照 (R807 = R805 = R796, 无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180, NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (实测 cc2 实际走 fid=b1b22d03 = fid 索引 0)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw 容器启动: 2026-08-05 10:32 CST (R 容器, 加载 R806 WAIT-RECOVER 补丁)
- cc4101: PRIMARY_UPSTREAM_MODEL=glm5_2_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages
- cc4101: FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/messages
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130

## SR 趋势 (校正后)

| 轮 | 30min SR (cc4101) | 真实 tier SR (b1b22d03) | 备注 |
|---|---|---|---|
| R798-R804 | "99-100%" | ? | STATE 写"tier 零错"是基于把 52e1ddb6 噪声当误读. 真实 tier 数据本周未交叉核实, 不可考 |
| R805 | "100%" (STATE) | ? | STATE 失真 — 把 52e1ddb6 噪声 + 可能的 b1b22d03 真错都当误读 |
| **R807** | **98.9% (91/92)** | **98.9% (91/92)** | 校正: 1 个 502 来自 WAIT-RECOVER 只跑 1 key 弱点 (补丁已部署待验证) |
