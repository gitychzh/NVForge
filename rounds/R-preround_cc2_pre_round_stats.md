# R-preround-cc2: cc2 轮前统计分析注入 prompt + 飞书通知集成

**日期**: 2026-07-31
**主机**: HM2
**改动者**: CC (基础设施)

## 背景

继 openclaw2 的轮前统计注入成功后, 将同样的机制应用到 cc2 自优化定时任务。
cc2 走 cc4101 adapter (port 4101), caller=cc4101-primary, 与 openclaw2 的 caller=openclaw2 不同,
因此 pre_round_stats 聚焦 cc4101-primary 视角。

## 改动

### 1. pre_round_stats.py (新增)
- 路径: `~/cc_ps/cc2_repair_self/.claude/pre_round_stats.py`
- 功能: 每轮 claude 启动前从 hermes_logs DB 拉 30min 链路数据
- 数据维度 (比 openclaw2 版多 2 段):
  - 当前配置 (nv_gw + cc4101 双容器 env 快照)
  - 30min 按 caller×model×status 总览
  - 30min 按模型 SR
  - **30min cc4101-primary 专属** (cc2 自己的请求 status×count×avg_dur×errors)
  - 30min 错误分类
  - 30min per-key×status (dsv4p)
  - 30min per-egress-IP (dsv4p)
  - 30min dsv4p 200 延迟/Token
  - 30min finish_reason 分布 (zombie 诊断)
  - 30min fallback 发生率
  - 30min nv_tier_attempts per-key
  - 30min 按分钟趋势
  - 2h SR 趋势 (10min 桶)
  - **30min nv_gw buffer/wait/keymanager 日志摘要** (最后20行)
  - 自动分析要点 (SR 评级 + top error + cc4101-primary 专属错误)

### 2. feishu_notify.py (新增)
- 路径: `~/cc_ps/cc2_repair_self/.claude/feishu_notify.py`
- 和 openclaw2 共用飞书群 `openclaw2_improve_self`
- 标题用 `[cc2]` 前缀区分, openclaw2 用 `[openclaw2]`
- 内容: 轮号 + 30min SR (cc4101-primary) + 错误分类 + STATE.md 摘要 + timer 状态

### 3. cc2_resume.sh (修改)
- 轮前调用 `pre_round_stats.py`, 输出写 `/tmp/cc2_pre_round_report.txt`
- 通过 `$(cat /tmp/cc2_pre_round_report.txt)` 安全注入 prompt 末尾
- prompt 第二步更新: "数据已注入, 无需重复查询"
- 轮后加 `feishu_notify.py` 调用 (在 R-guard 之后, exit 0 之前)

## 工作流 (改后)

```
cc2-resume.timer (30sec)
  → cc2-resume.service (oneshot, 300s timeout)
    → cc2_resume.sh
      1. NO_OUTPUT_WARN 检测 (已有)
      2. pre_round_stats.py → /tmp/cc2_pre_round_report.txt  ← 新增
      3. FULL_PROMPT = 任务骨架 + NO_OUTPUT_WARN + $(cat 报告)  ← 新增
      4. claude -p "$FULL_PROMPT" (300s, 新 session)
      5. R-guard (悬空 .py 检测 + restart)
      6. feishu_notify.py (飞书群通知)  ← 新增
      7. exit 0
```

## 飞书群消息示例

```
[cc2] R-nvonly 轮结束 — 2026-07-31 13:39 CST
📊 cc2 (cc4101-primary) 自优化轮结束
轮号: R-nvonly
📈 30min SR (cc4101-primary): 97.4% (74/77)
❌ 错误分类: buffer_exhausted|3; ...
📝 STATE.md 摘要: ...
```

## 验证

- pre_round_stats.py 手动执行: 输出完整 14 段数据 + 自动分析 ✅
- feishu_notify.py 手动执行: 发送成功 "[cc2] R-nvonly" ✅
- cc2_resume.sh bash -n 语法检查: OK ✅
- 和 openclaw2 共用飞书群, 标题前缀区分 ✅
