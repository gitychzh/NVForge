# R1051 cc2 NOP — cc2 primary 100% clean (111/111), scoped errors 0; bad 2 hermes (zombie_empty_completion×2); fallback 0 (0/184); 159th clean round (R893-R1051)

日期: 2026-08-07 CST
性质: NOP 巡检轮 (不改码)

## 结论
cc2 主链路 (caller=cc4101-primary) 连续第 **159** 轮 100% SR 干净 (R893-R1051)。
主链专属错误 0 rows, fallback 0 次。本轮 2 bad 全属 **hermes** 越界宿主, 与主链 host 分离干净。

## 数据 (注入轮前链路分析 18:28 CST + /health 复核)
- 30min cc4101-primary (主 nv_gw:40006) = **111/111 全 200 = 100% SR, 0 bad**
  (注入: cc4101-primary|dsv4f0731_nv|200|111)。
- 主链专属错误 (caller=cc4101-primary, status!=200) = **0 rows**。
- nv_requests 总 bad = 2 条: zombie_empty_completion ×2 (502),
  链路总览 caller×model×status 判定全属 **hermes** (hermes|dsv4f0731_nv|502|2, cc4101-primary 无任何非 200)。
- 30min 按模型总 SR dsv4f0731_nv = 98.9% (182/184), 差异 2 条 bad 全属 hermes。
- 30min cc_requests = **0 次 fallback (0.0%)** (fallback 发生率 f|184, 注入总览)。
- nv_tier_attempts (30min): k0-k4 全 pexec_success (22/23/21/21/24) — 主链首代=dsv4f0731_nv,
  无 tier 层错误, 无 key 疲劳。
- buffer/wait/keymanager 日志 (注入): 无 — 零吸收需要, 全 request attempt=1 直接成功。
- 容器 (/health 复核): nv_gw Up 15h, cc4101 Up 15h, nv_gw_stable Up 5d, /health 40006/4101/40066 全 200。
  当前首代模型 dsv4f0731_nv, 无 tier 降级。

## 关键判断
连续 **159** 轮稳态 (R893-R1051)。主链 111/111 全 200, 专属错误 0 行, fallback 0 (0.0%), buffer 零重试。
本轮 window 内混入 hermes 越界 2 bad (zombie×2), 链路总览按 caller 判定全属 hermes,
与主链 host 分离干净; 主链无根因可查; 参数处于稳态, 无可调。
**不改码**: 主链 SR 100% + 专属错误 0 + fallback 0 + buffer 零重试, 无优化需求。

## 下一步
- 保持 NOP 观察, 主链 dsv4f0731_nv 为首代, 无需参数改动。
- 持续确认 hermes 越界 bad (zombie_empty_completion/502) 与主链 host 分离 (caller JOIN)。
- 关注偶发 RemoteDisconnected 是否演成持久疲劳 (若单 key 连续多轮 100% 失败再考虑 KEY_FID_BIND 换 fid)。