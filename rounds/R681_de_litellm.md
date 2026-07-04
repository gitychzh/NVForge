# R681 — 彻底摒弃 litellm (Python base 统一 3.12-slim)

## 背景
R680 后所有容器命名消歧完成, 但 Dockerfile 仍 FROM litellm image (白嫖 Python base, 不 import litellm 库)。
用户要求去 litellm + Python 升 3.12+ (3.11 后期麻烦)。

## 调研结论 (cc 思考)
- **没有任何容器 import litellm 库**: nv_gw/ms_gw/legacy-* 全是自写代码, 纯 Python 标准库 (http.client/socket/ssl/threading)
- litellm base 只被当 Python 环境白嫖 (预装 fastapi/httpx/requests/psycopg2)
- nv_gw 实际第三方依赖: PySocks (import socks, SOCKS5 代码在但全直连不用) + psycopg2-binary (DB)
- ms_gw / legacy-ms-gateway / legacy-cc/codex/dispatcher/passthrough: 纯标库, 零第三方依赖

## 去 litellm 麻烦分析 (已思考)
1. **功能影响: 零**. 代码不 import litellm, 换 base 不改逻辑
2. **镜像体积: 收益**. litellm ~570MB → python:3.12-slim ~130MB (小 4 倍)
3. **Python 3.11→3.12**: 标准库 API 兼容, psycopg2-binary 有 3.12 wheel, 无破坏性变更
4. **docker.io 拉取**: HM1 走 registry-mirror (docker.1ms.run), HM2 走 mihomo daemon proxy (7880). 两机都测拉 python:3.12-slim 成功
5. **不失去**: 不失去任何功能 (热路径 nv_gw 不依赖 litellm); legacy_ms_litellm 改用自写 ms-gateway 代码, 41001 链路保留

## Dockerfile 改动 (两机对称, 7 个 Dockerfile)
| 容器 | 旧 FROM | 新 FROM |
|---|---|---|
| nv_gw | ghcr.io/berriai/litellm:v1.83.14-stable.patch.1 | python:3.12-slim + PySocks + psycopg2-binary |
| ms_gw | python:3.11-slim (HM1) / litellm/litellm:v1.87.0 (HM2) | python:3.12-slim |
| legacy-ms-gateway | python:3.11-alpine | python:3.12-slim |
| legacy-cc/codex/dispatcher/passthrough | ghcr.io/berriai/litellm:v1.83.14-stable.patch.1 | python:3.12-slim |

## HM2 特有
- legacy_ms_litellm: 之前 R680 用 litellm/litellm:v1.87.0 image (避 docker.io 墙), 现改回 build 自写代码 + python:3.12-slim (mihomo 代理拉)
- compose: 5 个 legacy auth 从 image retag 恢复 build 模式 (Dockerfile 不再依赖 docker.io base)
- legacy_ms_litellm 从 image: litellm/litellm:v1.87.0 恢复 build context: legacy-ms-gateway

## 验证 (两机)
- 9 容器全 healthy
- nv_gw: python 3.12.13, PySocks+psycopg2 装好, DB 连接 OK (HM1 11803条, HM2 17313条), /health OK
- legacy_ms_litellm (HM2): 跑自写 ms-gateway 代码, 日志 "ms-gateway listening on 0.0.0.0:4000"
- 三 agent 全 active (HM1: hermes/openclaw/opencode-web; HM2: hermes-gateway/openclaw-gateway/opencode-webui)

## 状态
**彻底摒弃 litellm**: 所有容器不再 FROM litellm image, 不依赖 litellm 库。Python 统一 3.12-slim。镜像大幅瘦身。
