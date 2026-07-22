# R2252 (HM2): nv_gw peek 内部换 key 重试 — 撤40007第一步代码改造

> 承接 SPEC-003(撤40007路线图)的"核心卡点":把 peek 软挂的恢复职责
> 从"切外部 ms_gw 后端"下沉到"nv_gw 内部多 key 自愈"。本轮只做代码改造 +
> shadow 验证,**不撤 40007**(ms_gw 保留作二线)。ChatGPT 设计讨论见
> chatgpt_api 仓库 `docs/nv_gw_peek_internal_keyretry_design.md`。

## 改前数据(6h 基线, 2026-07-22 13:37-19:37)

| 指标 | 值 |
|---|---|
| 总请求 | 703 |
| status=200 | 624 (88.8%) |
| peek first_byte 软挂 | 0 (DB error_type 字段, 本 6h 无) |
| ms_fallback 走的 | 212 (30.2%) |

注:212 ms_fallback 不全是 peek 软挂触发,含 all_tiers_exhausted/429 等。
peek 软挂数据需靠 `NV-PEEK-PROBE SOFTFAIL` 日志统计(DB error_type 字段
记录有 gap, 见 R2180)。本轮改造效果靠日志计数对比。

## 改造内容(仅 HM2, 3 文件)

### 1. config.py — 新 env 开关

```python
NVU_PEEK_RETRY_KEYS = int(os.environ.get('NVU_PEEK_RETRY_KEYS', '2'))   # 内部换 key 次数, 0=禁用(回退现状)
NVU_PEEK_RETRY_BUDGET_S = float(os.environ.get('NVU_PEEK_RETRY_BUDGET_S', '0'))  # 0=用 _fb_s 单 key 上限
```

默认 `=2`(ChatGPT 建议限 1-2,不试满 5T 打穿 SLA)。`=0` 回滚开关。

### 2. upstream.py — `_try_tier_keys` 加两可选参数 + 新增 `_peek_retry_next_key`

- `_try_tier_keys(..., start_key_idx_override=None, max_attempts_override=None)`:
  传 `start_key_idx_override` 时不调 `_next_nv_key`(不 advance RR counter,避免
  peek-retry 污染全局轮转);传 `max_attempts_override=1` 只试指定 key 一次。
- 新增 `_peek_retry_next_key(oai_body, tier_model, request_id, metrics, t_start,
  is_stream, prior_cycle_attempts, start_key_idx, upstream_timeout_override)`:
  包装 `_try_tier_keys(max_attempts=1, start_key_idx_override=start_key_idx)`,
  返回 `UpstreamResult`(带 resp/conn/nv_key_idx/egress_ip)。独立小循环,
  不进 execute_request 全量 5-key 轮转(ChatGPT: 避免污染 key 状态、扩大延迟)。

### 3. handlers.py — `_stream_openai_to_anth` peek 软挂分支插入内部 retry 子循环

在 `conn.close()` 后、`_ms_fallback_request` 前,插入:

```
_internal_rescued = False
_retry_keys_left = NVU_PEEK_RETRY_KEYS
_retry_next_k = (orig_softfail_key + 1) % NVU_NUM_KEYS   # 跳过刚软挂的 key
while _retry_keys_left > 0 and not _internal_rescued:
    _r = _peek_retry_next_key(..., start_key_idx=_retry_next_k)
    if _r.success and _r.resp:
        # 对新 resp 重新跑 peek barrier (确认新 key 也健康才 commit)
        _np_content_seen = _do_inline_peek(_r.resp, _fb_s, ...)
        if _np_content_seen:
            resp, conn = _r.resp, _r.conn
            metrics["nv_key_idx"], metrics["egress_ip"] = ...
            _peek_swapped = True; _internal_rescued = True
            cap_origin = now; converter reset; ...  # 复用 ms-swap 成功分支模式
            log("NV-PEEK-INTERNAL-RESCUE")
        else:
            # 新 key 也软挂, 记 breaker, 关 conn, 换下一个
            big_input_breaker.record_big_input_failure(...)
            _r.conn.close(); _retry_next_k = (_retry_next_k+1) % NVU_NUM_KEYS
    else:
        _retry_next_k = (_retry_next_k+1) % NVU_NUM_KEYS
# retry 耗尽才落 ms_gw (二线保留, 现状语义不动)
if not _internal_rescued:
    _ok, _ms_r = _ms_fallback_request(...)
```

