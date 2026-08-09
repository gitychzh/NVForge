#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
normalize_rounds.py — NVForge round 文件名规范化工具 (R-normalize-2026-08-09)

将 rounds/ 下 3600+ 个历史文件名统一到标准:
    rounds/R<seq>-<loop>-<desc>.md
其中 <seq> 是 loop 自身的计数器 (每个 loop 独立, loop 名消歧),
<loop> 是规范化 loop 标识符, <desc> 是短 kebab-case 描述 (可省略).

用法:
    python3 scripts/normalize_rounds.py --dry-run          # 只输出映射计划, 不移动
    python3 scripts/normalize_rounds.py --apply            # 执行重命名 (git 友好)
    python3 scripts/normalize_rounds.py --map              # 只输出 _rename_map.csv

安全:
    - --dry-run 前必跑; 冲突文件会列出, 不会自动覆盖
    - 输出 rounds/_rename_map.csv (旧名,新名) 供追溯与 .md 交叉引用批量替换
    - 不修改任何文件内容, 只做 git mv / os.rename
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

ROUNDS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rounds")
MAP_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rounds", "_rename_map.csv")

# ---------------------------------------------------------------------------
# loop 标识符映射 (把多种历史命名归一到一个 loop 名)
# ---------------------------------------------------------------------------
LOOP_ALIASES = [
    # (regex, loop). 按优先级从高到低匹配
    (re.compile(r"hm2_cc2_nop_r\d+"), "cc2"),          # R1991_hm2_cc2_nop_r101
    (re.compile(r"_dsv4f0731_self_opt_nop$"), "dsv4f0731"),
    (re.compile(r"_dsvf0731_self_opt(_nop)?$"), "dsv4f0731"),
    (re.compile(r"^RN\d+_dsv4f"), "dsv4f"),            # RN1006_dsv4f_nop_data_ok
    (re.compile(r"^RN\d+_dsv4p"), "dsv4p"),
    (re.compile(r"^RN\d+_dsvf"), "dsv4f"),
    (re.compile(r"_dsv4f_"), "dsv4f"),
    (re.compile(r"_dsv4p_"), "dsv4p"),
    (re.compile(r"_hm2_optimize_hm1$"), "hm2opt"),
    (re.compile(r"^cc2_R"), "cc2"),
    (re.compile(r"_cc2_"), "cc2"),
    (re.compile(r"_cc$"), "cc"),
    (re.compile(r"^R-nvonly"), "nvonly"),
    (re.compile(r"_buffer_|^R_buffer|^R-buffer"), "buffer"),
    (re.compile(r"_keyretry|^R-keyretry"), "keyretry"),
    (re.compile(r"_glm52|^R-glm52"), "glm52"),
    (re.compile(r"_legacy"), "legacy"),
    (re.compile(r"_openclaw|^R-openclaw"), "openclaw"),
    (re.compile(r"^RN"), "rn"),
]

# ---------------------------------------------------------------------------
# 解析器: 从文件名提取 (loop, seq, desc)
# ---------------------------------------------------------------------------

def find_loop(name):
    """找 loop 标识符。返回 (loop,) 或 (loop, matchobj)。"""
    stem = name[:-3] if name.endswith(".md") else name
    for rx, loop in LOOP_ALIASES:
        m = rx.search(stem)
        if m:
            return loop, m
    return None, None


