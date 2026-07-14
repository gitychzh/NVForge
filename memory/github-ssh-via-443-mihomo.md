---
name: github-ssh-via-443-mihomo
description: "GitHub SSH 22 端口在本机被 GFW reset, 用 ssh.github.com:443 经 mihomo 7891 可推拉"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 0406d561-48f4-457a-9d92-47a11ace0901
---

本机 (HM1) 直连 GitHub SSH (22 端口 git@github.com) 被 reset:
`kex_exchange_identification: Connection closed by remote host` / `103.70.77.218 port 22`。
HTTPS (github.com:443) 直连 OK, 但 git remote 是 SSH 协议, http.proxy 不生效。

可用通道 (验证过):
```bash
# 单次测试
ssh -o ProxyCommand="nc -X 5 -x 127.0.0.1:7891 %h %p" -T -p 443 git@ssh.github.com
# → "Hi gitychzh! You've successfully authenticated"

# git 推拉 (timeout + env 包装, ProxyCommand 参数要转义空格)
timeout 120 env GIT_SSH_COMMAND='ssh -p 443 -o ProxyCommand=nc\ -X\ 5\ -x\ 127.0.0.1:7891\ %h\ %p -o ConnectTimeout=15' git pull --rebase origin main
timeout 120 env GIT_SSH_COMMAND='ssh -p 443 -o ProxyCommand=nc\ -X\ 5\ -x\ 127.0.0.1:7891\ %h\ %p -o ConnectTimeout=15' git push origin main
```

mihomo 7891=sg-fast, 7892=jp-fast 都通; 7890 (mixed) 节点对 GitHub SSH 不稳。

关联 [[cross-host-collab-roles]] (push 前必 pull --rebase, 远程 CC 也会 push)。
