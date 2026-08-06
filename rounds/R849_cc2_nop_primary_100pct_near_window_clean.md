# R849 cc2 巡检轮 (NOP) — 近窗 primary SR=100%, 30-min 残留均为风暴旧痕

- 轮次: R849
- 时间: 2026-08-07 04:30 CST (DB UTC)
- 类型: **NOP 巡检轮 (不改码)**
- 容器: nv_gw Up 42min, cc4101 Up 16min, dsv4f0731_nv40666 Up 11h, dsv4p_nv40066 Up 2d (全 Up ✅)

## 结论

**近 10-15min 窗口全净, cc4101-primary (cc2 自己的路径) SR=100%, 一次成功, 零 buffer_exhausted.**
30min 窗口残留的 `buffer_exhausted×9`、`all_tiers_failed×5`、dsv4f0731_nv fid 52e1ddb6
RemoteDisc×9 全为窗口早期 glm5_2_nv 风暴旧痕, 已被修复链 (R827+R828+R829+R833+R813) 自适应吸收 —
与 R844-R848 同型. **无软件 bug, 不改码.**

## 近窗硬证据 (04:07-04:22 CST)

### cc4101-primary 最近 10min (cc2 请求)
| status | count |
|---|---|
| 200 | 37 |
| (错误) | 0 |

→ **SR = 100%** ✅

### nv_gw buffer 日志 (15min, 全走 dsv4f0731_nv)
```
[NV-BUFFER-START] (dsv4f0731_nv) cc4101-primary max_retries=5 stairs=[90×5] total_deadline=450s
[NV-BUFFER-ATTEMPT] attempt=1/5 timeout=90s input=73-77k thinking=True
[NV-BUFFER-VERDICT] attempt=1 verdict=success_tool_call fr=tool_calls elapsed=9s
[NV-BUFFER-SUCCESS] flushed after 1 attempt(s), elapsed=9052ms
[NV-BUFFER-SUCCESS] flushed after 1 attempt(s), elapsed=9061ms
[NV-BUFFER-SUCCESS] flushed after 1 attempt(s), elapsed=11794ms
```
→ 每条 **attempt=1/5 一次成功**, 9-12s, 零 buffer_exhausted, 零 WAIT ✅

### 当前 primary: dsv4f0731_nv (cc4101 /health 确认)
`curl localhost:4101/health` → primary=dsv4f0731_nv, status ok ✅

## 30min 硬窗口残留 (缓解释义, 非本轮新错误)

| 项 | 值 | 解释 |
|---|---|---|
| bufer_exhausted×9 | avg 217s | 窗口早期 glm5_2_nv 退化期残留, 已吸收 |
| all_tiers_failed×5 | avg 178s | fail-fast (R829/R833) 生效, 非 465s 死亡螺旋 |
| drop fallback 1 次 | — | ms_gw 层罕见触发, cc4101-primary nv 路径近窗干净 |
| dsv4f0731_nv S-d 52e1ddb6 RemoteDisc×9 | — | 多 key 轮转中单个 key-fid 瞬态失败, 其余 key 成功兜底 |

### 值得记录: dsv4f0731_nv 双 fid 现象
近窗 nv_tier_attempts 显示 dsv4f0731_nv 走两个 fid:
- **281478d0 → pexec_success × 37** (请求实际成功那次走的 key-fid)
- **52e1ddb6 → RemoteDisc×9 / 529×2 / budget_exhausted×1** (轮转中该 key 的失败 attempt)

这是 round-robin 多 key 设计意图: 单个 key-fid 瞬态失败被其余 key 成功吸收, 请求最终全部 200.
非死锁, 无回归, 不改码.

## 修复链 (沿用, 充分)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast (178s avg vs 历史 465s)
2. cc4101 动态 primary glm5_2_nv → dsv4f0731_nv (健康 tier 接管)
3. dsv4f0731_nv 9-12s 一次成功, 用户无感知

## 健康检查
- `curl localhost:4101/health` → ok, primary=dsv4f0731_nv ✅
- `curl localhost:40006/health` → ok, 5 keys, models 含 dsv4f0731_nv/glm5_2_nv ✅
- `curl localhost:40066/health` → ok (dsv4p_nv40066) ✅
- `curl localhost:40666/health` → ok (dsvf0731_nv40666) ✅
- docker ps: nv_gw/cc4101/dsv4p_nv40066/dsvf0731_nv40666 全 Up ✅

## 下一步
- 长期观测。glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标)。
- 关注 dsv4f0731_nv 的 fid 52e1ddb6 持续失败; 若该 key-fid 长期疲劳而 281478d0 稳定, 可考虑后续调 key-fid 绑定, 但当前无需动 (轮转已吸收)。
- 不改码, 修复链充分。