# R680 (HM2) — 框架重构命名消歧 (HM2 对齐 HM1)

HM1 R680 已完成 (见 R680_hm1_rebrand.md)。此轮 HM2 同步骤对齐。

## HM2 特有处理
- **ms_uni41002 孤立容器删除** (compose 不引用, litellm image, docker rm)
- **legacy_ms_litellm build 失败** (HM2 中国 IP 拉不动 docker.io python:3.11-alpine) → 改用 litellm/litellm:v1.87.0 image (零流量 legacy, 不影响热路径)
- **5 个 legacy auth_to_api image retag** (cc-infra-auth_to_api_4000x → cc-infra-legacy_*) 避免 rebuild
- **legacy-ms-gateway 目录从 HM1 rsync 过来** (HM2 历史无此目录)
- **三 agent systemd unit 重启**: hermes-gateway / openclaw-gateway (user) + opencode-webui (system)

## 命名映射
与 HM1 完全一致 (见 R680_hm1_rebrand.md 命名表)。

## HM2 验证
- 容器: nv_gw/ms_gw/logs_db + 5 legacy auth + legacy_ms_litellm 全起
- 40006/40007 health OK, 端口发布正确
- /v1/models 带 nv-gw-token 返回正常
- DB: nv_gw → logs_db 连接 OK, nv_requests 17254 条
- 三 agent: hermes-gateway/openclaw-gateway/opencode-webui 全 active
- hermes provider key: litellm-nv-hm → nv_gw (对齐 HM1)

## 不改的 (铁律, 同 HM1)
- 端口号 / NV/MS 真实上游 key / agent 进程名 / agent 模型选择逻辑 / pgdata volume cc_pgdata / DB 库名表名

## 状态
两机框架重构彻底版完成。命名消歧全层落地: 容器/service/image/源码目录/provider key/api_key token/logs 目录/代码注释+HTTP header。cc2 红队 6+1 雷全缓解。
