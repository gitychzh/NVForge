# R1067: 打破 45 轮 NOP — 将硬编码 CONN_ERR_FAST_BREAK=2 改为 env 可调并设为 5

> 时间: 2026-08-06 13:45 BJT (05:45 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **改动** — 首个非 NOP 轮。R1021-R1066 连续 45 轮 NOP 判定"模型特异性无 lever",
>   但本轮发现被 NOP 框架遗漏的结构性 lever: `CONN_ERR_FAST_BREAK=2` 硬编码于
>   upstream.py, 使 tier 在仅 2 次连续 RemoteDisconnected 后即放弃全部 5 key 循环,
>   白白浪费 180s budget 内本可命中的健康 key。

## 1. 背景 (改前必有数据)

### 30min 窗口 (pre-run 注入) — nv_requests (tier_model=dsv4f0731_nv)
- 总量 29, 200=9, 失败=20, **SR=31.0%**
- Avg 105760ms, p50 101328ms, p95 245804ms
- 429: 0 计数
- upstream_type: nvcf_pexec 25 (200=9, avg=83565ms), ms_fallback 3 (200=0, avg=239956ms),
  nv_integrate 1 (200=0, avg=258057ms)
- finish_reason: tool_calls=6, stop=3

### 错误分类 (30min, pre-run)
| error_type | count | avg_ms |
|---|---|---|
| all_tiers_exhausted | 12 | 107314 |
| buffer_exhausted | 4 | 244481 |
| zombie_empty_completion | 3 | 11834 |
| client_gone_during_flush | 1 | 210378 |

### per-key 200 延迟 (30min) — 关键证据: 每个 key 都有成功
| key | 200 | avg_ms | max_ms |
|---|---|---|---|
| 0 | 3 | 75288 | 139175 |
| 1 | 2 | 77660 | 113785 |
| 2 | 1 | 28610 | 28610 |
| 3 | 1 | 21386 | 21386 |
| 4 | 2 | 62148 | 81944 |

→ **全部 5 key 在 30min 内都有 200 成功**。断连是间歇性, 非永久性。

### attempt 层错误 (2h, 本轮直接查询 nv_tier_attempts)
| error_type | count | avg_ms | max_ms |
|---|---|---|---|
| NVCFPexecRemoteDisconnected | 137 | 43495 | 88387 |
| empty_200 | 10 | - | - |
| 504_nv_gateway_timeout | 12 | - | - |
| 529_nv_overloaded | 10 | - | - |
| NVCFPexecTimeout | 5 | 40883 | 58995 |

- **137/180 (76%) = NVCFPexecRemoteDisconnected**, avg 43.5s, max 88s
- 0 429 计数; 错误跨全 key 分散 (k0:23, k1:32, k2:21, k3:28, k4:32)
- 6h 趋势: SR 40-55% 每小时, 持续性而非瞬时

### 关键结构性发现 (本轮代码审查)
`CONN_ERR_FAST_BREAK` 在 upstream.py 三处**硬编码 = 2** (行 599/1002/1393):
```python
CONN_ERR_FAST_BREAK = 2
```
**含义**: 同一 tier 内连续 2 次连接错误 (RemoteDisconnected) 即触发 fast-break, 直接放弃
剩余 key 循环, 返回 `all_tiers_exhausted`。对比:
- `NVU_PEXEC_TIMEOUT_FASTBREAK=3` (env 可调)
- `NVU_EMPTY_200_FASTBREAK=3` (env 可调)
- `CONN_ERR_FAST_BREAK=2` (**硬编码, 不可调**)

**预算数学**: TIER_TIMEOUT_BUDGET=180s, 但 fast-break 在 ~86s (2×43.5s avg disconnect)
即触发, 只试了 2 个 key 就放弃, 留下 ~94s 未用。而 30min 数据证明 5 key 全部间歇性成功
→ 提高 CONN_ERR_FAST_BREAK 让 tier 循环全部 5 key, 最大化命中瞬时健康 key 的概率。

**为什么 R1021-R1066 的 NOP 结论遗漏此 lever**: 先前判定"错误跨全 key 分散 → 无 key
分配可调 / 无 429 → 无冷却可调 / 三协议全败 → 无路由可调", 但**未检查连接错误 fast-break
是否硬编码过激**。硬编码 2 意味着 tier 在间歇性断连场景下过早放弃, 这正是可调 lever。

## 2. 决策: 修改 (第 46 轮, 首个非 NOP)

**一次只改一个参数 (铁律)**: 仅将 `CONN_ERR_FAST_BREAK` 从硬编码 2 改为 env 可调
(默认 2 保持向后兼容), 并对本容器设 `NVU_CONN_ERR_FAST_BREAK=5`, 让 tier 循环全部
5 key 后再放弃。

### 修改 1: upstream.py (bind-mounted, 三处)
```python
# 旧
CONN_ERR_FAST_BREAK = 2
# 新
CONN_ERR_FAST_BREAK = int(os.environ.get("NVU_CONN_ERR_FAST_BREAK", "2"))
```
- 默认 2 保持不变 → nv_gw/nv_gw_stable 等其它容器行为不变 (向后兼容)
- 备份: `upstream.py.bak.R1016`

### 修改 2: docker-compose.yml (仅 dsvf0731_nv40666 块)
```yaml
- NVU_CONN_ERR_FAST_BREAK=5  # R1016: 76% NVCFPexecRemoteDisconnected, 2-consec fast-break 太激进, 全 5 key 循环再放弃
```

### 预期效果
- 间歇性断连下, tier 不再在 2 次失败后放弃, 而是遍历全部 5 key (每次 ~43s 断连)
- 30min 数据证明 5 key 全有成功 → 180s budget 内 (5×43s=215s 略超, 但好 key 常在
  前 3-4 个命中, 实际 ~129-172s), 显著提高命中健康 key 概率
- 预期 all_tiers_exhausted 下降, SR 提升; 若某 key 端口持续坏, keymgr 连接冷却
  (NVU_KEYMGR_CONN_BASE_COOLDOWN=30, MAX=60, LONG=120) 仍保护不反复烧同 key

### 风险
- 若 5 key 全部持续断连, 会多烧 ~86s 预算才放弃 (2→5 次), 但 TIER_TIMEOUT_BUDGET=180
  上限保护, 且 30min 数据证明非全部持续坏
- 源码改 bind-mounted upstream.py, nv_gw/nv_gw_stable 共享该文件但默认 2 不变, 无副作用

## 3. 验证

- [x] `docker compose config` OK (无 YAML 错误)
- [x] `python3 -c "import ast; ast.parse(...)"` 语法 OK
- [x] 容器 recreate 成功 (compose up -d dsvf0731_nv40666)
- [x] `/health` = {"status": "ok", ...} (端口 40666)
- [x] `docker exec dsvf0731_nv40666 env | grep CONN_ERR_FAST_BREAK` = `NVU_CONN_ERR_FAST_BREAK=5`
- [x] 备份 `upstream.py.bak.R1016` 存在

## 4. 当前状态 (30min, 改动前基线)

- 30min SR: 31.0% (9/29)
- Avg/P50/P95: 105760 / 101328 / 245804 ms
- 错误分布: all_tiers_exhausted=12, buffer_exhausted=4, zombie_empty_completion=3,
  client_gone_during_flush=1
- Fallback: hm4104 持续 fallback (PRIMARY-FAIL-STREAM 502 after 126730ms → FALLBACK-STREAM)
- upstream: nvcf_pexec 25/200=36%, ms_fallback 3/200=0%, nv_integrate 1/200=0%

## 5. 上次修改效果 (R1066 NOP)

R1066 无参数修改 (NOP, 第 45 轮)。SR 从 R1065 的 39.5% 略降至 38.7% (6h), 风暴持续。
本轮为 46 轮以来首个非 NOP 改动, 针对 NOP 结论遗漏的硬编码 fast-break lever。

## 6. 下一步建议

- 观察 30min 后: 若 all_tiers_exhausted 显著下降且 SR 回升 → CONN_ERR_FAST_BREAK 调优
  方向正确, 可考虑微调 (如 4 或结合 KEY_COOLDOWN)
- 若 SR 无改善 → 确认 fast-break 非主要瓶颈, 回滚此改动 (restore bak.R1016) 并回到
  NOP 框架重新审视
- 始终: 若 NVCF 侧恢复 (glm5_2_nv 与 dsv4f0731_nv SR 趋同), 此改动可保留 (默认 2 无副作用)