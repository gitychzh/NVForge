# R813 — restart 加载 R813 chain_full_retry 修复 (RECOVER 2h×11 全 FAIL 根因)

> 时间: 2026-08-05 12:20 CST
> 上轮: R812 (NOP — R806 WAIT-RECOVER 补丁首次 RECOVER 分支实战触发)
> 容器: nv_gw restart 12:18 CST (此前 10:32 启动, 加载老代码)

## 本轮发现 (根因定位)

### 现象
- 30min cc4101-primary nv_requests SR = **89.2%** (66/74: 66×200, 6×502, 2×499)
- cc4101 fallback 触发率 = **10.53%** (8/76 > 10% 阈值)
- 7×502: 5×all_tiers_exhausted + 2×buffer_exhausted, avg_dur 550-596s
- 2×499: client_gone_during_flush avg_dur 527s (用户等不住先断)
- **R806 WAIT-RECOVER 补丁 2h 内触发 11 次, 全部 WAIT-FAIL, 0 次 WAIT-OK**

### 根因 (铁证)
R812 commit (3f72bae, 11:42 CST) 已含 R813 `chain_full_retry=True` 修复 (buffer_stream.py:268-273, 571-572), **但容器主进程 10:32 CST 启动, 加载的是 R813 修复之前的老代码**. `docker exec python3 -c "import inspect"` 显示源码有 chain_full_retry (新进程 import 最新文件), 但主服务进程 (uvicorn) 缓存了 10:32 时的老代码, 不会重新 import.

日志铁证 (req=c55fb175, 12:14:15):
```
[12:14:15.0] [NV-BUFFER-WAIT-RECOVER] ... retrying NVCF with full 5-key chain (override cleared), remaining=253s
[12:14:15.0] [NV-GLM52-CHAIN] tier=glm5_2_nv BUFFER_OVERRIDE start_key=k2 (buffer _KEY_ROTATION, NVCF 1 attempt)
```
- WAIT-RECOVER log 触发 (line 552 在 _recovered=True 分支内, _remaining<30 判断外, 老代码也有)
- 紧接着 `BUFFER_OVERRIDE start_key=k2 ... NVCF 1 attempt` — 这是老 R806 逻辑 (_execute_and_drain line 282 `self.metrics["nv_start_key_override"] = _use_key_idx`), 只试 1 个 key
- R813 新代码 line 268 `if chain_full_retry:` 会 emit `NV-BUFFER-CHAIN-FULL` log 并跳过 override 设置
- **2h 内 NV-BUFFER-CHAIN-FULL log 0 次触发** → 主进程跑老代码, R813 修复未生效

老 R806 逻辑后果: RECOVER 后只试 probe 恢复的那 1 个 key, 若该 key 仍在抖 → 1.5-28s 立即 all_keys_exhausted → WAIT-FAIL → 502. 即使同期其他 4 key 已恢复也不会被试到.

## 本轮改动

### 改动: docker compose restart nv_gw (无源码改动, 加载已有 R813 修复)

R813 修复代码已于 R812 commit (3f72bae) 写入 buffer_stream.py, 本轮只需 restart 让主进程重新 import:

```python
# buffer_stream.py:235  _execute_and_drain signature
def _execute_and_drain(self, timeout_s, is_first=False, chain_full_retry=False):

# buffer_stream.py:268-273  R813 新分支
if chain_full_retry:
    _log("NV-BUFFER-CHAIN-FULL",
         f"({self.request_model}) chain_full_retry=True, skip override, "
         f"start_key=k{_use_key_idx+1} (RR起, NVCF chain full 5key) (req={_rid})")
    # 不设 nv_start_key_override → _try_glm52_mode_chain 走 RR, _chain_max_attempts=7

# buffer_stream.py:571-572  RECOVER 分支调用
verdict, reason = self._execute_and_drain(
    self.timeout_stairs[0], is_first=False, chain_full_retry=True
)
```

效果: RECOVER 后走完整 5key RR (_chain_max_attempts=7), 充分利用所有可能已恢复的 key, 而非被 _KEY_ROTATION 困在 probe 的那 1 个 key.

## 验证

### restart 前 (老代码, 2h 窗口)
- WAIT-RECOVER 触发 11 次, 全部 WAIT-FAIL
- NV-BUFFER-CHAIN-FULL 触发 0 次 (老代码无此 log)
- RECOVER 后 `BUFFER_OVERRIDE start_key=kX (NVCF 1 attempt)` (老逻辑, 只试 1 key)

