---
name: glm52-egress-geo-real-data
description: "glm5.2多IP实测:美国最快2.6s; ⚠2026-07-14修正: integrate对glm5.2 chat有地理限制,日本出口5/5超时(非只是慢),见[[glm52-integrate-geo-restriction-confirmed]]; pexec rclen=0疑thinking未真返"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8fd3e5ef-956b-47c8-bc05-6cf506d1c4aa
---

2026-07-13 22:00 实测 (远程 HM2, timeout=120s). **多 IP/多链路 glm5.2 真实数据.** 修正了 timeout=40 时代的误判.

## mihomo 端口→出口→地理 (HM2, ~/.config/mihomo/config.yaml)
- 7891 = 新加坡 (203.27.106.146)
- 7892 = 日本 (103.62.49.138)  [7893 同 IP]
- 7894 = 美国A (134.195.101.193)  [7897 同 IP]
- 7895 = 美国B (134.195.101.194)
- 7896 = 美国C (134.195.101.195)
- 7899 = 美国D (134.195.101.180)
- 无台湾节点 (provider 只有 JP 东京 / SG / US 旧金山)

## A. pexec 5_2 function (3b9748d8) × 出口 (k1, 1次)
| 出口 | 结果 | 时延 | 备注 |
|---|---|---|---|
| direct 直连 | 504 | 63.6s | ❌ 后端网关错误 |
| 7891 新加坡 | 200 | 62.6s | ✓ 慢 |
| 7892 日本 | 202 | 64.5s | ⚠ 后端scaling (202=非失败但无content, 需重试) |
| 7894 美国A | 200 | 2.6s | ✓✓ 最快 |
| 7899 美国B | 200 | 5.0s | ✓ |

## B. integrate (model 名 z-ai/glm-5.2, 不分 function) × 出口
| 出口 | 结果 | 时延 |
|---|---|---|
| direct 直连 | 200 | 80s ✓ (慢但可用, 推翻旧"只接受美国") |
| 7892 日本 | 200 | 66.4s ✓ |
| 7899 美国B | 200 | 2.7s ✓✓ 最快 |

**integrate 不限制地理**, 美国最快(2.7s), 日本/直连慢(60-80s). 旧"JP/SG卡死"是 timeout=40 误判.

> ⚠️ **2026-07-14 修正**: 上述"integrate 不限制地理"结论已被推翻。当天实测日本出口(103.62.49.138)+integrate z-ai/glm-5.2 chat 调用 **5/5 全超时(25s 0字节)**,而美国节点 3/3 OK。可能 NVCF 当天收紧了地理策略,或 pexec 202(后端scaling)与 integrate chat 限制行为不同。详见 [[glm52-integrate-geo-restriction-confirmed]]。生产 K1-K5 必须全美国,绝不能切日本/新加坡做测速——切日本会直接搞坏 glm5_2_nv 生产路径(已造成 R856 mid-response 故障).

## C. 5key×5美国出口 排名 (并发, 最快5组合)
| # | 链路 | key | 出口 | IP | 耗时 |
|---|---|---|---|---|---|
| 1 | integrate | k4 | 7894 | 193 | 6.51s |
| 2 | integrate | k4 | 7895 | 194 | 6.97s |
| 3 | integrate | k4 | 7899 | 180 | 6.99s |
| 4 | integrate | k4 | 7896 | 195 | 7.04s |
| 5 | integrate | k1 | 7897 | 193b | 8.42s |

integrate 全面优于 pexec (integrate 24/25 成功 vs pexec 16/25, 且更快). **最快集中在 integrate + k4 + 任意美国出口 (6.5-7s, 4出口几乎无差别).**

## 异常发现
1. **pexec 5_2 的 reasoning_content 全部 rclen=0** (除 direct 外): inject 配置 `chat_template_kwargs.enable_thinking:True` (R827 开), 但 pexec 路径实际没返回 reasoning 内容 (content=5字符, rclen=0). 疑 NVCF pexec 后端对 5_2 的 thinking 支持有问题, 或 thinking 内容被 NVCF 在 pexec 路径剥离. (对比: integrate 路径 thinking 健康, 见 [[integrate-us-exit-glm52-breakthrough]]).
2. **504 只在 pexec direct 出现**: integrate direct 是 200(80s), pexec direct 是 504(63.6s). pexec 直连后端网关有故障.
3. **202 = 后端 scaling**: 日本出口 pexec 返回 202, 非失败但无 content, 需重试或换出口. 见 [[nvcf-pexec-field-semantics]].

相关 [[glm52-function-id-fact]] [[integrate-us-exit-glm52-breakthrough]] [[r839-glm52-mode-chain]] [[nvcf-testing-methodology]]
