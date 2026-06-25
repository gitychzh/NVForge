#!/bin/bash
# ============================================================
# 交替优化轮询脚本
# 运行位置: 两台机器各部署一份
# 逻辑:
#   - 定时 git pull
#   - 检查最新 round_N.md 中的 "轮到XX优化XX" 标记
#   - 如果是"轮到我了"，输出信号给Hermes Cron
# ============================================================

REPO_DIR="$HOME/hm_ps/hermes_improve_self"
ROUNDS_DIR="$REPO_DIR/rounds"
MY_ROLE="${MY_ROLE:-HM1}"  # 通过环境变量传入

cd "$REPO_DIR" || exit 1

# 拉取最新
git pull --ff-only origin main 2>/dev/null

# 找到最新的轮次文件
LATEST_ROUND=$(ls -1t "$ROUNDS_DIR"/R*_*.md 2>/dev/null | head -1)

if [ -z "$LATEST_ROUND" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 无轮次记录, 未被分配到。"
    exit 0
fi

# 提取最后一行 (检查是否 "轮到XX优化XX")
LAST_LINE=$(tail -1 "$LATEST_ROUND")

# 从文件名提取当前轮次
FILENAME=$(basename "$LATEST_ROUND")
ROUND_NUM=$(echo "$FILENAME" | grep -oP 'R\d+' | head -1)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 最新: $FILENAME | 最后行: $LAST_LINE"

# 如果最后一行是 "轮到HM2优化HM1" → 看我是谁
if echo "$LAST_LINE" | grep -q "轮到.*优化"; then
    TARGET=$(echo "$LAST_LINE" | grep -oP '(?<=轮到)(HM\d)(?=优化(HM\d))')
    DST=$(echo "$LAST_LINE" | grep -oP '(?<=优化)(HM\d)(?!优化)')
    
    # 我是否该行动?
    if [ "$TARGET" = "$MY_ROLE" ]; then
        echo "ACTION: 轮到我优化 $DST 了！"
        exit 0  # 返回0 → cron触发优化流程
    else
        echo "等待: 当前轮到 $TARGET , 我是 $MY_ROLE , 继续等待"
        exit 1  # 返回1 → cron不触发
    fi
fi

# 如果最后一行是完成标记
if echo "$LAST_LINE" | grep -q "R.*完成"; then
    echo "状态: 最后一轮已完成，下一轮待开始"
    exit 0
fi

echo "状态: 未识别标记"
exit 1