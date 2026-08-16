#!/usr/bin/env bash
# sync_core.sh — R-decouple: 共享通用文件同步脚本
#
# 三个 NV 网关容器 (40006/40066/40666) 解耦后各自有独立 gateway/ 目录。
# 通用文件 (rr_counter, cooldown, nvcf_conn, pexec, func_health, db, logger, ...)
# 在三个目录间需保持一致 (修复 bug 时一改三)。
# 模型特定文件 (config.py, upstream.py, handlers.py, buffer_stream.py, glm52_mode_idx.py)
# 不由本脚本同步 — 各目录独立维护。
#
# 用法:
#   ./sync_core.sh                 # 从 nv-gw (40006) 同步到 dsv4p + dsv4f0731
#   ./sync_core.sh --diff          # 只显示差异, 不同步
#   ./sync_core.sh --from dsv4p    # 从 dsv4p 同步到 nv-gw + dsv4f0731 (反向同步)
#
# 安全: 同步前自动 diff 检查 + 确认; 带自动备份 (.bak.sync.<timestamp>)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_DIR=""
MODE="sync"  # sync or diff
SOURCE_NAME="nv-gw"

# 通用文件清单 (模型无关, 三目录共享)
CORE_FILES=(
    "__init__.py"
    "app.py"
    "rr_counter.py"
    "cooldown.py"
    "nvcf_conn.py"
    "pexec.py"
    "func_health.py"
    "db.py"
    "logger.py"
    "error_mapping.py"
    "nv_breaker.py"
    "big_input_breaker.py"
    "key_manager.py"
    "probe_worker.py"
    "stream_success_judge.py"
    "fid_discovery.py"
    # config.py / upstream.py / handlers.py / buffer_stream.py / glm52_mode_idx.py
    # 是模型相关的, 不同步 — 各目录独立维护
)

# 目标目录
TARGET_DIRS=("nv-gw-dsv4p" "nv-gw-dsv4f0731")

# 解析参数
while [[ $# -gt 0 ]]; do
    case "$1" in
        --diff)  MODE="diff"; shift ;;
        --from)  SOURCE_NAME="$2"; shift 2 ;;
        *)       echo "Unknown arg: $1"; exit 1 ;;
    esac
done

SOURCE_DIR="${SCRIPT_DIR}/${SOURCE_NAME}/gateway"
if [[ ! -d "${SOURCE_DIR}" ]]; then
    echo "ERROR: source dir not found: ${SOURCE_DIR}"
    exit 1
fi

echo "=== sync_core.sh — R-decouple 通用文件同步 ==="
echo "Source: ${SOURCE_NAME}/gateway"
echo "Mode:   ${MODE}"
echo "Files:  ${#CORE_FILES[@]} core files"
echo ""

TS=$(date +%Y%m%d_%H%M%S)
TOTAL_DIFFS=0

for target_dir in "${TARGET_DIRS[@]}"; do
    if [[ "${target_dir}" == "${SOURCE_NAME}" ]]; then
        continue
    fi
    TARGET="${SCRIPT_DIR}/${target_dir}/gateway"
    if [[ ! -d "${TARGET}" ]]; then
        echo "WARN: target dir not found: ${TARGET}, skipping"
        continue
    fi

    echo "--- ${target_dir}/gateway ---"
    for f in "${CORE_FILES[@]}"; do
        src_file="${SOURCE_DIR}/${f}"
        tgt_file="${TARGET}/${f}"

        if [[ ! -f "${src_file}" ]]; then
            echo "  SKIP ${f} (not in source)"
            continue
        fi

        if [[ ! -f "${tgt_file}" ]]; then
            echo "  COPY ${f} (not in target → copy new)"
            if [[ "${MODE}" == "sync" ]]; then
                cp -a "${src_file}" "${tgt_file}"
            fi
            continue
        fi

        if ! diff -q "${src_file}" "${tgt_file}" >/dev/null 2>&1; then
            if [[ "${MODE}" == "diff" ]]; then
                echo "  DIFF ${f}:"
                diff --brief "${src_file}" "${tgt_file}"
                TOTAL_DIFFS=$((TOTAL_DIFFS + 1))
            else
                # 备份 + 同步
                cp -a "${tgt_file}" "${tgt_file}.bak.sync.${TS}"
                cp -a "${src_file}" "${tgt_file}"
                echo "  SYNC ${f} (backup: ${f}.bak.sync.${TS})"
            fi
        else
            echo "  OK   ${f}"
        fi
    done
    echo ""
done

if [[ "${MODE}" == "diff" ]]; then
    echo "=== Summary: ${TOTAL_DIFFS} file(s) differ ==="
    if [[ ${TOTAL_DIFFS} -gt 0 ]]; then
        echo "Run without --diff to sync."
    fi
else
    echo "=== Done. Restart containers to apply: ==="
    echo "  cd /opt/cc-infra && docker compose restart nv_gw dsv4p_nv40066 dsvf0731_nv40666"
fi
