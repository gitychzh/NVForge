# R1070: 回滚 dsv4f0731_nv tier budget 220→180 — budget 非绑定约束, R1069 无收益

> 时间: 2026-08-06 17:1x BJT (09:1x UTC)
> 容器: dsvf0731_nv40666 (端口 40666, HM2, DeepSeek V4 Flash 0731 via NVCF)
> 状态: **改动** — 回滚 R1069 的 budget 放宽。R1069 (180→220) 未带来 SR 改善, 且数据证明
>   budget 不是绑定约束 (fast-break=5 先耗尽 key), 按 R1069 决策规则回滚并给出根因。

## 1. 背景 (改前必有数据)

### R1069 修改 (上轮)
- `NVU_TIER_BUDGET_DSV4F0731_NV` 180→220s, 预期让 fast-break=5 遍历全 5 key 提高命中率
- 依据: all_tiers_exhausted=6 全在 ~180s budget cap, 5×43.5s=217s>180 第 5 key 被 cut

### 本轮当前数据 (30min pre-run + 补充查询)
- **30min SR=53.8% (50/93, 1h 窗口)** — 较 R1069 基线 58.8% 未升反降
- 错误: all_tiers_exhausted=11, buffer_exhausted=9, zombie_empty_completion=7, stream_absolute_cap=1
- **tier_attempts 30min**: NVCFPexecRemoteDisconnected=35, empty_200=21, NVCFPexecTimeout=6,
  504_nv_gateway_timeout=5, 529_nv_overloaded=3 → **70 个上游错误, 跨全 5 key 分散**
- per-key 200: k0=7, k1=8, k2=3, k3=12, k4=4 (全部 key 有成功, 也全部有失败)

### 关键证据 (本轮改动依据)
1. **budget 非绑定约束**: key_cycle_details 显示 ATE 在 ~96-180s 内已耗尽 4-5 key (全失败),
   budget 220s 根本没被烧满就 fail。fast-break=5 先耗尽 key, budget 是冗余上限。
2. **R1069 budget 放宽无收益**: 1h SR 58.8%→53.8%, budget 不是瓶颈。按 R1069 自设规则回滚。
3. **根因是 NVCF function 专属劣化**: glm5_2_nv 近 1h tier_attempts 错误 = **0**,
   而 dsv4f0731_nv (deepseek-v4-flash 0731) 70 错误。非链路/代理问题, 是 NVCF 该 function 侧不稳。
4. **empty_200 + RemoteDisconnected 风暴**: 全 5 key 同时劣化, 非单 key 问题, 无 key 冷却 lever 可解。

## 2. 决策: 回滚 (budget 恢复 180)

**仅回滚 `NVU_TIER_BUDGET_DSV4F0731_NV` 220→180s** (恢复 R1068 基线, 避免无谓的长等待)。

- 旧: `NVU_TIER_BUDGET_DSV4F0731_NV=220`
- 新: `NVU_TIER_BUDGET_DSV4F0731_NV=180`
- 预期: 失败请求在 fallback 前少烧 ~40s budget (fast-break 已先耗尽 key, 此改动降低 fallback 延迟)
- 风险: 无 (fast-break=5 遍历 5 key 在 180s 内通常足够; 220s 是冗余)

## 3. 验证

- [x] `sed` 修改 `docker-compose.yml` 行 296 → `=180`
- [x] `docker compose up -d dsvf0731_nv40666 --no-deps --force-recreate` 成功
- [x] `docker exec dsvf0731_nv40666 env | grep NVU_TIER_BUDGET_DSV4F0731_NV` = 180
- [x] `/health` = {"status": "ok", ...} (端口 40666, 5 keys)
- [x] 容器 Up (recreate 后)

## 4. 当前状态 (基线, 30min)

- 30min SR: **53.8%** (50/93, 1h) — R1069 基线 58.8%, 下滑
- 错误分布: all_tiers_exhausted=11, buffer_exhausted=9, zombie_empty_completion=7,
  stream_absolute_cap=1, client_gone_during_flush=1
- Fallback: hm4104 持续 PRIMARY-FAIL-STREAM → FALLBACK（ms_gw 也 timeout 70s）
- upstream: nvcf_pexec 53/200=64%, ms_fallback 7/200=0%, nv_integrate 2/200=0%

## 5. 上次修改效果 (R1069)

| 指标 | R1069 基线 | 当前 (R1070 pre) |
|---|---|---|
| 30min/1h SR | 58.8% | 53.8% |
| 逐小时 ATE | 16 (06:00) | 31 (08:00) |
| 上游错误(tier_attempts) | RemoteDisconnected 56 | RemoteDisconnected 35+empty200 21 |

→ **budget 放宽 180→220 无正向收益, 已回滚。**

## 6. 根因结论与下一步建议

- **根因**: NVCF deepseek-v4-flash 0731 function (`52e1ddb6-...`) 侧临时劣化, 全 5 key 同时
  出现 empty_200 + RemoteDisconnected + timeout 风暴。这是 NVCF 上游问题, 非本容器参数可解。
- **下一步**: 观察 NVCF 侧是否自然恢复 (比对 glm5_2_nv 持续 0 错误)。若 dsv4f0731_nv 持续
  >2h SR<60% 且 empty_200 风暴不散, 考虑切换 primary 到 dsv4f_nv (04 版本) 或评估
  NVU_EMPTY_200_FASTBREAK 3→1 (空 200 立即判 fail, 加速 key 轮转, 减少烧 budget)。
- 不推荐改 KEY_COOLDOWN / CONN_COOLDOWN — 这是全 key 同时劣化, 非单 key 问题。