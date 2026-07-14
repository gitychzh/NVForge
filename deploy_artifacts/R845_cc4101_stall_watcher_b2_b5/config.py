#!/usr/bin/env python3
"""Configuration constants and environment variables for cc4101.

R684: Clean config for a CC-dedicated glm5.2 proxy. No v×k cycling, no NV tiers,
no MS-NV interleaving. Just: two upstreams (primary + fallback), always stream,
auth token, DB settings.

All configurable parameters are read from env vars with defaults.
"""
import os
import threading

# ─── Network ──────────────────────────────────────────────────────────────
# Listen on all in-container interfaces; the docker-compose `ports:` mapping is
# what controls off-host exposure (published as 127.0.0.1:4101:4101 there so
# only the host loopback can reach it — see compose, R690).
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "4101"))
UPSTREAM_TIMEOUT = int(os.environ.get("UPSTREAM_TIMEOUT", "30"))  # R829: connect+header总超时(死连接快速放弃). R830语义澄清: 此值只管connect+getresponse(), body read改用UPSTREAM_IDLE_TIMEOUT.
UPSTREAM_IDLE_TIMEOUT = int(os.environ.get("UPSTREAM_IDLE_TIMEOUT", "150"))  # R830: body read idle超时(两次chunk间隔). 对齐nv_gw [NV-THINKING-TIMEOUT]150s, 容纳thinking静默期. 与UPSTREAM_TIMEOUT分离: 后者管死连接快断, 本值管长思考不误杀.
# R845 B7: stream stall-watcher 双门槛 (总时长+idle). per-read socket timeout(UPSTREAM_IDLE_TIMEOUT=150s)
# 被 keep-alive drip 绕过即失明 (a1db6f13: 上游120.8s断连, 150s没触发, cc4101连检查点都没有).
# 解法: per-read 改用短轮询 CC4101_STREAM_POLL_S, read 每次最多阻塞这么久就抛 socket.timeout,
# 在 except 里不立即break, 而是检查双门槛: 总时长超限 or idle间隙超限. 阈值见下.
CC4101_STREAM_TOTAL_DEADLINE_S = float(os.environ.get("CC4101_STREAM_TOTAL_DEADLINE_S", "180"))  # ttfb后绝对总时长兜底, 防无限挂. 高于正常长思考(避免误杀); 只兜纯挂死.
CC4101_STREAM_IDLE_GAP_S = float(os.environ.get("CC4101_STREAM_IDLE_GAP_S", "60"))  # 无真内容(content/reasoning/tool_call)的idle间隙上限. 持续产出时last_progress_time更新不触发.
CC4101_STREAM_POLL_S = float(os.environ.get("CC4101_STREAM_POLL_S", "30"))  # per-read socket timeout(短轮询获取检查点). 原UPSTREAM_IDLE_TIMEOUT(150s)退为总预算语义, 不再作per-read.
# R822: header/TTFB timeout — connect + time-to-response-header. Shorter than full
# UPSTREAM_TIMEOUT so a cycling upstream (ms_gw glm5_2_ms choices_null storm) fails
# fast instead of hanging 120s for getresponse(). Body read still uses UPSTREAM_TIMEOUT.
UPSTREAM_HEADER_TIMEOUT = int(os.environ.get("UPSTREAM_HEADER_TIMEOUT", "12"))
# R823: per-stage header timeouts. primary (nv_gw) empty200 cycle takes ~60s to
# fully fail; 15s is enough to detect a non-fast-success round and let fallback
# (the more reliable path when MS is not storming) take over. fallback (ms_gw)
# does 7-key RR with 3s 429-backoff each; under collective rate-limit that is
# ~18s before a warm key is found, so 12s guarantees a false timeout -> 30s lets
# it actually find a usable key. These override UPSTREAM_HEADER_TIMEOUT per stage.
# R823: primary 15s. R824 调: 实测大上下文(tools=30,msgs=20+)请求 primary TTFB 9-14.3s,
# 15s 把 15-20s 区间的请求误杀切 fallback(整体 20-45s 浪费). 抬到 22s 救回这批请求.
# empty200 单key降级由 R824 nv_gw 内部 threshold=3 + key cooldown 处理, 22s 不放大 empty200 卡死.
PRIMARY_HEADER_TIMEOUT = int(os.environ.get("PRIMARY_HEADER_TIMEOUT", "25"))  # R828: 45->25. R827后走integrate实测3-14s, 25s覆盖p90留余量, 超时切fallback  # R825: 48->8 紧急止血. glm5_2_nv NVCF function 3b9748d8 服务端整体故障(实测60s无响应/42s极慢), 48s让每请求白等48s才切fallback致claude卡死(msgs 130->166停滞18min). 降8s让primary死得快早切glm5_2_ms(实测6.8s 200). nv_gw恢复后调回22-48. R824c原值48基于p90=47.8s, 故障期不适用.
FALLBACK_HEADER_TIMEOUT = int(os.environ.get("FALLBACK_HEADER_TIMEOUT", "30"))
# R823: total request budget across all stages (primary + fallback + primary_retry).
# Prevents the R822 three-stage chain from amplifying to 36s+ of pure timeouts when
# both upstreams are rate-limited/empty-flowing simultaneously. When remaining
# budget is too small for another stage, skip it and fail fast.
# R824: 60→70. primary 22s + fallback 30s + primary_retry 22s = 74s, 70s 让 retry 在预算不足时跳过.
CC4101_TOTAL_BUDGET_S = int(os.environ.get("CC4101_TOTAL_BUDGET_S", "80"))  # R824b: 70->80
# R822: retry primary once after fallback fails (primary often recovers faster than
# a storming fallback). Disable with RETRY_PRIMARY_AFTER_FALLBACK=0.
RETRY_PRIMARY_AFTER_FALLBACK = os.environ.get("RETRY_PRIMARY_AFTER_FALLBACK", "1") == "1"

