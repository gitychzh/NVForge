#!/usr/bin/env python3
"""cc-adapter 配置. 全部 env-overridable. 不持 key (转发到 nv_gw/ms_gw).

一个镜像服务 3 个容器 (opclaw4103/hm4104/oc4105), 区别仅在 env:
  ADAPTER_NAME: 容器名 (日志/health 标识)
  PRIMARY_URL/PRIMARY_MODEL: 主后端 (nv_gw:40006)
  FALLBACK_URL/FALLBACK_MODEL: 备后端 (ms_gw:40007), oc4105 设 FALLBACK_ENABLED=0 禁用
"""
import os

# ─── Network ──────────────────────────────────────────────────────────────
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "4103"))
PROXY_TIMEOUT = int(os.environ.get("PROXY_TIMEOUT", "300"))

# ─── 身份 ─────────────────────────────────────────────────────────────────
ADAPTER_NAME = os.environ.get("ADAPTER_NAME", "opclaw4103")
ADAPTER_ROLE = os.environ.get("ADAPTER_ROLE", "cc-adapter")  # chat-completions 透传 + fallback

# ─── 后端路由 (adapter 不做 key 轮转, 转发到 nv_gw/ms_gw) ───────────────
PRIMARY_URL = os.environ.get("PRIMARY_URL", "http://nv_gw:40006/v1")
FALLBACK_URL = os.environ.get("FALLBACK_URL", "http://ms_gw:40007/v1")
PRIMARY_MODEL = os.environ.get("PRIMARY_MODEL", "glm5_2_nv")
FALLBACK_MODEL = os.environ.get("FALLBACK_MODEL", "glm5_2_ms")

# ─── fallback 开关 (oc4105 设 0, 无 fallback) ────────────────────────────
FALLBACK_ENABLED = os.environ.get("FALLBACK_ENABLED", "1") == "1"

# ─── fallback 触发条件 ─────────────────────────────────────────────────────
FALLBACK_TIMEOUT_S = float(os.environ.get("FALLBACK_TIMEOUT_S", "300"))  # 整体 socket 超时上限
# primary 流式首响应超时 (响应头/首字节). 到点没拿到就切 fallback, 不等 FALLBACK_TIMEOUT_S
PRIMARY_STREAM_TIMEOUT_S = float(os.environ.get("PRIMARY_STREAM_TIMEOUT_S", "60"))
CIRCUIT_FAILURE_THRESHOLD = int(os.environ.get("CIRCUIT_FAILURE_THRESHOLD", "3"))
CIRCUIT_OPEN_S = int(os.environ.get("CIRCUIT_OPEN_S", "60"))
FALLBACK_RECOVER_S = int(os.environ.get("FALLBACK_RECOVER_S", "30"))

# ─── 鉴权 (adapter 自己的 token, 与 nv_gw/ms_gw token 解耦) ──────────────
ADAPTER_API_KEY = os.environ.get("ADAPTER_API_KEY", "cc-adapter-token")
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "1") == "1"

# ─── 上游 key (adapter 用 nv-gw-token / ms-gw-token 访问后端) ───────────
NV_GW_API_KEY = os.environ.get("NV_GW_API_KEY", "nv-gw-token")
MS_GW_API_KEY = os.environ.get("MS_GW_API_KEY", "ms-gw-token")

# ─── 日志 ──────────────────────────────────────────────────────────────────
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")

# ─── 提醒文案 (fallback 时插入响应, 不中断 agent 任务) ──────────────────
FALLBACK_NOTICE = os.environ.get(
    "FALLBACK_NOTICE",
    "⚠️ [{name}] primary 故障/超时, 已 fallback 到 {fb_model}. 本轮继续, 下一轮回 primary. ({name} fallback)"
).format(name=ADAPTER_NAME, fb_model=FALLBACK_MODEL)

# ─── R766: openclaw 兜底 (默认禁用, 仅 opclaw4103 启用) ─────────────────
# prompt token 估算超此值直接返回 400 (不转发 NVCF), 避免 openclaw Context overflow 后 retry 累积超时
PROMPT_TOKEN_LIMIT = int(os.environ.get("PROMPT_TOKEN_LIMIT", "0"))  # 0=禁用
# 流式 content=null 但有 reasoning_content 时, 流末补 content=reasoning 全文
SUPPLEMENT_REASONING_AS_CONTENT = os.environ.get("SUPPLEMENT_REASONING_AS_CONTENT", "0") == "1"
