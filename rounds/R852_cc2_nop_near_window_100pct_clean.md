# R852 cc2 — NOP 巡检轮 (近窗 100% 净, 不改码)

日期: 2026-08-07 04:23 CST
主机: HM2 (100.109.57.26) | 容器: nv_gw (Up 53min), cc4101 (Up 27min), dsv4p_nv40066 (Up 2d)

## 结论
**最近 15min cc4101-primary SR = 100% (57×200, 零错误).** 不改码 (NOP).

## 本轮数据 (04:23 CST, 实时拉取, DB UTC=DTS)

**30min 窗口 cc4101-primary:** 112×200 / 5 错误 (SR=95.7%)
- 错误全部集中在窗口早期 `19:53-19:55 UTC`:
  - 19:53 `buffer_exhausted×3` (avg 170s)
  - 19:54-19:55 `client_gone_pre_attempt×2` (avg 29s)
- 此刻 ~20:23 UTC; **最近 20min (20:03+) 逐分钟全 200, 零错误** (57×200)

**nv_gw buffer 日志 (近15min):** 全部走 dsv4f0731_nv, attempt=1/5 一次成功,
7-13s, verdict=success_tool_call, 零 buffer_exhausted, 零 WAIT. 完整样例:
- 04:22:02 start → attempt=1 → 04:22:10 success_tool_call (7s, 8180b flush)
- 04:22:10 start → attempt=1 → 04:22:24 success_tool_call (13s, 19247b flush)

**tier 错误 (30min):** `all_tiers_exhausted×5` (529_nv_overloaded + NVCFPexecRemoteDisconnected
+ empty_200 混合) 均为窗口早期 glm5_2_nv 短暂疲劳; 多 tier round-robin + fail-fast 已吸收.

## 判稳
- 近窗 15min SR=100%, 零新错误 → **NOP**, 修复链充分, 不改码.
- 30min 残留 5 错误全为 19:53-55 早期风暴旧痕 (同 R844-R851 同型, cc4101 重启后短暂波动).
- 修复链: glm5_2_nv 疲劳 → cc4101 动态 primary pinned dsv4f0731_nv → 1-7-13s 一次成功.

## 健康
- cc4101 /health: ok, primary=dsv4f0731_nv
- nv_gw /health: ok, passthrough, 5 keys, nvcf_pexec_models 含 dsv4f0731_nv/glm5_2_nv
- fallback (ms_gw 层): 近窗 0 次

## 下一步
- 长期观测; glm5_2_nv 冷却退去后看 cc4101 primary 是否自动回归 glm5_2_nv (主链路目标).
- 不改码.