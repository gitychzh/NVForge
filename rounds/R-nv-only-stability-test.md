# R-nv-only-stability-test: glm5_2_nv vs dsv4p_nv 多链路稳定性测试 (HM2)

> 日期: 2026-07-31
> 范围: 仅 NVIDIA 模型, 不涉及 MS 模型
> 主机: HM2 (100.109.57.26)
> 方法: 直接 nv_gw 探测 + DB 24h 回溯

## 测试设计

### 直接探测 (/tmp/nv_stability_test_v4.py)
- URL: `http://127.0.0.1:40006/v1/chat/completions`
- 2 模型 (glm5_2_nv, dsv4p_nv) × 2 模式 (流式/非流式) × 2 大小 (small ~10 tokens / medium ~500 tokens) × 5 次迭代 (small) / 1 次 (medium)
- 共 24 请求, 10s 间隔, 120s 超时
- 注: 适配器 (hm4104/opclaw4103) forwarder.py L226 `body["model"]=PRIMARY_MODEL` 覆盖请求模型 → 只能直打 nv_gw 测指定模型

### DB 回溯
- 24h `nv_requests` 表, 按模型/状态/错误类型/调用方/流式 拆分

## 直接探测结果

18/24 请求完成 (进程在第 19 请求卡死, curl 子进程挂起被 kill):

| 模型 | 模式 | 大小 | 成功率 | TTFB 范围 | 备注 |
|---|---|---|---|---|---|
| glm5_2_nv | nonstream | small | 4/5 (80%) | 54-98s | 1×120s timeout |
| glm5_2_nv | stream | small | 3/5 (60%) | 44-84s | 2×no_response, total_dur=120s(curl timeout) |
| glm5_2_nv | nonstream | medium | 1/1 (100%) | 105s | |
| glm5_2_nv | stream | medium | 1/1 (100%) | 49s | total_dur=120s(curl timeout) |
| dsv4p_nv | nonstream | small | 5/5 (100%) | 1.4-30s | 快 4-20× |
| dsv4p_nv | stream | small | 3/3 (100%) | 2.2-25s | total_dur=120s(curl timeout) |
| dsv4p_nv | nonstream/stream | medium | 未完成 | — | 进程卡死 |

## DB 24h 统计

| 指标 | dsv4p_nv | glm5_2_nv |
|---|---|---|
| 总请求 | 3,964 | 235 |
| 成功 | 2,771 | 216 |
| **成功率** | **69.9%** | **91.9%** |
| 平均延迟 | 52.6s | 63.8s |
| P50 延迟 | 20.9s | 32.8s |
| 最大延迟 | 741.1s | 439.2s |

### 错误分布 (24h)

| 模型 | 错误类型 | 数量 |
|---|---|---|
| dsv4p_nv | all_tiers_exhausted (502+429) | 773 |
| dsv4p_nv | buffer_exhausted | 218 |
| dsv4p_nv | zombie_empty_completion | 151 |
| dsv4p_nv | client_gone_pre/during_flush | 39 |
| dsv4p_nv | NVStream/NVAnth IncompleteRead | 12 |
| glm5_2_nv | all_tiers_exhausted | 12 |
| glm5_2_nv | buffer_exhausted | 6 |
| glm5_2_nv | zombie_empty_completion | 1 |

### 调用方拆分 (24h)

| caller | model | total | SR% |
|---|---|---|---|
| cc4101-primary | dsv4p_nv | 1,313 | 84.7% |
| cc4101-primary | glm5_2_nv | 94 | 93.6% |
| openclaw2 | dsv4p_nv | 1,374 | 51.4% |
| hermes | dsv4p_nv | 44 | 36.4% |
| openclaw | dsv4p_nv | 17 | 5.9% |
| unknown | dsv4p_nv | 1,199 | 76.6% |
| unknown | glm5_2_nv | 121 | 92.6% |
| other | dsv4p_nv | 19 | 100% |
| other | glm5_2_nv | 20 | 80% |

### 流式 vs 非流式 (24h)

| 模型 | stream | total | SR% |
|---|---|---|---|
| dsv4p_nv | f | 178 | 68.0% |
| dsv4p_nv | t | 3,794 | 70.1% |
| glm5_2_nv | f | 18 | 88.9% |
| glm5_2_nv | t | 211 | 92.4% |

### 小时趋势 (dsv4p_nv SR%)

```
17:00 UTC: 46.0%  ← 谷底
18:00 UTC: 34.2%  ← 谷底
19:00 UTC: 36.2%  ← 谷底
20:00 UTC: 53.7%
21:00 UTC: 76.7%
22-03:00: 74-82%
04-06:00: 90-94%  ← 峰值
07-08:00: 76-79%
09:00 UTC: 96.2%  ← 恢复
```

glm5_2_nv 在同时段保持 78-95%, 波动小.

## 核心结论

1. **glm5_2_nv 更稳定但极慢**: SR 91.9% vs 69.9%, 但响应 54-105s (nonstream) / TTFB 44-84s (stream). 24h 仅 235 请求 (低流量).

2. **dsv4p_nv 快但不稳定**: 正常时 1.4-30s (4-20× 快于 glm5_2_nv), 但有周期性 all_tiers_exhausted 级联 (NVCF 429 限流 → KeyManager 全 key cooldown). 集中在 17:00-19:00 UTC (北京时间 01:00-03:00).

3. **dsv4p_nv 错误多样性**: 773 all_tiers_exhausted + 218 buffer_exhausted + 151 zombie_empty_completion. glm5_2_nv 仅 19 错误.

4. **流式 vs 非流式差异小**: 两模型流式 SR 略高 (dsv4p +2.1pp, glm5_2 +3.5pp).

5. **探测期间 dsv4p_nv 100% 成功** (5/5 ns + 3/3 stream), 而 glm5_2_nv 60-80%. 说明 dsv4p_nv 的故障是间歇性的, 探测刚好避开了故障窗口.

6. **openclaw2 调用方 dsv4p_nv SR 仅 51.4%**: 占 1,374 请求 (34.7% 总流量), 大量 all_tiers_exhausted. 是 dsv4p_nv 整体 SR 拉低的主因.

## 配置参考 (测试期间)

- NVU_DISABLE_MS_FALLBACK=1 (nv_gw 无 ms_gw fallback)
- 5 key × 5 美国 IP (mihomo SOCKS5 7894-7899)
- KeyManager: 429 指数退避 120s→600s, conn 30s→60s
- NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4 (cc4101 不绑定固定 key)
- 所有 4 adapter PRIMARY=glm5_2_nv (R2293 设定, 但 dsv4p_nv 流量更大 = hermes + openclaw2)

## 声明

本测试仅使用 NVIDIA 模型, 未触及 ms_gw / MS 模型. 未修改任何配置.
