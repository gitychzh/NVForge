# R-deadline650: cc4101 STREAM_TOTAL_DEADLINE 580→650 对齐 buffer 600s 预算

**Date:** 2026-07-27
**Host:** HM2 (100.109.57.26)
**性质:** 参数改动 (env 单点, 不改代码)

## 改前数据 (2h 窗口 11:51-13:51)

| 层级 | 指标 | 值 |
|---|---|---|
| nv_gw buffer | 87 成功 / 88 总 | 97.7% SR |
| nv_gw buffer 4-key 轮转 | k2 直射 59, k5 救回 26, k3 救回 2 | 32.2% 被 key 轮转救回 |
| nv_gw buffer exhausted | 1 (4 key 全失败→ms_gw 救回) | 1.1% |
| **cc4101 透传层** | **80 请求, 31 次 STREAM-STALLED** | **38.8% stall** |
| cc4101 stall 原因 | 全部 `stream_total_deadline=580s` | 580s 死钟 |
| stall 时长分布 | min=610s, p50=626s, p90=649s, max=733s | 全超 580s |

## 根因

R-buf2key 扩展 buffer 到 4 key × 150s = 600s 总预算, 但 cc4101 透传层的
`CC4101_STREAM_TOTAL_DEADLINE_S=580` 没有同步提升. cc4101 不知道 buffer 在做多 key
轮转, 它只看到一个请求挂了 580s 没完成 → 杀连接 → CC SDK 收到 timeout → session 死.

```
NVCF 不稳 → buffer 4 key 轮转(最坏 600s) → cc4101 580s 死钟先响 → STREAM-STALLED → CC timeout
```

buffer 救活了 NVCF 层 (97.7%), 但 cc4101 的 580s 死钟把 buffer 救回的请求又杀了 (38.8%).

## 改动

| 文件 | 改动 | 回滚 |
|---|---|---|
| `/opt/cc-infra/docker-compose.yml` L214 | `CC4101_STREAM_TOTAL_DEADLINE_S=580→650` | 改回 580 |
| `cc2_resume.sh` L13 | `API_TIMEOUT_MS=600000→700000` | 改回 600000 |
| `cc2_resume.sh` L14 | `CLAUDE_STREAM_IDLE_TIMEOUT_MS=600000→700000` | 改回 600000 |

为什么 650:
- buffer 最坏 4×150=600s + ms_gw fallback ~10s = 610s
- 留 40s 余量给 flush → 650s
- cc2 SDK API_TIMEOUT=700s > 650s, 留 50s 余量

备份: `docker-compose.yml.bak.R-deadline650`

## 验证

- cc4101 health: ok, `CC4101_STREAM_TOTAL_DEADLINE_S=650` 生效
- buffer 正常工作: NV-BUF2KEY-INTERCEPT + NV-BUFFER-SUCCESS 持续产出
- 改后请求成功 (req=b5fb71f4 等, 1 attempt, 41s, success_tool_call)

## 预期效果

- 之前 38.8% 的 580s stall 应降到接近 0 (只有真正超 650s 的请求才 stall)
- buffer 4 key 轮转完整执行, 不再被 cc4101 死钟打断
- ms_gw fallback 几乎不触发 (2h 仅 1 次 exhausted)
- **最终目标: 仅凭 glm5_2_nv 稳住, 不 fallback 到 ms_gw**

## 关联

- [[r-buf2key-verified]] — R-buf2key 4-key 轮转架构
- [[r-buffer-cc2-zombie-rootfix-deployed]] — R-buffer 基础
- [[r-cc-s3-per-agent-key-stepped-timeout]] — per-agent key 绑定
