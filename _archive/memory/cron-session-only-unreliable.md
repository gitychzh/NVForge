---
name: cron-session-only-unreliable
description: "Claude 的 CronCreate 是 session-only 不写盘, 会话中断/上下文压缩会丢失, 不能用于跨会话定时任务"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9f86955b-051d-43b2-9038-4442ccdeff80
---

CronCreate 创建的定时任务是 session-only (in-memory), 不写盘, 会话结束或上下文压缩时丢失. 用 `recurring: false` 的一次性任务 fire 后自动删除, 加 session-only, 极不持久.

**Why**: 2026-07-07 跑 HM2 8 轮优化, 第 1 轮后用 CronCreate 调度 5 分钟后第 2 轮, 结果会话状态变化后 cron 没了, 第 2-8 轮全漏, 用户发现"只跑一轮就终止".

**How to apply**: 多轮定时优化这类需要跨较长时间的任务, 不要依赖 CronCreate 调度下一轮. 应在该会话内连续执行完所有轮 (每轮之间用 Bash sleep 或 Monitor 等待间隔), 或用系统级 cron (crontab) / systemd timer 做持久调度. CronCreate 只适合会话内短时提醒. 见 [[cross-host-collab-roles]].
