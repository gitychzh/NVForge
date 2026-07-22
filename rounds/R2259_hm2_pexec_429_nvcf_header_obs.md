# R2259 (HM2): nv_gw pexec 429 响应头观测点 — 撤连环 429 后抓 NVCF 限流维度

> 承接: R2258 webui watchdog 落地后的推进轮. 用户指令"继续推进".
> 本轮只加观测(HM2 only), 不动逻辑. 改前必有数据: 6h + 12h 采完确认 dsv4p_nv pexec 429 日间恶化是真病.

## 一、数据 (改前必有数据)

### 6h 窗口 (22:30 采)
```
nv_gw: 716 req / 618 OK (86.3% SR) / 69 ATE / 15 zombie / 0 个 499 / 0 个 429
```
- ATE 69 个 **全是 dsv4p_nv**, `upstream_type` 全 NULL, `nv_key_idx` 全 NULL,
  `max_dur=180046ms` = 5 key 试一遍全挂耗尽 `TIER_TIMEOUT_BUDGET_S=180s` budget.
- 错误分布:
  - dsv4p_nv: 69 ATE + 1 zombie
  - glm5_2_nv: 14 zombie + 9 stream_absolute_cap + 3 NVAnth_IncompleteRead + 1 ATE + 1 no_content_gap

### dsv4p_nv pexec tier_attempts 6h
| error_type | count |
|---|---|
| pexec_success | 332 |
| pexec_429 | 108 |
| pexec_conn_RemoteDisconnected | 87 |
| NVCFPexecRemoteDisconnected | 20 |
| pexec_SSLEOFError | 13 |
| pexec_empty_200 | 3 |
| 500_nv_error | 2 |
| NVCFPexecTimeout | 1 |

### 关键: 429 在 5 个独立美国 socks5 IP 上均匀分布
| key_idx | pexec_success | pexec_429 | RemoteDisconnected |
|---|---|---|---|
| 0 | 58 | 23 | 24 |
| 1 | 79 | 15 | 13 |
| 2 | 51 | 24 | 17 |
| 3 | 61 | 23 | 19 |
| 4 | 83 | 23 | 14 |

R2082 给 dsv4p 配 5 独立美国 socks5(7900-7904)治连环 429, 但只把连环变均匀, **没降总量**.

### 12h 趋势: dsv4p_nv SR 日间恶化 (非 R2252 引入)
| 小时 | OK | ATE | total | SR |
|---|---|---|---|---|
| 02:00 | 12 | 1 | 13 | 92% |
| 04:00 | 108 | 2 | 111 | 97% |
| 09:00 | 9 | 14 | 23 | 39% |
| 13:00 | 3 | 14 | 17 | 18% |
| 14:00 | 3 | 10 | 13 | 23% |

## 二、根因判断 + ChatGPT 决策

**判断**: NVCF pexec 429 在 5 个独立美国 IP 上均匀分布 → NVCF pexec 按**模型/account**
全局限流, 不按 IP. R2082 换 IP 无效已间接证明.

**ChatGPT 决策 (inject 重登后问到, 桥之前 3 次超时=CDP 会话未登录 cookie 过期)**:
- 判断对: NVCF pexec 429 按模型/account 全局限流不按 IP.
- 优先级表:
  1. **C (本轮)**: 抓 NVCF 429 响应头 (`x-ratelimit-*` / `retry-after`) 确认限流桶维度
  2. **B (下一轮)**: pexec retry policy `on_429:true, max_retry:3, strategy:key_rotate,
     backoff base:2 max:30` — 把 429 从致命错误改成可恢复事件
  3. **D**: `dsv4p_nv_failure_rate` 监控 (5min 窗 429>40% AND retry_exhausted>20% →
     switch glm5_2_nv)
  4. **A (最后)**: `KEY_AUTHFAIL_COOLDOWN_S 60→0` (非主矛盾, HM1 R2257 同款改动)
- 一句话: **HM2 SR 92%→23% 主因不是认证问题, 是 pexec 429 被网关错误地放大成 failure**.
- 顺序不能反: 先 C 抓数据, 再 B 把 429 改可恢复, D 兜底, A 最后.

## 三、改动 (HM2 only, 本轮只加观测)

