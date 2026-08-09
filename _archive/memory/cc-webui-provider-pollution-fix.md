---
name: cc-webui-provider-pollution-fix
description: cc_webui 前端 selected-provider 被 codex 历史会话反向污染的根因与修复
metadata: 
  node_type: memory
  type: project
  originSessionId: 57d797c6-9305-4150-8d3b-a57601fb6040
---

cc_webui(CloudCLI webui)前端有个 effect(useChatProviderState.ts ~257行):打开任何历史会话时,把该会话的 `__provider` 用 `localStorage.setItem('selected-provider', __provider)` 反向写回全局默认。一旦点开过 codex 会话,`selected-provider` 被钉成 codex,之后所有新建会话都发 `codex-command`,后端 spawn codex —— 表现为"UI 选 claude 却跑 codex"。后端(agent.js/providerRegistry/readProvider)无任何强制改写,严格透传。

**Why:** 用户 2026-07-08 报"明明选 claude code 却强制 codex"。经代码审计+playwright 实测+后端日志三方印证,根因是前端 localStorage 污染,不是后端 bug。最初诱因是上轮 webui ANTHROPIC_BASE_URL 指向死端口 40005(已修成 4101),claude 报错后切到 codex 从此被钉死。

**How to apply:** 已在本地 cc_webui 源码删掉那行 setItem(保留 setProvider),vite build 出 index-DSJCzv7z.js,rsync 到远程 100.109.57.26:/home/opc2_uname/cc_ps/cc_webui/dist,重启 cloudcli-webui。旧 dist 备份在远程 dist.bak.20260708_211641。补丁只防新污染,不自动清旧残留:用户日常浏览器仍需手动 `localStorage.removeItem("selected-provider")` + 刷一次。本机 build 时 node_modules 残缺,临时 symlink 了 /tmp/vite7 的 vite7.3.5/@vitejs/plugin-react/autoprefixer 才能构建,下次重建要注意。相关:[[github-ssh-via-443-mihomo]] [[host-roles-and-self-positioning]]
