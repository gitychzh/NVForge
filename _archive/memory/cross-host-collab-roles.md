---
name: cross-host-collab-roles
description: NVForge 双机对称架构下我(本地HM1的CC)与远程CC的优化职责划分
metadata: 
  node_type: memory
  type: project
  originSessionId: e096d5f6-d05f-464c-99c6-dccdfa5578b8
---

NVForge 是双机对称架构 (HM1=100.109.153.83 本机, HM2=100.109.57.26 远程)。两台各跑一个 Claude Code 实例, 共用同一个 GitHub repo (`gitychzh/NVForge`), 互为优化者:

- **我(本地 HM1 的 CC) → 优化 HM2**, 不碰 HM1
- **远程 CC (在 HM2) → 优化 HM1**, 不碰 HM2

原因: 自己改自己容易崩溃 (改 nv_gw 时若把链路改坏, 自己的 CC 就跑不动了, 无法继续修复)。

**操作约束**:
- HM1 默认不动, 除非用户明确授权 (现在有了明确原因, 不只是偏好)
- 对 HM2 的改动 commit/push 后, 远程 CC 会 pull 到
- 远程 CC 对 HM1 的改动也会 push, 我 push 前必须 `git pull --rebase` (否则 fast-forward 被拒, 已遇到过一次)
- 远程用 `gh`/SSH key push, 本机 SSH key 已在 GitHub 账号

