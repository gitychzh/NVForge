# R1506: HM2→HM1 — NOP (zombie-only, zero ATE, all params floor/optimal, ms_gw healthy)

## 数据收集 (HM1, post-restart 3h window)
- **Container restart**: 2026-07-15T18:15:54Z (~3h ago), clean post-restart window
- **3h**: 27req/16OK 59.3%SR, 11 fail
- **失败分解**: 11 zombie_empty_completion (NVCF content-filter, 不可配置)
  - dsv4p_nv: 5 zombie, avg 4,894ms, avg input 221,879 chars
  - glm5_2_nv: 6 zombie, avg 9,248ms, avg input 221,523 chars
- **0 ATE, 0 tier_attempts, 0 peer-fb, 0 ms-gw fallback, 0 key_cycle_429s**
- **Pexec 路径**: dsv4p_nv 100% key success (NV-SUCCESS on first attempt every time), zombie detected on stream passthrough
- **Integrate 路径**: glm5_2_nv 100% key success (NV-INTEGRATE-SUCCESS on first attempt), zombie detected on stream passthrough
- **ms_gw**: 6/6 100% SR — healthy fallback
- **Hourly**: 18h 75% (4req), 19h 55.6% (9req), 20h 60% (10req), 21h 50% (4req)
- **Compose md5**: ba4f2871 unchanged

## 分析
- Zombie 是唯一失败源 (11/11=100%), NVCF content-filter 行为: HTTP 200 + finish_reason=stop + 0-31 chars content, 221K+ input
- Gateway zombie detection 正确工作: NV-SUCCESS → NV-THINKING-TIMEOUT → NV-ZOMBIE-EMPTY → NV-ZOMBIE-ERROR-CHUNK，触发 openclaw fallback
- 0 ATE, 0 tier cycling, 0 429 — key pool 完全干净
- All FASTBREAK/Cooldown/Timeout/Budget 已在 floor/optimal
- ms_gw 100% SR — openclaw 的 fallback 路径可靠
- NVCF zombie 不可配置，无代码路径可优化

## 变更: NOP (无变更)
- 所有参数已在 floor/optimal
- 无配置可优化空间
- 铁律: 只改HM1不改HM2
## ⏳ 轮到HM1优化HM2
