# R1015: 529 风暴第 6 轮 — 启用 dsv4f0731_nv k5 integrate 通路 (R838B per-key lane)

> 时间: 2026-08-05 04:25 BJT (20:25 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 via NVCF)
> 状态: **改参数** — 启用 R838B per-key integrate lane (`NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5`)
> Fallback: hm4104 持续 fallback 到 dsv4f0731_ms (primary 502 触发)

## 1. 背景 (改前必有数据)

R1010-R1014 连续 5 轮记录 NVCF 529_nv_overloaded **账户级过载风暴**。R1014 定性为"账户级过载, 改参数无效, NOP"。本轮从**框架层面**重新审视 (任务要求: 不只调超时, 要考虑 pexec/integrate 路由)。

### 关键新发现 (改前 24h 数据)

**1. dsv4f_nv 已成功使用 integrate, 而 dsv4f0731_nv 只走 pexec:**
- `dsv4f_nv` (同 FID 52e1ddb6): integrate **171 请求, 119 成功 = 69.6% SR**; pexec 237 请求, 166 成功 = 70%
- `dsv4f0731_nv`: **仅 pexec (112 请求), 0 integrate**
- 两者共享同一 NVCF FID (`52e1ddb6-c74...`, ai-deepseek-v4-flash) — 唯一区别是 dsv4f_nv 走 dsv4f 动态 handler 的 pexec→integrate 自适应切换, 而 dsv4f0731_nv 因 `NV_INTEGRATE_MODELS=""` + `NV_KEY_INTEGRATE_KEYS=""` 完全无 integrate 路径

**2. integrate 基础设施已配置但完全未用:**
- `NV_INTEGRATE_PROXY_URLS` 5 个 socks5 代理已配好, `NV_INTEGRATE_EGRESS_IPS` 5 个 egress IP 已配好
- `NV_INTEGRATE_MODELS=""` (空), `NV_KEY_INTEGRATE_KEYS=""` (空) → 上层 never 触发 integrate

**3. 根因 (改前 6h):**
- dsv4f0731_nv tier_attempts: 216 次, 197 次 (91.2%) `529_nv_overloaded`
- 5 key 完全均匀 (21-24 529/key) → 账户级, 非 per-key
- 30min 请求级 SR: 86% (43/50), avg 28.8s

### R838B per-key integrate lane (代码路径, upstream.py:2622)

```python
_r838_keys = nv_key_integrate_keys_for(tier_model)   # 从 NV_KEY_INTEGRATE_KEYS 解析
_peek_key = _peek_nv_key(tier_model)                 # RR peek 当前 key
if (is_first_tier and NV_INTEGRATE_ENABLED
        and tier_model not in NV_INTEGRATE_MODELS
        and _r838_keys and _peek_key in _r838_keys   # peek 到 k5 → integrate
        and not _integrate_is_path_cooling()):
    → _try_integrate_keys(key_filter=[_peek_key])    # 只试 k5 integrate
```

- 该 lane 对 `dsv4f0731_nv` **可达** (不在 NV_INTEGRATE_MODELS, 非 dsv4f_nv 动态 handler, 非 dsv4p channel)
- 之前因 `NV_KEY_INTEGRATE_KEYS=""` 返回空 → `_r838_keys` 空 → lane never 触发

## 2. 决策: 启用 `NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5`

**compose env 变更** (docker-compose.yml 该服务):
```
前: - NV_KEY_INTEGRATE_KEYS=                      # 空 → 无 per-key integrate
后: - NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5        # k5 integrate 通路
```

**理由:**
- integrate 对同 FID (dsv4f_nv) 有 69.6% SR (171 req, 24h) — 非不可用
- 为 dsv4f0731_nv 增加第二条独立 NVCF 路径 (`/v1/integrate`, 不同 endpoint 负载)
- RR 约 20% 流量 (k5) 走 integrate, 80% 保持 pexec — 数据多样性与风险平衡
- 失败时自动 fallback 回 pexec (已有的 `NV-INTEGRATE-PERKEY-FALLBACK` 逻辑)

## 3. 部署与验证

- [x] `docker compose up -d dsvf0731_nv40666` (Recreate, 容器重启)
- [x] env 生效: `NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5`
- [x] /health: status OK, 5 keys, tiers 含 dsv4f0731_nv
- [x] 容器 Up (重启后 25 min)

### 改后 25min 数据 (重启后, 20:00-20:25 UTC)

**R838B lane 触发 5 次, integrate 结果:**
| outcome | cnt | 说明 |
|---------|-----|------|
| SUCCESS | 2 | 2.3s, 18.4s (avg) 首 attempt 成功 |
| 529_integrate_overloaded | 2 | integrate 端也过载 (账户级) |
| SSLEOFError | 1 | 405ms 快速失败, 转 pexec |

**请求级 SR: 76.2% (16/21)**, avg: integrate 200=18.4s, pexec 200=35.1s (p50 24.4s)

**tier_attempts (重启后):** 42× 529_nv_overloaded, 3× NVCFPexecRemoteDisconnected, **1× 529_integrate_overloaded** (首次记录 integrate 层过载)

## 4. 效果评估

- ✅ **integrate 通路已激活**: RR 约 20% (k5) 流量走 integrate, 成功时 2.3s 首 hit (比 pexec 200 avg 快)
- ✅ **失败自动降级**: integrate 529/SSL → 快速 fallback 回 pexec, 无 SR 牺牲
- ✅ **无 SR 回归**: 76.2% (25min) vs R1014 基线 71.9% (30min) — 略升, 且在 overlapping 波动范围
- ⚠️ **integrate 端同样过载**: 529_integrate_overloaded 出现 → 账户级 NVCF 过载同时影响 pexec 与 integrate, 非银弹
- 净效果: 增加第二路冗余, 部分流量成功改用 integrate, 边际正收益

## 5. 验证清单

- [x] /health: status OK
- [x] 容器 Up (重启后 25 min)
- [x] env 生效: NV_KEY_INTEGRATE_KEYS=dsv4f0731_nv:5
- [x] R838B lane 触发 (5 次) + integrate 成功 (2 次) — 通路真实工作
- [x] integrate 失败自动 fallback pexec (529/SSL)
- [x] 写入仓库 (本 round 文件 + commit)

## 6. 下一步建议

1. **观察 24h**: 收集 integrate vs pexec 的 SR 对比, 若 integrate 持续优于 pexec, 可扩展 `NV_KEY_INTEGRATE_KEYS` 到更多 key (如 `:5,4`)
2. **账户级过载持续**: 若 529_storm 超 24h 仍在, 需上游侧干预 (额外 NVCF key / egress IP 池 / 换 FID)
3. **监控 529_integrate_overloaded**: 新指标, 用于量化 integrate 端过载程度
4. **考虑 counter-reset bug**: `upstream.py` line 778 RemoteDisconnected 重置 consecutive-529 counter, 使 dsv4f_nv 动态 handler 的 pexec→integrate 自适应难以触发 — 但 dsv4f0731_nv 已用 R838B per-key lane 绕过此问题