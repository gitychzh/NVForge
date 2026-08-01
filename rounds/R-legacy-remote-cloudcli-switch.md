# R-legacy-remote: cloudcli webui + cc2 CLI 全部切到 40001

**日期**: 2026-08-01
**主机**: HM2
**铁律**: HM1 零改动

## 问题

cloudcli webui 和 claude code CLI 不行: cc4101 (4101) breaker OPEN + FALLBACK_URL=none = 所有请求 "upstream failed".

根因: cc4101 → nv_gw 链路 dsv4p_nv 间歇失败, breaker 累积 OPEN, R-nvonly 禁用了 ms_gw fallback, 无路可走.

## 变更

1. cloudcli-webui systemd unit: ANTHROPIC_BASE_URL 4101→40001, API_KEY cc4101-token→sk-litellm-local
2. ~/.cloudcli/.env: 40000→40001 (保持一致)
3. npm cloudcli .env: 4101→40001, cc4101-token→sk-litellm-local
4. systemctl --user daemon-reload + restart cloudcli-webui

备份: .bak.R-legacy-remote (三个文件各一份)

## 不动

- cc4101 容器 (4101) — 原链路保留
- settings.json 已在上一轮改好 (40001)

## 链路

切换前 (cloudcli + cc2):
  cloudcli/cc2 → 127.0.0.1:4101 (cc4101) → nv_gw → NVCF (breaker OPEN, 100% fail)

切换后:
  cloudcli/cc2 → 127.0.0.1:40001 (legacy_cc_1) → legacy_ms_litellm → ModelScope glm5.2

## 验证

- cloudcli 进程 env: ANTHROPIC_BASE_URL=http://127.0.0.1:40001, API_KEY=sk-litellm-local
- webui HTTP 200
- E2E 40001: model=glm5.2_cc, stop=max_tokens
- 旧 4101 连接 FIN-WAIT-2 关闭中, 无新流量
- 旧 claude 进程 (pid=3305233) 已退出

## 回滚

- systemd: cp cloudcli-webui.service.bak.R-legacy-remote → daemon-reload → restart
- .env: cp .env.bak.R-legacy-remote
