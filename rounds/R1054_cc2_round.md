# R1054 — cc2 NOP 巡检轮 (HM2 nv_gw)

## 决定: NOP 不改码 — cc2 主链连续第 162 轮 100% 干净

## 依据 (注入轮前链路分析 2026-08-07 18:39 CST + /health 复核 + caller JOIN)

- 30min cc4101-primary (主 nv_gw:40006) = **108/108 全 200 = 100% SR, 0 bad**
  (caller JOIN: cc4101-primary|200|108, 无任何非 200, scoped 主链专属错误 = 0 rows)
- nv_requests 总 bad = 2 (zombie_empty_completion ×2, 502, avg_dur 3047ms), 全属 hermes 越界宿主
  (caller JOIN 判归属: hermes|502|zombie_empty_completion|2, 与主链彻底 host 分离)
- 30min 按模型 SR: **dsv4f0731_nv SR=98.8% (167/169)** — 唯二 bad 即 hermes 越界 502, 主链无关
- fallback (cc_requests 30min) = **0 次 / 108 请求全 200 (0.0%)**
- nv_tier_attempts (dsv4f0731_nv 30min) = k0-k4 全 pexec_success (22/19/23/22/21, 另 k3 一条 empty_200), 无 tier 致命错误
- 30min nv_gw buffer/wait/keymanager 日志: 仅 NV-BUFFER 全 attempt=1 直接 success (elapsed 1.6s~13s, fr=tool_calls),
  零重试/零等待/零冷却 — 无缓冲吸收需要
- 主链当前首代模型 = **dsv4f0731_nv** (cc4101.PRIMARY_UPSTREAM_MODEL), 无 tier 降级/无 key ��劳
- /health: 40006/4101 全 200; 容器 nv_gw Up 15h, cc4101 Up 15h, nv_gw_stable Up 5d+

## 主链 (首代 dsv4f0731_nv)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary SR | 108/108 = 100% | ✅ |
| 主链专属错误 | 0 rows | ✅ |
| fallback 触发 | 0 次 (0.0%) | ✅ |
| tier 错误 (dsv4f0731_nv) | k0-k4 全 pexec_success | ✅ |
| buffer | 全 attempt=1 success, 零重试 | ✅ |

## 下一步
- 持续 NOP 观察, 主链 dsv4f0731_nv 首代, 参数稳态无可调。
- 持续确认 hermes 越界 bad (zombie_empty_completion/502) 与主链 host 分离 (caller JOIN)。
- 关注偶发 RemoteDisconnected 是否演成持久疲劳 (单 key 连续多轮全败再考虑 KEY_FID_BIND 换 fid)。