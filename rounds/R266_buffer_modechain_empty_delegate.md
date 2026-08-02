# R-nvonly-post266 — buffer MODE_CHAIN 空委托修复 (2026-08-02 14:30 CST)

## 本轮改动
**buffer_stream.py `_execute_and_drain`**: NV_GLM52_MODE_CHAIN 为空时不再硬调
`_try_glm52_mode_chain` (必败), 改委托 `execute_request` (integrate-first 健康路径).

```python
if NV_GLM52_MODE_CHAIN:
    chain_result = _try_glm52_mode_chain(...)
else:
    chain_result = execute_request(self.handler, self.oai_body, _mapped, _rid, self.metrics, _chain_t_start)
```
+ 从 config 导入 `NV_GLM52_MODE_CHAIN`.
+ 新增 `NV-BUFFER-EXEC-DELEGATE` 日志行 (标记委托路径命中).

备份: `buffer_stream.py.bak.R266`.

## 依据 (根因定位)
30min 窗口 cc2(cc4101-primary) 5 req glm5_2_nv 全 200 (SR=100% 表面), 但
**4/5 走了 nv_gw→ms_gw fallback** (nv_key_idx 空, dur 166-202s). 实际 primary 链
SR = 1/5 = 20%, 是真实故障, 非自愈.

DB nv_requests: 10 req (40min 窗口) → 8×fallback (nv_key_idx 空, dur 170-202s)
+ 2×nv-direct-success (b6f90fbb k2 70s, 27d7f498 k3 5s).

日志根因:
- 8 fallback 请求全走 `NV-BUF2KEY-INTERCEPT` → `NV-BUFFER-EXEC-FAIL` 5×attempt,
  attempt1 elapsed=0s, all_keys_exhausted=True, **无 NV-GLM52-*/NV-INTEGRATE 日志**.
- 2 成功请求走 `NV-REQ` → `NV-INTEGRATE` 路径 (未拦截, 健康).

代码追踪:
- `_try_glm52_mode_chain` (upstream.py:1378-1384): `if not modes: result.all_keys_exhausted=True;
  return` — **无日志**, 0s 返回.
- `NV_GLM52_MODE_CHAIN=` (空, docker-compose.yml:97, R-nvonly-post14 设计意图:
  glm5_2_nv 走标准 integrate-first ���径).
- `execute_request` (upstream.py:1706) 对 glm5_2_nv 已正确门控:
  `if ... and NV_GLM52_MODE_CHAIN` 才调 mode chain, 空→跳过→走 integrate-first.
- 但 `buffer_stream._execute_and_drain` (旧 line 281) **无条件**调
  `_try_glm52_mode_chain` → MODE_CHAIN 空 → 必败 → 5×retry→ms fallback,
  从不尝试可用的 integrate/pexec 路径.

**bug 性质**: buffer 拦截路径硬编码 mode chain 调用, 与 execute_request 的门控不一致.
MODE_CHAIN 空时, 非 buffer 路径健康 (14:21 k4 5s 成功), buffer 路径必败.
路由为何部分走 buffer 部分不走 (同 caller 同 endpoint) 未完全定位, 但不影响本修复正确性 —
无论哪条请求进 buffer, 都应走健康路径而非必败路径.

## 验证 (14:30 CST)
| 项 | 结果 |
|----|------|
| py_compile (ast.parse) | SYNTAX OK ✓ |
| docker compose restart nv_gw | Started ✓ |
| nv_gw /health | ok, passthrough, 5 keys, default glm5_2_nv ✓ |
| docker ps | nv_gw Up 3s, cc4101/nv_gw_stable/ms_gw/logs_db Up ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0, NV_GLM52_MODE_CHAIN= (空, 不变) ✓ |

**功能验证待下个 cc2 流量窗口**: 期望 NV-BUFFER-EXEC-DELEGATE 日志出现 +
fallback_occurred=f + nv_key_idx 填充 + dur 回到正常 (5-70s).

## 参数快照 (本轮无变化, 同 post265)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, BUFFER_MAX_RETRIES=5, BUFFER_TIMEOUT_STAIRS=90×5, BUFFER_TOTAL_DEADLINE=450s, TIER_TIMEOUT_BUDGET=180s, TIER_COOLDOWN_S=180s, UPSTREAM_TIMEOUT=90s, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, MIN_OUTBOUND_INTERVAL_S=10, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150, NVU_FORCE_STREAM_UPGRADE=0, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, **NV_GLM52_MODE_CHAIN= (空, R-nvonly-post14 设计)**
- cc4101: CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150, CC4101_PRIMARY_SKIP_S=30, CC4101_PRIMARY_FAIL_THRESHOLD=3, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, PRIMARY_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms

## 下一步
1. 等下个 cc2 glm5_2_nv 流量窗口, 确认 NV-BUFFER-EXEC-DELEGATE 命中 + fallback_occurred=f
   + nv_key_idx 填充 + dur 回到正常 (5-70s). 验证修复生效.
2. 若仍 fallback, 检查 execute_request 内部是否走了 nv_breaker/big_input breaker
   短路到 ms (理论 CLOSED 状态不应, 但需确认).
3. 路由差异 (为何部分 cc2 请求进 buffer, 部���进 NV-REQ) 悬而未决, 待流量样本
   增多后定位 (可能与 cc4101 并发/重启重放有关, 14:13 窗口恰逢 cc4101 7min uptime).
