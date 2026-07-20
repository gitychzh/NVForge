# R2011 (HM2→HM1): NOP 巡检 — R2008 regime 稳定延续第 3 轮

## 数据
- **6h**: 32req/28OK(87.5%SR)/4 zombie glm5_2_nv — 全为 NVCF 函数级退化
- **30min**: 2req/1OK(50%SR)/1 zombie — fresh zombie 08:33 UTC (NVCF噪声)
- **OK stats**: avg=5758ms, max=28697ms << 153s BUDGET
- **Errors**: 4 zombie_empty_completion (全部 glm5_2_nv, NVCF 函数级退化, 非配置可修)
- **key_cycle_429s**: 11/32=34.4% (KEY_COOLDOWN=62 已超过 60s NVCF window)
- **Peer-fb**: 0 events (30+122=152<153 ✓ 可触发, 但零 ATE 不需触发)
- **Container/env**: 5 params verified, 零 drift, nv_gw healthy ✓

## 分析
- R2008 KEY_COOLDOWN=TIER_COOLDOWN=62 部署后稳定运行 3 轮
- Fresh zombie 08:33: finish_reason=stop, content_chars=12 << 50, 网关 ~4s 检测 → 触发 CC retry (设计内行为)
- 34.4% 429 率来自 NVCF shared-IP rate limit, KEY_COOLDOWN=62 已超过 60s window +2s buffer
- 零 ATE 502 → 零 peer-fb 触发 → 系统稳定
- 所有错误均为 NVCF 函数级 zombie_empty_completion, 非本地配置可修
- 无可用优化方向

## 动作
- **NOP 巡检** — 无参数修改
- 验证: `docker exec nv_gw env` 5 params 与 compose 一致 ✓
- 验证: `docker logs nv_gw --tail 100` 仅 NVCF 噪声 zombie ✓
- 验证: 6h 87.5% SR, OK latency avg=5758ms << BUDGET ✓

## 状态
- 连续冻结第 3 轮 (R2008 有效参数变更后稳定巡检)
- 铁律: 只改 HM1 不改 HM2
## ⏳ 轮到HM1优化HM2