### restart 后 (12:18 CST, 新代码)
- health OK: `curl /health` → status=ok, 5 keys
- docker exec 验证: `inspect.signature(_execute_and_drain)` → `(self, timeout_s, is_first=False, chain_full_retry=False)` ✅
- 待下个窗口观测: 若再触发 WAIT-RECOVER, 应出现 `NV-BUFFER-CHAIN-FULL` log (而非 `BUFFER_OVERRIDE ... 1 attempt`), 且 retry 走完整 5key chain

## 判稳结论

| 指标 | restart 前 30min | 目标 | 状态 |
|---|---|---|---|
| nv_gw SR (cc4101-primary) | 89.2% (66/74) | 90%+ | ⚠️ 略低 |
| fallback 触发率 | 10.53% (8/76) | <10% | ⚠️ 略超 |
| R806 RECOVER 成功率 | 0% (0/11) | >0% | ❌ 老代码未加载 R813 修复 |

**本轮实质: R813 修复代码早已 commit 但容器主进程未 restart 加载 → RECOVER 11 次全走老逻辑 (只试 1 key) → 全 FAIL. restart 后修复应生效, 待下个 RECOVER 触发验证.**

## SR 趋势

| 轮 | 30min SR (cc4101-primary) | per-attempt tier SR | RECOVER 触发 | 备注 |
|---|---|---|---|---|
| R810 | 100% (88/88) | 83.0% (88/106) | 0 | BUFFER 3-attempt 自愈 |
| R811 | 100% (91/91) | 100% (95/95) | 1 (fall-through) | WAIT 首触达 |
| R812 | 98.75% (79/80) | 78.2% (79/101) | 1 (RECOVER 首次) | 补丁 RECOVER 首触发 |
| **R813** | **89.2% (66/74)** | ~74% (72/cnt) | **11 (全 FAIL)** | **restart 加载 R813 修复** |

## 噪声 (不属 cc2 链路)

- hermes × dsv4f0731_nv: 30min SR 73.3% (11/15, 4×502) — dsv4f 自优化线, 不穿透 cc2

## 下一步

- **R814**: 监测 restart 后下一个 WAIT-RECOVER 触发:
  1. ✅ 预期: `NV-BUFFER-CHAIN-FULL` log 出现 (新代码生效标志)
  2. ✅ 预期: RECOVER 后走完整 5key RR, 非 `BUFFER_OVERRIDE ... 1 attempt`
  3. ⏳ 待观测: RECOVER retry 成功 → `NV-BUFFER-WAIT-OK` (补丁真正挽救 req)
  4. 若仍 WAIT-FAIL 但 CHAIN-FULL 出现: 说明 5key 确实全在抖, 需考虑:
     - ProbeWorker probe 间隔 15s 是否太短 (刚 probe 通但实际不稳)
     - NVU_WAIT_QUEUE_MAX_WAIT 180→240s (给 NVCF 更多恢复时间)
     - RECOVER retry 失败后给一次额外 WAIT (而非直接 FAIL)

## 参数快照 (R813 = R812 参数, 仅 restart)

- nv_gw StartedAt: 2026-08-05 12:18 CST (R813 chain_full_retry 修复已加载)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180
- nv_gw: KEY_COOLDOWN_S=30, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- nv_gw: NVU_BUFFER_MAX_RETRIES=5, NVU_BUFFER_TIMEOUT_STAIRS=90×5, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180, NVU_PROBE_INTERVAL=15
- nv_gw: NVU_KEYMGR_429_BASE=120 MAX=600, NVU_KEYMGR_CONN_BASE=30 MAX=60 FAIL_THRESHOLD=3
- cc4101: PRIMARY=glm5_2_nv @ nv_gw:40006, FALLBACK=glm5_2_ms @ ms_gw:40007
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130

## 一句话总结

R813 根因轮 — 30min SR 89.2% + fallback 10.53% 双双告警, 深挖发现 R806 WAIT-RECOVER 补丁 2h 内触发 11 次全 WAIT-FAIL. 根因: R812 commit 已含 R813 `chain_full_retry=True` 修复 (buffer_stream.py:268-273), 但容器主进程 10:32 启动加载老代码, R813 修复从未生效. 日志铁证: RECOVER 后走 `BUFFER_OVERRIDE start_key=kX (NVCF 1 attempt)` (老逻辑只试 1 key) 而非 `NV-BUFFER-CHAIN-FULL` (新逻辑走完整 5key RR). docker compose restart nv_gw 12:18 CST 加载新代码, 待下个 RECOVER 触发验证 CHAIN-FULL log + retry 成功.