### nv_gw `/opt/cc-infra/proxy/nv-gw/gateway/upstream.py` (bind-mount)
- 备份: `upstream.py.bak.R2259obs_20260722`
- 位置: `_try_tier_keys` 的 pexec 429 分支 (L748 `elif resp.status == 429:`)
- 加 `NV-PEXEC-429-HDR` 日志: 抓 `resp.headers` 里 ratelimit/retry-after 头 +
  `egress_info_for_key(key_idx)` 确认 IP 维度. 只写日志不动逻辑.
- 语法 `ast.parse` OK. `docker compose restart nv_gw` 加载. `/health` OK.

```python
elif resp.status == 429:
    mark_key_cooling(tier_model, key_idx)
    _log("NV-COOLDOWN", f"tier={tier_model} k{key_idx+1} marked cooling after 429")
    # R2259obs: pexec 429 响应头观测. 目的=确认 NVCF pexec 429 限流维度
    # (按 model/account 全局, 还是按 IP). 抓 x-ratelimit-* / retry-after.
    try:
        _rh = dict(resp.headers) if resp.headers else {}
        _rl_keys = {k: v for k, v in _rh.items() if "ratelimit" in k.lower() or "retry-after" in k.lower() or "x-ratelimit" in k.lower()}
        _eg = egress_info_for_key(key_idx) if "egress_info_for_key" in globals() else (None, None)
        _log("NV-PEXEC-429-HDR", f"tier={tier_model} k{key_idx+1} 429 resp headers: ratelimit/retry={_rl_keys or '(none)'} all={list(_rh.keys())[:12]} egress={_eg}")
    except Exception as _e:
        _log("NV-PEXEC-429-HDR", f"tier={tier_model} k{key_idx+1} header probe failed: {_e}")
```

### ChatGPT 桥修复 (副产物)
- `login_edge.py ask` 连续 3 次 120s 超时 = Edge CDP 会话未登录 (cookie 过期).
  `status` 显示 "Log in / Sign up", `ask` 卡 `_wait_reply` 等(永不来的)回复.
- 修复: `DISPLAY=:99 python3 login_edge.py inject` 注入 committed_cookies
  (25 cookies) 重登 `93921526@163.com` (plan=free, expires 2026-10-20).
- 桥本身活着, 只是登录态丢.

## 四、验证 (改后必有验证)

- 语法: `python3 -c "import ast; ast.parse(...)"` OK
- restart: `docker compose restart nv_gw` → Started + `/health` OK
- shadow 验证: **待 1-2h 抓 6-14 个 `NV-PEXEC-429-HDR` 样本**, 看是否有
  `x-ratelimit-*` / `retry-after` 头, 确认限流桶维度 (模型/account vs IP).
- 回滚: `cp upstream.py.bak.R2259obs_20260722 upstream.py && docker compose restart nv_gw`

## 五、参数表

| 参数 | 值 (HM2) | 本轮改动 |
|---|---|---|
| TIER_TIMEOUT_BUDGET_S (dsv4p) | 180 | 不变 |
| KEY_AUTHFAIL_COOLDOWN_S | 60 | 不变 (A 步最后才动) |
| KEY_COOLDOWN_S | 60 | 不变 |
| NV-PEXEC-429-HDR 观测点 | 新增 | 只写日志不动逻辑 |

## 六、未做 (留下一轮, 数据驱动)

- **B**: pexec retry policy (on_429:true, max_retry:3, key_rotate, backoff base:2 max:30)
  — 等 C 抓到限流维度确认后再定 key_rotate vs 别的
- **D**: dsv4p_nv_failure_rate 降级回退 glm5_2_nv (5min 窗 429>40% AND retry_exhausted>20%)
- **A**: KEY_AUTHFAIL_COOLDOWN_S 60→0 (最后, 非主矛盾)
- R2258 P2: nv_gw peek 覆盖 cc4101 直连 header 路径 (优先级低于 dsv4p 429)

## 七、铁律遵守

- 改前必有数据: 6h + 12h 采完, dsv4p_nv pexec 429 日间恶化是真病. ✅
- 改后必有验证: 语法 OK + restart + /health OK, shadow 验证待抓样本. ✅
- 聚焦 nv_gw: 只动 nv_gw upstream.py. ✅
- 写入仓库: 本 round 文件 commit + push. ✅
- 只改 HM2 不改 HM1: HM2 only. ✅
- UTF-8 no BOM: `open(encoding="utf-8")`. ✅
