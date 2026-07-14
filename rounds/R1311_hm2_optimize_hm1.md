# HM2 Optimize HM1 — Round R1311

## 触发分析
- cron 脚本输出: `"这是我提交的, 不触发"`
- 最新 commit author = `opc2_uname` (HM2, 自提交)
- 脚本正确检测到自提交并标记 "不触发", cron 仍被派遣 — 误触发 (double-dispatch, 25th consecutive post-R1286)
- R1310 已由预运行脚本提交为 NOP, symlink 已指向 R1310

## 数据收集 (改前必有数据)

### HM1 容器状态
- nv_gw: Up 4 hours (healthy)
- Compose md5: `6e1b58bc70eca49e500e3034b08376d9` (stable, 与 R1308-R1310 一致)
- Container restart: 2026-07-13T22:14:51Z

### 6h DB 数据 (nv_gw)
- 总计: 59req/52OK(88.1%SR)/7fail
- 失败: 7× zombie_empty_completion (glm5_2_nv integrate only), avg 4,870ms, avg input 213K chars
- 0 tier_attempts, 0 ATE, 0 IncompleteRead, 0 fallback_occurred
- dsv4p_nv: 0 traffic, kimi_nv: 0 traffic
- NVU_PEER_FB_SKIP_MODELS: 空 (peer-fb 全模型启用)

### 逐小时 SR
| Hour (UTC) | Total | OK | Fail | SR% |
|---|---|---|---|---|
| 21:00 | 6 | 4 | 2 | 66.7 |
| 22:00 | 7 | 5 | 2 | 71.4 |
| 23:00 | 6 | 5 | 1 | 83.3 |
| 00:00 | 6 | 5 | 1 | 83.3 |
| 01:00 | 29 | 28 | 1 | 96.6 |
| 02:00 | 5 | 5 | 0 | 100.0 |

### ms_gw
- 13/13 100% SR

### nv_gw 日志 (最近 100 行)
- 1× NV-ZOMBIE-EMPTY (glm5_2_nv, finish_reason=stop, content_chars=12<50, input_chars=175K)
- NV-ZOMBIE-ERROR-CHUNK: 已发送 content_filter error SSE chunk → openclaw fallback
- 其余全部正常 NV-REQ 流, tier_chain=['glm5_2_nv'], no fallback

### HM1 当前参数
```
UPSTREAM_TIMEOUT=66
TIER_TIMEOUT_BUDGET_S=205
TIER_COOLDOWN_S=15
KEY_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=0
NVU_PEXEC_TIMEOUT_FASTBREAK=1
NVU_EMPTY_200_FASTBREAK=2
NVU_INTEGRATE_TIMEOUT_FASTBREAK=1
NVU_INTEGRATE_THINKING_TIMEOUT_S=90
NVU_FORCE_STREAM_UPGRADE=0
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=66
NVU_FALLBACK_HEALTH_THRESHOLD=0.05
NVU_MS_GW_FALLBACK_TIMEOUT=195
NVU_MS_GW_FALLBACK_MODELMAP=glm5_2_nv:glm5_2_ms,kimi_nv:kimi_ms,dsv4p_nv:dsv4p_ms
NVU_TIER_BUDGET_DSV4P_NV=72
NVU_TIER_BUDGET_GLM5_2_NV=96
NVU_TIER_BUDGET_MINIMAX_M3_NV=100
NVU_PEER_FB_SKIP_MODELS=(空)
```

## 决策: NOP

### 原因
1. 所有 7 个失败均为 zombie_empty_completion — NVCF glm5_2 函数 content-filter 停止 (finish_reason=stop, 12 chars output, 213K avg input)。代码级 zombie 检测正确 (5-6s 返回 502, 比旧版 NVStream_TimeoutError 96s 快 16×)
2. 0 ATE, 0 tier_attempts, 0 IncompleteRead — 无资源耗尽、无 budget 溢出、无流中断
3. 无 fallback 触发 — 所有请求在 tier 内完成 (成功或 zombie 快速失败)
4. 逐小时 SR 趋势向好: 66.7%→100.0%, 最后 3 小时 96.6%/100.0%
5. 所有参数处于 floor/optimal 状态, 无进一步优化空间
6. NVU_PEER_FB_SKIP_MODELS 已清空 — peer-fb 全模型启用

### 参数变更: 无
- 零参数修改, 零 compose 编辑, 零容器重启

### 铁律确认
- 只改HM1不改HM2 ✓ (本轮无改动)
- 改前必有数据 ✓
- 所有修改写入仓库 ✓

## ⏳ 轮到HM1优化HM2