# R824d: primary circuit breaker. When nv_gw (primary) is in a sustained degraded
# state (glm5_2_nv NVCF empty200 storm, or a key-tier-wide outage), every request
# burns PRIMARY_HEADER_TIMEOUT (~48s) before falling back — wasting ~48s/req and
# hammering a sick upstream. The breaker short-circuits primary after N consecutive
# failures, routing straight to fallback for a cooldown, then re-probes primary.
# States: CLOSED (normal) -> OPEN (skip primary) -> HALF_OPEN (one probe) -> CLOSED/OPEN.
# Threshold/skip are conservative: 3 fails to open (avoids opening on a single NVCF
# hiccup), 120s cooldown (covers a typical empty200 storm window of 5-15min). Tunable
# via env. Disable by setting CC4101_PRIMARY_FAIL_THRESHOLD=0.
CC4101_PRIMARY_FAIL_THRESHOLD = int(os.environ.get("CC4101_PRIMARY_FAIL_THRESHOLD", "5"))
CC4101_PRIMARY_SKIP_S = int(os.environ.get("CC4101_PRIMARY_SKIP_S", "60"))

# ─── Role ─────────────────────────────────────────────────────────────────
PROXY_ROLE = os.environ.get("PROXY_ROLE", "cc4101")
HOST_MACHINE = os.environ.get("CC4101_HOST_MACHINE") or os.environ.get("HOSTNAME") or "unknown"

# ─── Upstreams ────────────────────────────────────────────────────────────
# Primary: nv_gw (glm5_2_nv). Fallback: ms_gw (glm5_2_ms).
# R704: fallback 改 dsv4p_ms (与 hermes 回退链一致). R805: 改回 glm5_2_ms (NV glm5.2 DEGRADED 期,
# dsv4p_ms 同链路也降级; 同模型 glm5_2_ms 经 ms_gw ModelScope 链路更稳, compose env 实配此值).
# 注释与 config.py default 对齐 R805; default 值也同步, 防 env 丢失时落到过时 dsv4p_ms.
# URLs are full chat-completions endpoints (http://nv_gw:40006/v1/chat/completions).
PRIMARY_UPSTREAM_URL = os.environ.get("PRIMARY_UPSTREAM_URL", "http://nv_gw:40006/v1/chat/completions")
PRIMARY_UPSTREAM_MODEL = os.environ.get("PRIMARY_UPSTREAM_MODEL", "glm5_2_nv")
PRIMARY_UPSTREAM_TOKEN = os.environ.get("PRIMARY_UPSTREAM_TOKEN", "nv-gw-token")

