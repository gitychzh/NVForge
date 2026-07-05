#!/usr/bin/env python3
"""简单 logger, 复用 nv_gw 风格 (stdout JSONL)."""
import os
import json
import datetime
import sys

LOG_DIR = os.environ.get("LOG_DIR", "/app/logs")


def _ts():
    return datetime.datetime.now().isoformat()


def _log(tag, msg, **extra):
    """结构化日志, stdout JSONL."""
    rec = {"ts": _ts(), "tag": tag, "msg": msg}
    if extra:
        rec.update(extra)
    try:
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    except Exception:
        print(f'{{"ts":"{_ts()}","tag":"{tag}","msg":"{msg}"}}', flush=True)


def _log_error_detail(rec):
    """错误详情写 JSONL 文件."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        path = os.path.join(LOG_DIR, "hm_error_detail.jsonl")
        with open(path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:
        _log("LOG-ERR", f"failed to write error detail: {e}")
