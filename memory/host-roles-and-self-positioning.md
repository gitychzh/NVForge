---
name: host-roles-and-self-positioning
description: "我(本会话CC)运行在HM1, 被指派修HM2的cc4101/ms_gw/nv_gw; 改远程≠改自己, 不动本地即可"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9f86955b-051d-43b2-9038-4442ccdeff80
---

拓扑与定位 (2026-07 确认):
- **HM1 (100.109.153.83, opc_uname)** = 本机 = 我(本会话 Claude Code)运行的地方. 工作目录 /home/opc_uname/cc_ps/NVForge.
- **HM2 (100.109.57.26, opc2_uname, ssh -p 222)** = 远程主机. cc4101(远程CC agent, port 4101) / ms_gw(40007) / nv_gw(40006) 都在 HM2 上.
- 跨主机分工: 我优化 HM2, 远程另一个 CC 优化 HM1. 互不改自己. push 前 pull --rebase.

**关键定位 (用户 2026-07-07 明确):** 我是本机 CC, 用户让我修的是**远程主机 HM2 上的 claude code (cc4101) 及其链路 (ms_gw/nv_gw)**. 只要不动本地 HM1, 不修改自己(本会话), 风险非常小 — 即使把 cc4101 改坏, 我(本地)仍能 SSH 进去修.

**How to apply:** 修 cc4101/ms_gw/nv_gw 时不必过度保守 (它们在 HM2, 不是我). 但 ms_gw 的 db.py/upstream.py/schema 是 HM1+HM2 共享源 ([[shared-source-cross-host]]), 改共享源仍需外科 patch + pull --rebase, 不能整覆盖. cc4101 自身的 upstream.py/handlers.py/stream.py 不是共享源, 是 HM2 独有, 可直接改. 相关: [[cross-host-collab-roles]]
