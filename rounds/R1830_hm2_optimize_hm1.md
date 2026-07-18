# R1830 (HM2→HM1): NOP — false trigger, 零可配置修复故障

## 数据 (HM1, 6h)
- 总请求: 41, 成功: 37 (90.2% SR), 失败: 4
- 4 kimi_nv ATE: all NVCF-degraded, 502, tiers_tried=1, duration=1-1715ms, no fallback, non-config
- glm5_2_nv: 25/25 OK (100%), avg=8240ms, max=15722ms (6h), 24h max=21582ms
- dsv4p_nv: 12/12 OK (100%), avg=15025ms, max=40603ms
- 1 SSLEOF (glm5_2 pexec, rare), 2 429_nv_rate_limit (dsv4p, rare, all recovered)
- 0 fallback_occurred, 0 docker log errors, 0 peer-fb triggered

## 24h 数据
- 122 total, 114 OK (93.4%), 8 fail
- 4 kimi ATE (NVCF-degraded) + 3 glm5 zombie_empty_completion (>250K BIG_INPUT) + 1 dsv4p ATE
- 3 zombie handled by BIG_INPUT breaker (FAIL_N=1, COOLDOWN=7200s, fast-reject ATE ~0ms)

## 容器漂移检查
- 零漂移: KEY_COOLDOWN=61, TIER_COOLDOWN=61, BUDGET_GLM5_2=65, BUDGET_DSV4P=45, PEER_FB=122, SSLEOF=0.1, FASTBREAK=1, EMPTY_200=1, MIN_OUTBOUND=0, BIG_INPUT_FAIL_N=1, BIG_INPUT_COOLDOWN=7200, STREAM_FIRST=15, STREAM_TOTAL=25, CONNECT_RESERVE=0, FORCE_STREAM=66, INTEGRATE_FASTBREAK=1, MS_GW_FB=120 — all container=compose ✓
- health: status=ok ✓

## 分析
- False trigger: HM2 自提交 caae3a4 (R1830 cc2), 脚本正确识别"不触发"但 cron 仍被派遣
- 6h 零可配置修复故障: 4 kimi ATE 全部 NVCF-degraded (non-config, kimi peer-fb SKIP_MODELS)
- glm5_2_nv 100% SR, dsv4p_nv 100% SR, 零 peer-fb 触发
- 所有参数 floor/optimal: KEY_COOLDOWN=61(60+1 buffer), TIER_COOLDOWN=61, SSLEOF=0.1(floor), FASTBREAK=1(floor), EMPTY_200=1(floor), BIG_INPUT_FAIL_N=1(floor), MIN_OUTBOUND=0(floor), CONNECT_RESERVE=0(floor)
- NVU_TIER_BUDGET_GLM5_2_NV trajectory R1825(80)→R1827(75)→R1828(70)→R1829(65): 6h max=15.7s, 65=4.1x margin. 继续→60 仅省5s ATE路径, glm5_2 6h 零ATE, 无实际收益
- Peer-fb: 55+122=177<180 ✓ (3s margin)
- 429 cycling: 1.08 cycles/req (low, healthy)

## 决策: NOP
- 零参数修改, 零compose修改, 零容器重启
- 铁律:只改HM1不改HM2 ✓
## ⏳ 轮到HM1优化HM2
