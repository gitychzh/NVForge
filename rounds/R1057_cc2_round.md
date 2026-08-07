# R1057 — cc2 NOP 巡检轮 (HM2 nv_gw)

## 决定: NOP 不改码 — cc2 主链连续第 165 轮 100% 干净

## 依据 (注入轮前链路分析 2026-08-07 18:51 CST + caller JOIN)

- 30min cc4101-primary (主 nv_gw:40006) = **109/109 全 200 = 100% SR, 0 bad**
  (caller JOIN 实测: cc4101-primary total=109, ok=109, max(status)=200 — scoped 主链专属错误 = 0 rows)
- nv_requests 总 bad = 2 (zombie_empty_completion ×2, 502), 全属 hermes 越界宿主
  (实测 caller JOIN: hermes total=35, ok=33, non200=502 — 与主链彻底 host 分离)
- 30min 按模型 SR: **dsv4f0731_nv SR=98.6% (144/146)** — 唯二 bad 即 hermes 越界 502, 主链无关
- fallback (cc_requests 30min, 实测) = **0 次 / 0.0%** (总 109, 主链 109 请求全 200)
- nv_tier_attempts (dsv4f0731_nv 30min) = k0=23,k1=21,k2=24,k3=19(另1empty_200),k4=22 全 pexec_success — 无 tier 致命错误
- 30min nv_gw buffer/wait/keymanager 日志: 无缓冲吸收需要 (全 attempt=1 直接 success)
- 主链当前首代模型 = **dsv4f0731_nv** (cc4101.PRIMARY_UPSTREAM_MODEL), 无 tier 降级/无 key 疲劳
- /health 实测: 40006/4101 全 200
- 容器: nv_gw Up 20h, cc4101 Up 15h

## 主链 (首代 dsv4f0731_nv)

| 指标 | 值 | 状态 |
|---|---|---|
| cc4101-primary SR | 109/109 = 100% | ✅ |
| 主链专属错误 | 0 rows | ✅ |
| fallback 触发 | 0 次 (0.0%) | ✅ |
| tier 错误 (dsv4f0731_nv) | k0-k4 全 pexec_success | ✅ |
| buffer | 全 attempt=1 success, 零重试 | ✅ |

## 下一步
- 持续 NOP 观察, 主链 dsv4f0731_nv 首代, 参数稳态无可调。
- 持续确认 hermes 越界 bad (zombie_empty_completion/502) 与主链 host 分离 (caller JOIN)。
- 关注偶发 RemoteDisconnected 是否演成持久疲劳 (单 key 连续多轮全败再考虑 KEY_FID_BIND 换 fid)。