FALLBACK_UPSTREAM_URL = os.environ.get("FALLBACK_UPSTREAM_URL", "http://ms_gw:40007/v1/chat/completions")
FALLBACK_UPSTREAM_MODEL = os.environ.get("FALLBACK_UPSTREAM_MODEL", "glm5_2_ms")  # R805: dsv4p_ms -> glm5_2_ms
FALLBACK_UPSTREAM_TOKEN = os.environ.get("FALLBACK_UPSTREAM_TOKEN", "ms-gw-token")

# ─── Auth (gateway-side, for CC → cc4101) ─────────────────────────────────
CC4101_GATEWAY_API_KEY = os.environ.get("CC4101_GATEWAY_API_KEY", "cc4101-token")
AUTH_ENABLED = os.environ.get("AUTH_ENABLED", "1") == "1"

# ─── Truncation / estimation ──────────────────────────────────────────────
MAX_TOOL_DESC = int(os.environ.get("MAX_TOOL_DESC", "2000"))
MAX_SCHEMA_DESC = int(os.environ.get("MAX_SCHEMA_DESC", "600"))
CHARS_PER_TOKEN_ESTIMATE = float(os.environ.get("CHARS_PER_TOKEN_ESTIMATE", "3.0"))

# ─── Thinking signature (Anthropic thinking block requires a signature) ───
THINKING_SIGNATURE_DEFAULT = os.environ.get(
    "THINKING_SIGNATURE",
    "ErUB3WY0k2GCM2h+4O0S3Y3W3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f3Y3f",
)

# ─── Frontend model (what /v1/models advertises to CC) ────────────────────
# CC sends "claude-opus-4-8" or any name; we map everything to the primary
# upstream model. /v1/models lists one canonical name.
CC_FRONTEND_MODEL = os.environ.get("CC_FRONTEND_MODEL", "cc-glm5-2")
MODEL_INPUT_TOKEN_SAFETY = int(os.environ.get("MODEL_INPUT_TOKEN_SAFETY", "170000"))

# ─── Logging ──────────────────────────────────────────────────────────────
LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")
LOG_RETENTION_DAYS = int(os.environ.get("LOG_RETENTION_DAYS", "14"))


# ─── Model name mapping ──────────────────────��────────────────────────────
# cc4101 only serves glm5.2. Any model name CC sends maps to PRIMARY_UPSTREAM_MODEL.
# We keep a MODEL_MAP for explicit names but everything routes to the same backend.
MODEL_MAP = {
    CC_FRONTEND_MODEL: PRIMARY_UPSTREAM_MODEL,
    "glm5.2": PRIMARY_UPSTREAM_MODEL,
    "glm-5.2": PRIMARY_UPSTREAM_MODEL,
    "zhipuai/glm-5.2": PRIMARY_UPSTREAM_MODEL,
    # Claude Code names → glm5.2
    "claude-opus-4-8": PRIMARY_UPSTREAM_MODEL,
    "claude-opus-4-7": PRIMARY_UPSTREAM_MODEL,
    "claude-opus-4": PRIMARY_UPSTREAM_MODEL,
    "claude-sonnet-4-6": PRIMARY_UPSTREAM_MODEL,
    "claude-sonnet-4": PRIMARY_UPSTREAM_MODEL,
    "claude-haiku-4-5": PRIMARY_UPSTREAM_MODEL,
    "claude-sonnet-4-20250514": PRIMARY_UPSTREAM_MODEL,
    "claude-opus-4-20250514": PRIMARY_UPSTREAM_MODEL,
    "claude-opus-4-8-20250514": PRIMARY_UPSTREAM_MODEL,
    "claude-haiku-4-5-20251001": PRIMARY_UPSTREAM_MODEL,
    "claude-3-5-sonnet-20241022": PRIMARY_UPSTREAM_MODEL,
    "claude-3-5-haiku-20241022": PRIMARY_UPSTREAM_MODEL,
    "claude-3-opus-20240229": PRIMARY_UPSTREAM_MODEL,
}


def map_model(requested_model):
    """Map any client-supplied model name to the upstream model id.

    Returns the upstream model id (str). Unknown names → primary upstream model
    (cc4101 is glm5.2-only; we never reject a model name, we just route to glm5.2).
    """
    if not requested_model:
        return PRIMARY_UPSTREAM_MODEL
    return MODEL_MAP.get(requested_model, PRIMARY_UPSTREAM_MODEL)


# ─── Thread locks for logging ─────────────────────────────────────────────
_log_lock = threading.Lock()
_metrics_lock = threading.Lock()
_error_detail_lock = threading.Lock()
