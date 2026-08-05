# R808: cc2 — NOP 巡检轮, R806 补丁已就位待下次瞬断验证

**时间**: 2026-08-05 10:55 CST
**决策**: NOP — 无源码改动、无 env 改动、无容器重启. 当前稳定, R806 WAIT-RECOVER 补丁已加载待触发.

## 本轮改动 (无)

R807 之后未改码、未改 env、未重启容器. 本轮工作: 拉数据 + 时间线核实 + R806 补丁静态审查 + 判稳 NOP.

## 时间线核实 (R807 STATE 修正)

R807 STATE 写 "容器启动 10:32 CST" — 本轮用 `docker inspect nv_gw --format '{{.State.StartedAt}}'` 核实:
- **nv_gw StartedAt = 2026-08-05T02:32:28Z = 10:32:28 CST** (确认正确)
- `docker ps` 显示 "Up 17 minutes, Created 09:10:54" 的 09:10 是 **CreatedAt** 不是 StartedAt, R807 STATE 记的 10:32 是对的
- 502 req=357b71d9 发生于 10:09-10:15 CST, 早于容器启动 22 分钟, 属**上一容器实例** (旧代码, R806 补丁未加载)
- 当前容器实例启动后 23min 内 (10:32→10:55) 暂未触发 WAIT-RECOVER 场景, 补丁待下次集中瞬断自动验证

## 数据 (实测 30min, 2026-08-05 ~10:55 CST, 拉自 hermes_logs DB)

### cc4101-primary nv_requests (cc2 自己链路最可信证据)
- 30min caller=cc4101-primary: **78×200 = SR 100%**, 零 502 零 fallback.
- 路径: nv_gw(40006) → 5key RR (fid=b1b22d03) pexec_us_rr.

### cc2 自己链路 tier SR (JOIN nv_requests 限定 caller=cc4101-primary)
- 30min: k0:17, k1:16, k2:20, k3:17, k4:17 = **87 attempts 全 pexec_success**
- 平均延迟: k0=15900ms, k1=12700ms, k2=10900ms, k3=12100ms, k4=11500ms (10-16s 一次过)
- **零 RemoteDisconnected / 零 529_nv_overloaded / 零 empty_200** — tier SR 100%

### cc4101 cc_requests (含 fallback)
- 30min: 79×200 + 2×499 + 1×200(fallback_triggered) = **SR 97.5%** (79/81)
- 2×499 = client_gone_mid_stream (cc2 SDK 自己 idle/超时断开, 非链路错)
- 1×200 fallback (rid=773517d9, 02:33:10 UTC = 10:33:10 CST, duration 41770ms): 容器重启后 38s 内, 第一条请求命中瞬时全挂窗口, cc4101 fallback ms_gw 干净挽回 (最终 200)
  - 走的是 cc4101 层 fallback (ms_gw:40007), **不是** nv_gw 层 fallback (NVU_DISABLE_MS_FALLBACK=1, nv_gw 不 fallback)
- fallback 触发率 1/81 = **1.2%** < 10% 目标

### 噪声 (不属 cc2 链路, 不计入决策)
- hermes × dsv4f0731_nv: 14×200/502 各半 (SR 50%) — dsv4f 自优化线持久不稳, 不穿透 cc4101-primary

## R806 补丁静态审查 (趁本轮 NOP 做)

