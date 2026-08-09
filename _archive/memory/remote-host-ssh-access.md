---
name: remote-host-ssh-access
description: 远程主机(100.109.57.26)的SSH连接方式——走222端口不是22
metadata: 
  node_type: memory
  type: reference
  originSessionId: 6f683545-7b50-4750-b5ee-94614afa7f78
---

远程主机 100.109.57.26 的 SSH 登录方式：`ssh -p 222 opc2_uname@100.109.57.26`（端口 **222**，用户名 **opc2_uname**）。

22 端口是 closed 的，但不能据此推断"SSH 进不去"——SSH 实际监听在 222。之前我错误地因 22 closed 就断定无法 SSH 登录，这是错的；用户明确纠正过。

相关：cloudcli UI 在 3001，cc4101 在 4101，ms_gw 在 8080（见 [[host-roles-and-self-positioning]]）。远程主机的本地服务挂了时，应直接 SSH 上去查 `ps`/`ss`/日志，而不是干等。
