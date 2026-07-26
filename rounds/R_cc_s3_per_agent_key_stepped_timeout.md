# R cc_s3: per-agent 固定 key 绑定 + cc4101 阶梯超时重试

> 标签 `cc_s3` (第三个成功节点). 部署于 HM2 (100.109.57.26). 本轮目的: 探测 NVIDIA
> 单 key 配额规则 (每 agent 只用 1 个固定 key), 并给 cc4101 加阶梯超时重试
> (60→120→240s, 3 次都 timeout 报 `error:time out3`).

## 背景

用户要求把 nv_gw 原本的 5-key 轮转改为 **per-agent 固定单 key**:
- cc (cc4101) → k2
- hermes (hm4104) → k3
- openclaw (opclaw4103) → k4
- opencode (oc4105/cx4102) → k5

目的是探测 NVIDIA 对每个 key 的具体限额规则. 同时给 cc4101 加阶梯超时:
60s → 120s → 240s, 每轮间隔 2s, 3 次都超时直接告诉 CC `error:time out3`.

## 数据 (改前)

- glm5_2_nv pexec+5US 裸测: 92%→96% SR (见 memory r-probe-glm52-pexec-5us-20260726).
- nv_gw 5-key 轮转下 cc4101-primary 的 DB 记录: 08:32 之前 nv_key_idx=4 (k5),
  08:33 nv_key_idx=1 (k2) — 轮转中, 无法固定探测单 key 配额.

## 变更 (3 文件, HM2)

### 1. nv_gw `config.py` — 新增 `NVU_CALLER_KEY_MAP` env 解析

```python
# NVU_CALLER_KEY_MAP: "caller_name:key_idx;caller_name:key_idx" (0-based key idx).
# 命中 caller 时只用绑定的那一个 key (不走 5-key 轮转), max_attempts=1.
NVU_CALLER_KEY_MAP = {}  # 从 env 解析
```

### 2. nv_gw `upstream.py` — caller→fixed key 注入

- `_try_glm52_mode_chain` (line ~1325): 命中 `NVU_CALLER_KEY_MAP[caller]` 时
  `start_key = bound_key`, `_chain_max_attempts = 1` (不跨 key 轮转).
- `execute_request` 调 `_try_tier_keys` (line ~1709): 命中时传
  `start_key_idx_override=bound_key, max_attempts_override=1` (复用 R2224 peek-retry 机制).

### 3. cc4101 `upstream.py` + `handlers.py` — 阶梯超时重试

- `upstream.py`: `execute_request` 加 `header_timeout_override=None` 参数,
  `_try_primary`/`_try_fallback` 内非 None 时覆盖 R2154 分档 `_hdr_to`.
- `handlers.py` `do_POST`: 包裹 execute_request 在阶梯循环里:
  ```python
  TIMEOUT_STAIRS = [60, 120, 240]   # 秒
  RETRY_INTERVAL_S = 2             # 阶梯间 sleep
  for _hdr_to in TIMEOUT_STAIRS:
      result = execute_request(..., header_timeout_override=_hdr_to)
      if result.success: break
      if result.error_kind != "timeout": break  # 非超时错误不重试
      if not last: time.sleep(RETRY_INTERVAL_S)
  else:
      self._send_json(504, {"type":"error","error":{"type":"timeout","message":"error:time out3"}})
  ```

### 4. docker-compose.yml — env

```yaml
- NVU_CALLER_KEY_MAP=cc4101-primary:1;hermes:2;openclaw:3;opencode:4
```
(cc=k2 idx1, hermes=k3 idx2, openclaw=k4 idx3, opencode=k5 idx4, 0-based)

## 验证 (改后, HM2)

1. **config 加载**: `docker exec nv_gw python -c "from gateway import config; print(config.NVU_CALLER_KEY_MAP)"`
   → `{'cc4101-primary': 1, 'hermes': 2, 'openclaw': 3, 'opencode': 4}` ✓
2. **nv_gw 日志**: `CALLER_BIND caller=cc4101-primary -> fixed key=k2 (no cross-key rotation, max_attempts=1)` ✓
3. **E2E** (curl cc4101 /v1/messages): 200, 返 GLM-5.2, `hdr_to=60` (第一阶梯生效, 覆盖 R2154 的 25s) ✓
4. **DB nv_requests**: cc4101-primary → `nv_key_idx=1`, `egress_ip=134.195.101.193`,
   `egress_route=glm52-mihomo-7895` (k2 专属代理), status=200, duration=4448ms ✓
5. **DB cc_requests**: status=200, mapped_model=glm5_2_nv ✓

## 阶梯超时路径说明

- 阶梯仅在 `error_kind == "timeout"` 时连续推进; client_4xx/server_5xx/conn 直接返回原错误.
- 3 次都 timeout → `504 error:time out3` (CC 看到后会自己重试/换路径).
- 阶梯超时覆盖 primary 与 fallback 两条分支 (`header_timeout_override` 在两处生效).

## 后续 (本轮不做)

- Stage 4: cc-adapter (hm4104/opclaw4103/oc4105/cx4102) 加 `X-Caller: ADAPTER_NAME` header
  + 阶梯超时 (forwarder.py 现无 X-Caller, 导致 nv_gw DB 521 "unknown" caller). 等 hermes/openclaw/opencode 流量验证.
- 阶梯超时在线触发需等真 NVCF timeout; 当前路径已验证逻辑 + 小请求成功路径.

## 回滚

- nv_gw: 删 docker-compose.yml `NVU_CALLER_KEY_MAP` 行 → `docker compose up -d nv_gw`;
  upstream.py 回滚用 `upstream.py.bak.cc_s3`.
- cc4101: `handlers.py.bak.cc_s3` + `upstream.py.bak.cc_s3` 回滚 → `docker compose up -d cc4101`.

## 铁律

- 改前有数据 ✓ (pexec+5US 96% SR + DB 轮转记录)
- 改后有验证 ✓ (config/env/log/E2E/DB 五重验证)
- 聚焦 nv_gw ✓ (nv_gw caller-bind + cc4101 阶梯, 都在 40006/4101 链上)
- 写入仓库 ✓ (deploy_artifacts/cc_s3_per_agent_key_stepped_timeout/ + 本 round + tag cc_s3)
