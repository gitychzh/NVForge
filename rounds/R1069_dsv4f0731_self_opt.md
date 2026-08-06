# R1069: 放宽 dsv4f0731_nv tier budget 180→220s — fast-break=5 遍历全 5 key

> 时间: 2026-08-06 15:20 BJT (07:20 UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Pro via NVCF)
> 状态: **改动** — 应用 R1068 计划的下一步 lever。R1067 (CONN_ERR_FAST_BREAK 2→5) 已被
>   R1068 验证为正向 (SR 31→46%, ATE 减半), 本轮升级绑定约束: tier budget。

## 1. 背景 (改前必有数据)

### R1068 结论 (上上轮效果确认)
- R1067 改动 (CONN_ERR_FAST_BREAK 2→5) 效果确认: 30min SR 31%→47%, 逐小时 ATE 35→16
- R1068 明确给出下一步: `NVU_TIER_BUDGET_DSV4F0731_NV` 180→~220s

### 当前数据 (本轮直接查询, nv_tier_attempts 1h)
| error_type | count | avg_ms | max_ms |
|---|---|---|---|
| NVCFPexecRemoteDisconnected | 56 | 41740 | 85785 |
| NVCFPexecTimeout | 16 | 39077 | 91729 |
| 529_nv_overloaded | 15 | - | - |
| empty_200 | 10 | - | - |

- 0 429; RemoteDisconnected 仍为主 (56/97, 58%), 跨全 5 key 分散 (k0:9, k1:10, k2:7, k3:12, k4:18)

### 30min 窗口 (pre-run 注入)
- 总量 34, 200=20, **SR=58.8%** (较 R1068 47.1% 再升)
- nvcf_pexec SR=74% (20/27), ms_fallback 0% (0/7)
- 错误: all_tiers_exhausted=6 (avg 180072ms), buffer_exhausted=7 (ms_fallback), zombie_empty_completion=1
- **per-key 200: k0=4, k1=7, k2=4, k3=5, k4 无记录** — 全部 key 有成功
- key_cycle_429s: k0=22, k1=9, k2=3

### 关键证据 (本轮改动依据)
1. **all_tiers_exhausted=6 全部 avg≈180s** = 精确命中 180s budget 上限 → tier 在 budget 被 cut
2. **预算数学**: 5 key × 43.5s (RemoteDisconnected avg) = 217s > 180s budget → 第 5 key 被错过
3. R1067 已设 fast-break=5 (遍历全 5 key), 但 180s budget 成为新绑定约束 → 放宽 budget 让
   fast-break=5 真正生效
4. **ms_fallback 本窗 0% (0/7)** → 更多 primary budget 不会伤害 fallback 路径 (fallback 反正失败)

## 2. 决策: 修改 (一次只改一个参数)

**仅改 `NVU_TIER_BUDGET_DSV4F0731_NV` 180→220s** (dsv4f0731_nv 专属 tier budget,
不影响其它 model/容器)。

- 旧: `NVU_TIER_BUDGET_DSV4F0731_NV=180`
- 新: `NVU_TIER_BUDGET_DSV4F0731_NV=220`
- 预期: tier 在 180s→220s 内可遍历更多 key (5 key 全试需 ~217s), 提高命中瞬时健康 key
  概率, 降低 all_tiers_exhausted
- 风险: 若 5 key 全连续坏, 失败请求 fallback 前多烧 ~40s; 但 ms_fallback 本窗 0% 成功,
  权衡可接受

### 验证代码路径 (改前确认)
- `upstream.py` 三处 `os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}")` 在请求
  处理路径内读取 → 属 request-time hot-reload 变量, recreate 后生效
- 仅改 compose env, 未改源码 (bind-mounted upstream.py 无需改)

## 3. 验证

- [x] `docker compose config --quiet` = CONFIG_EXIT=0 (无 YAML 错误)
- [x] `docker compose up -d dsvf0731_nv40666 --no-deps --force-recreate` 成功
- [x] `docker exec dsvf0731_nv40666 env | grep NVU_TIER_BUDGET_DSV4F0731_NV` = 220
- [x] `/health` = {"status": "ok", ...} (端口 40666)
- [x] 容器 Up (recreate 后)

## 4. 当前状态 (recreate 前基线, 30min)

- 30min SR: **58.8%** (20/34) — 较 R1068 47.1% 再升
- Avg / P50 / P95: 131885 / 115994 / 299538 ms (fallback 混合拖高)
- 错误分布: all_tiers_exhausted=6, buffer_exhausted=7 (ms_fallback), zombie_empty_completion=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK-STREAM (模型断裂连)
- upstream: nvcf_pexec 27/200=74%, ms_fallback 7/200=0%

## 5. 上次修改效果 (R1067)

R1067 (CONN_ERR_FAST_BREAK 2→5) 持续正向:
| 指标 | R1067 基线 | R1068 | 当前 (R1069 pre) |
|---|---|---|---|
| 30min SR | 31.0% | 47.1% | **58.8%** |
| 逐小时 ATE | 35 | 16 | 16 (06:00) |
| 逐小时 SR | 32.1% | 46.2% | ~48% (06:00) |

→ 连续 2 轮正向, fast-break=5 方向确认正确。

## 6. 下一步建议

- 观察 30min: 若 all_tiers_exhausted 下降且 SR 保持/上升 → budget 放宽方向正确
- 若 SR 无改善 → 说明 budget 非主要瓶颈, 回滚至 180 评估
- 持续比对 glm5_2_nv SR (R1068 86.7%): 若趋同说明 NVCF 侧整体恢复; 此 lever 为
  dsv4f0731_nv 专属, 不影响其它容器
- 关注 key_cycle_429s (k0=22 偏高): 若再升, 下一轮评估 KEY_COOLDOWN_S 30→更高