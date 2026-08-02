#!/usr/bin/env python3
"""超时策略 — 从 upstream.py 拆出 (R-modref).

按输入大小返回 header timeout, 6 档 (R2154/R2202/R2197).
primary 和 fallback 分档不同 (ms_gw 更慢, 多留余量).

改超时策略 = 只动本文件.
"""
import json

from .config import PRIMARY_HEADER_TIMEOUT


def get_primary_header_timeout(oai_body, override=None):
    """R2154/R2202/R2197: 按输入大小返回 primary header timeout.

    分档表 (chars → seconds):
      <30K     → 25   (死连快断)
      30-50K   → 40   (中等请求偶发慢)
      50-90K   → 150  (nv_gw first-byte 60s + 90s 余量, p99 141s)
      90-150K  → 160  (nv_gw first-byte 60s 先 break, 160s 兜底真 NVCF 慢 p99 142-246s)
      150-200K → 180  (R2202: NVCF 120-142s ttfb 踩 120s 线致 499, 180s 覆盖)
      200-350K → 180  (R2197: 同 R2202 根因延伸)
      >350K    → 120  (同)

    override 非 None 时强制用此值 (R-cc_s3 阶梯超时探测用).
    """
    if override is not None:
        return override
    _hdr_ic = len(json.dumps(oai_body, ensure_ascii=False)) if oai_body else 0
    if _hdr_ic > 350000:
        return 120
    elif _hdr_ic > 200000:
        return 180
    elif _hdr_ic > 150000:
        return 180
    elif _hdr_ic > 90000:
        return 160
    elif _hdr_ic > 50000:
        return 150
    elif _hdr_ic > 30000:
        return 40
    else:
        return PRIMARY_HEADER_TIMEOUT


def get_fallback_header_timeout(oai_body, override=None):
    """Fallback (ms_gw) header timeout 分档.

    ms_gw 不走 nv first-byte 倒挂问题, 但分档粗同样砍慢请求.
    50-150K 给 120s (ms 比 nv 慢, 多留余量).
    """
    if override is not None:
        return override
    _hdr_ic = len(json.dumps(oai_body, ensure_ascii=False)) if oai_body else 0
    if _hdr_ic > 350000:
        return 120
    elif _hdr_ic > 200000:
        return 120
    elif _hdr_ic > 150000:
        return 120
    elif _hdr_ic > 90000:
        return 120
    elif _hdr_ic > 50000:
        return 120
    elif _hdr_ic > 30000:
        return 60
    else:
        return PRIMARY_HEADER_TIMEOUT