def parse(name):
    """解析文件名 → (loop, seq, desc) 或 None(无法识别 → 保留原样)."""
    stem = name[:-3] if name.endswith(".md") else name
    if not stem or stem.startswith("STATE") or stem.startswith("_rename") or stem.startswith("README"):
        return None  # 非 round 文件, 跳过

    loop, m = find_loop(name)

    # 提取 seq
    seq = None
    # 1) R<digits> 前缀 (R1234, RN1234, cc2_R1234)
    #    注意: 不能用 \b 结尾 — _ 是 word char, "1190_" 之间无 boundary。
    #    用 (?!\d) 拒绝被更长数字吞掉 (R1000 不应匹配出 000).
    mseq = re.search(r"\bR(?:N)?(\d+)(?!\d)", stem)
    if mseq:
        seq = int(mseq.group(1))

    # 提取 desc: 去掉 seq 与 loop 标记后的剩余, 转 kebab
    remaining = stem
    # 去掉 R<digits> 前缀
    remaining = re.sub(r"^R(?:N)?\d+_?", "", remaining)
    # 去 loop 标记
    remaining = re.sub(r"hm2_optimize_hm1", "", remaining)
    remaining = re.sub(r"dsv4f0731_self_opt_nop", "", remaining)
    remaining = re.sub(r"dsvf0731_self_opt(?:_nop)?", "", remaining)
    remaining = re.sub(r"nvonly_post\d+_", "", remaining)
    remaining = re.sub(r"cc2_R\d+_?", "", remaining)
    remaining = re.sub(r"cc2_nop", "", remaining)
    remaining = re.sub(r"cc2_nv_gw", "nv-gw", remaining)
    remaining = re.sub(r"buffer_post\d+_", "", remaining)
    remaining = re.sub(r"keyretry_post\d+_", "", remaining)
    remaining = re.sub(r"_", "-", remaining)
    remaining = re.sub(r"-{2,}", "-", remaining)
    remaining = remaining.strip("-").lower()
    desc = remaining if remaining else None

    if loop is None:
        # 无 loop 标记 → 主题 loop (用首词)
        first = re.sub(r"^R-?", "", stem).split("_")[0].split("-")[0]
        loop = first.lower() if first else "round"

    return loop, seq, desc


def build_target(loop, seq, desc, orig):
    """构造目标文件名 R<seq>-<loop>[-<desc>].md"""
    parts = []
    if seq is not None:
        parts.append(f"R{seq}")
    else:
        parts.append("R")
    parts.append(loop)
    if desc:
        parts.append(desc)
    return "-".join(parts) + ".md"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="只打印计划, 不移动")
    ap.add_argument("--apply", action="store_true", help="执行重命名")
    ap.add_argument("--map", action="store_true", help="只输出 _rename_map.csv")
    args = ap.parse_args()

    files = sorted(os.listdir(ROUNDS_DIR))
    rows = []          # (orig, target)
    unresolved = []    # (orig, reason)
    seen_targets = defaultdict(list)

    for f in files:
        if not f.endswith(".md"):
            continue
        parsed = parse(f)
        if parsed is None:
            continue
        loop, seq, desc = parsed
        target = build_target(loop, seq, desc, f)
        if target == f:
            continue  # 已符合, 跳过
        rows.append((f, target))
        seen_targets[target].append(f)

    # 冲突检测
    conflicts = {t: srcs for t, srcs in seen_targets.items() if len(srcs) > 1}

    if args.map or args.dry_run or args.apply:
        print(f"# 待改名: {len(rows)} 文件, 冲突: {len(conflicts)} 组\n")
        if conflicts:
            print("## 冲突目标 (需人工处理):")
            for t, srcs in sorted(conflicts.items()):
                print(f"  {t}  <-  {srcs}")
            print()

    if args.map:
        with open(MAP_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["old", "new"])
            for orig, target in rows:
                w.writerow([orig, target])
        print(f"# 已写出 {MAP_CSV} ({len(rows)} 行)")

    if args.dry_run:
        print("## 干跑计划 (前 40 条):")
        for orig, target in rows[:40]:
            print(f"  {orig}  ->  {target}")
        print(f"\n... 共 {len(rows)} 条。冲突 {len(conflicts)} 组。")

    if args.apply:
        if conflicts:
            print("!! 存在冲突, 中止 (先 --dry-run 处理冲突)。")
            sys.exit(1)
        moved = 0
        for orig, target in rows:
            src = os.path.join(ROUNDS_DIR, orig)
            dst = os.path.join(ROUNDS_DIR, target)
            if os.path.exists(dst):
                print(f"!! dst 已存在, 跳过: {target}")
                continue
            os.rename(src, dst)
            moved += 1
        print(f"# 已重命名 {moved} 文件。")
        # 写 rename map
        with open(MAP_CSV, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["old", "new"])
            for orig, target in rows:
                w.writerow([orig, target])
        print(f"# 已写出 {MAP_CSV}")


if __name__ == "__main__":
    main()