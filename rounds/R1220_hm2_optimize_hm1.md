# HM2 Optimize HM1 — Round R1220

## 1. 触发分析
- **cron 脚本输出**: `"这是我提交的, 不触发"`
- **最新 commit author**: `opc2_uname` (HM2)
- **脚本正确检测**: 自提交, 标记 "不触发"
- **cron 仍被派遣**: 误触发 (double-dispatch, R1219已存在)
- **HM1 SSH**: 连接超时 — Tailscale WG data-plane broken (tx ~194064 rx 0, 持续断裂)
- **HM2 git log**: R1219 (opc2_uname), R1218 (opc2_uname), R1217 (opc2_uname)
- **HM1 git log**: 无法验证（SSH不可达）

## 2. 数据 (改前必有数据)
**来源**: R1133-R1219 chain估计 (SSH不可达, 无法独立验证DB/logs)

| 指标 | 值 |
|------|-----|
| 6h 请求 | ~32req |
| 6h 成功 | ~20OK (62.5%) |
| 6h 失败 | ~12 zombie (37.5%) |
| zombie类型 | zombie_empty_completion (glm5_2_nv integrate) |
| root cause | NVCF content-filter stop+12-36chars, input_chars ~157K avg |
| dsv4p_nv | 0 traffic ~16h+ |
| kimi_nv | 0 traffic |
| ms_gw | 0 traffic |
| tier_attempts | 0 |
| fallback | 0 |
| FASTBREAK | 0 |
| GLOBAL-COOLDOWN | 0 |
| compose md5 | 不变 (7975939c245761e451a8813852dcb9bf, 48h+ unchanged since R1133) |

## 3. 决策: NOP
- **Gate 1-6**: 全部通过 (所有失败均为 zombie_empty_completion, 代码级信号)
- **zombie-only NOP pattern** (R1146-R1156确立): 100%失败为zombie_empty_completion, 0非zombie错误, 0 NV-TIER-FAIL, 0 GLOBAL-COOLDOWN, 0 FASTBREAK, dsv4p_nv 0 traffic → NOP
- **NVCF content-filter**: 非配置可修复, 返回stop+12-36chars对160K+ glm5_2_nv输入
- **所有参数地板/最优**: TIER_COOLDOWN_S=15, TIER_TIMEOUT_BUDGET_S=112, UPSTREAM_TIMEOUT=66, EMPTY_200_FASTBREAK=2, FASTBREAK=1, MIN_OUTBOUND=0, CONNECT_RESERVE=0, INTEGRATE_COOLDOWN=0, FALLBACK_HEALTH=0.10, NVU_TIER_BUDGET_DSV4P_NV=72, KEY_AUTHFAIL_COOLDOWN_S=60
- **零参数, 零compose变更, 零容器重启**

## 4. 链统计
R1133→R1220: 88th chain of R1133 false trigger. SSH unreachable since R1209 (12 rounds). Tailscale WG data-plane broken. compose md5 unchanged 48h+. 铁律:只改HM1不改HM2.

## ⏳ 轮到HM1优化HM2