**ChatGPT 确认的 commit-point 边界**:peek barrier = SSE transaction commit
barrier。peek 窗口内 `send_response(200)` 未发,message_start 未 commit 给下游,
换 key 重放安全;新 key 重新 peek 确认健康才 commit。peek 之后的软挂
(no_content_gap / total_deadline / 流中途 hang)维持现有 graceful end,不动。

## 改造参数

| 参数 | 改前 | 改后 | 说明 |
|---|---|---|---|
| NVU_PEEK_RETRY_KEYS | (不存在) | 2 | 内部换 key 次数, 0=回退 |
| NVU_PEEK_RETRY_BUDGET_S | (不存在) | 0 | 0=用 _fb_s 单 key 上限 |
| peek 软挂恢复路径 | 直走 ms_gw | 先内部换 2 key, 耗尽才 ms_gw | 恢复职责下沉 |
| ms_gw (40007) | 二线 | 二线(保留) | 本轮不撤 |

## 预期效果

- peek 软挂后,先在 nv_gw 内部换 1-2 个 NVCF key 重放,救回一部分原本会落
  ms_gw 的请求 → `NV-PEEK-INTERNAL-RESCUE` 计数 > 0,`NV-PEEK-MS-OK` 下降。
- 恢复职责从 cc4101 切外部后端,下沉到 nv_gw 内部多 key 自愈(撤 40007 前置)。
- 最坏延迟增加 1-2 个 key 的 peek deadline(复用 `_fb_s` 按 input 分档,有界)。

## 验证清单(改后)

- [x] 三文件 `ast.parse` 通过(本地 + HM2 容器内)。
- [x] `docker compose restart nv_gw` 成功,`/health` 返 ok。
- [x] 容器加载新代码:`ProxyHandler._stream_openai_to_anth` 内 R2224×2、
      `NV-PEEK-INTERNAL-RESCUE`×1、`_internal_rescued`×5;`_peek_retry_next_key`
      可调用;`NVU_PEEK_RETRY_KEYS=2` 生效。
- [x] 启动日志干净,正常请求走 `NV-PEEK-OK` 健康分支不受影响(R2224 只在
      peek 软挂 else 分支触发)。
- [ ] **shadow 验证(待 3-6h)**:观察 `NV-PEEK-INTERNAL-RESCUE` 日志计数 +
      `NV-PEEK-PROBE SOFTFAIL` 的 key/IP 分布;对比改造前后 `ms_fallback` 请求数。
- [ ] **DB 验证(待 6h)**:改造后 6h `nv_requests` 里 `peer_fallback_ms=0` 且
      `upstream_type=nvcf_pexec` 的请求(内部救回)数量;无新增 mid-response
      中断/499。
- [ ] 回滚开关验证(备):`NVU_PEEK_RETRY_KEYS=0` + restart = 回退现状。

## 回滚

- `NVU_PEEK_RETRY_KEYS=0` + `docker compose restart nv_gw` 即回退(跳过内部
  retry,直接走 ms_gw,等价改造前)。
- 源码回滚:`cp handlers.py.bak.R2224_20260722 handlers.py`(三文件备份在
  `/opt/cc-infra/proxy/nv-gw/gateway/*.bak.R2224_20260722`)。

## 风险与边界

- **延迟**:最坏 1-2 个 key 的 peek deadline 叠加,但限 2 + 复用 `_fb_s`
  单 key 上限,总延迟有界。若实测打穿 SLA,调小 `NVU_PEEK_RETRY_KEYS` 或设
  `NVU_PEEK_RETRY_BUDGET_S`。
- **key 状态污染**:用 `start_key_idx_override` 不 advance RR counter,不污染。
- **新 key 也��挂**:每记 breaker + 换下一个,耗尽落 ms_gw(现状兜底不动)。
- **mode-chain 一致性**:正常 glm5_2_nv 走 R839 mode-chain,peek-retry 调
  `_try_tier_keys`(pexec)。软挂时换 pexec 路径反而避开原软挂 mode,可接受。
- **HM1 nv_gw 不改**(无 format/ 无 R1716 peek;铁律聚焦 HM2)。

## 下一步(撤 40007 路线,见 SPEC-003)

1. 本轮 shadow 验证达标(内部救援率 > 0,无新增中断)后,进入灰度:
   把 `NVU_PEEK_RETRY_KEYS` 调大或覆盖更多软挂场景。
2. 影子 agent(hermes2/openclaw2)跑 150K+ 纯主路径数据(SPEC-003 前置条件 2)。
3. 达量化标准(7-14 天 大输入 僵尸率<0.1% 流中断<0.1% 自恢复>99%)才撤 40007。