`/app/gateway/buffer_stream.py:527-557` (容器内已加载):
```python
if _recovered:
    # R806: WAIT-RECOVER 后清掉 nv_start_key_override, 让 chain 走完整
    # 5key RR (NV_GLM52_MODE_CHAIN=pexec_us_rr, 一档), 而非被 _KEY_ROTATION
    # 固定到刚 probe 恢复的那 1 个 key.
    _remaining = self.total_deadline - time.time()
    _log("NV-BUFFER-WAIT-RECOVER",
         f"({self.request_model}) key recovered, retrying NVCF with full "
         f"5-key chain (override cleared), remaining={_remaining:.0f}s (req={_rid})")
    verdict, reason = None, None
    if _remaining < 30:
        # 剩余预算不足以跑 chain (~chain_budget_s 默认 120s), 不浪费配额
        _log("NV-BUFFER-WAIT-NO-TIME", ...)
    else:
        self._reset_for_retry()
        self.attempt = 0  # 重置 attempt 以从头选 healthy key
        self.metrics.pop("nv_start_key_override", None)  # 清掉 override
        verdict, reason = self._execute_and_drain(self.timeout_stairs[0], is_first=False)
```
逻辑正确:
1. 恢复后先判剩余预算 < 30s → skip, 保持 verdict=None → 走 WAIT-FAIL (避免浪费配额)
2. 否则 reset + attempt=0 + pop override → 调用 `_try_glm52_mode_chain` 走完整 5key RR (无 override 时 `_chain_max_attempts=NVU_NUM_KEYS+2=7`)
3. 新字串 `5-key chain (override cleared), remaining=Xs` 就位 — 验证用签到字串, grep 即可

## 判稳结论

| 指标 | 实测 | 阈值 | 判定 |
|---|---|---|---|
| cc4101-primary nv_requests SR | 100% (78/78) | ≥85% | ✅ |
| cc2 自己链路 tier SR (b1b22d03) | 100% (87/87) | ≥90% | ✅ |
| cc4101 cc_requests SR (含 fallback) | 97.5% (79/81) | ≥99% | ⚠ 2 个 499 是客户端断开非链路错, 1 fallback 干净挽回 → 实质链路稳 |
| fallback 触发率 | 1.2% (1/81) | <10% | ✅ |

- 链路当前稳定, 无新错误, 无需改码
- R806 补丁已就位, 等下次集中瞬断场景自动触发验证 (无需主动构造)

## SR 趋势 (校正后, 接续 R807)

| 轮 | 30min SR (cc4101-primary) | tier SR (b1b22d03 cc2 自链) | 备注 |
|---|---|---|---|
| R798-R804 | "99-100%" (STATE) | 不可考 | STATE 写"tier 零错"基于噪声误读, 未交叉核实 |
| R805 | "100%" (STATE) | 不可考 | STATE 失真 |
| R807 | 98.9% (91/92) | 98.9% (91/92) | 校正: 502 来自 WAIT-RECOVER 1-key 弱点 (上轮容器实例, R806 补丁未加载) |
| **R808** | **100% (78/78)** | **100% (87/87)** | R806 补丁已加载 (容器 10:32 启动), 当前窗口无集中瞬断, 待下次自动验证 |

## 下一步

- **R809**: 监测下一次集中瞬断. 期望日志出现新字串 `NV-BUFFER-WAIT-RECOVER (glm5_2_nv) key recovered, retrying NVCF with full 5-key chain (override cleared), remaining=Xs`, 验证补丁是否真跑完整 5key chain 挽回 502.
  - 补丁生效 (chain 成功) → 502 应消失, 无需进一步改
  - 补丁跑 chain 仍全失败 → 瞬断范围更大, 评估 NVU_WAIT_QUEUE_MAX_WAIT 180→240s 或方案 C (放宽 cc4101 STREAM_TOTAL_DEADLINE 470→~600s 接近 SDK 上限)
  - 补丁触发但 verdict 仍 None 走 WAIT-FAIL → 检查 `_remaining < 30` 分支是否过早 skip, 评估放宽阈值
- 当前不动码, 等数据.

## 参数快照 (R808 = R807 = R805 = R796, 无改动)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180** (R796), NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (实测 cc2 实际走 fid=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空), NV_GLM52_MODE_CHAIN=pexec_us_rr
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw 容器启动: 2026-08-05 10:32:28 CST (R806 WAIT-RECOVER 补丁已加载, `docker inspect` 核实)
- cc4101: PRIMARY_UPSTREAM_MODEL=glm5_2_nv, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages
- cc4101: FALLBACK_UPSTREAM_MODEL=glm5_2_ms, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/messages
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130
