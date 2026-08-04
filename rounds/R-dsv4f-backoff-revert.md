# R-dsv4f-backoff-revert: 529 cycling backoff 实验失败 — 回退

**Date:** 2026-08-04
**Container:** dsvf0731_nv40666 (port 40666, HM2)
**Status:** REVERTED (not committed to repo, only round file)

## 实验

在 R-dsv4f-adaptive 基础上增加 529 cycling backoff: 每次 529 后等待 2s 再试下一个 key。

**假设**: NVCF 529 过载可能在 2s 内恢复, key 间加 backoff 给 NVCF 恢复时间。
**实际**: NVCF 529 是账户级持续过载, 2s 不会恢复。backoff 只增加延迟。

## 数据

| 策略 | SR | avg latency | 502 avg latency |
|------|-----|-------------|-----------------|
| Adaptive (no backoff) | 80-90% | 10s | 10-44s |
| Adaptive + 2s backoff | 60% | 14s | 18-46s |

backoff 导致:
- SR 下降 20-30pp (80%→60%)
- 延迟增加 40% (10s→14s)
- 502 延迟增加 (10-44s→18-46s)

## 结论

529 backoff 有害无益。NVCF 529 是账户级持续过载, 在 tier budget (180s) 内不会恢复。
快速换 key (0ms 间隔) 反而能在 budget 内多试几次, 增加命中成功 key 的概率。

## 操作

已撤销 backoff 补丁, 保留 R-dsv4f-adaptive (pexec-first 自适应)。
