# R-preround: openclaw2 轮前统计分析注入 prompt

**日期**: 2026-07-31
**主机**: HM2
**改动者**: CC (基础设施)

## 背景

openclaw2 自优化 agent 每轮启动时, 需要自己跑 DB 查询拉链路数据 (SR/错误分类/per-key 等), 花费宝贵的 session 时间在数据收集而非分析决策上。

## 改动

### 1. pre_round_stats.py (新增)
- 路径: `~/cc_ps/openclaw2_repair_self/.claude/pre_round_stats.py`
- 功能: 每轮 claude 启动前, 从 hermes_logs DB 拉 30min 链路数据, 输出纯文本摘要
- 数据维度:
  - 当前 nv_gw 配置快照 (env 关键参数)
  - 30min 按 caller×model×status 总览
  - 30min 按模型 SR
  - 30min 按 caller 分解 (status×count×avg_dur×errors)
  - 30min 错误分类 (type×sub×count×avg_dur)
  - 30min per-key×status (dsv4p)
  - 30min per-egress-IP (dsv4p)
  - 30min dsv4p 200 延迟/Token 统计
  - 30min finish_reason 分布 (zombie 诊断)
  - 30min fallback 发生率
  - 30min nv_tier_attempts per-key 错误分布
  - 30min dsv4p 按分钟趋势
  - 2h SR 趋势 (10min 桶)
  - 自动分析要点 (SR 评级 + top error 诊断建议)

### 2. openclaw2_resume.sh (修改)
- 轮前调用 `pre_round_stats.py`, 输出存入 `$PRE_ROUND_REPORT`
- 将报告注入 `$FULL_PROMPT` 末尾, agent 一上来就看到链路分析
- prompt 步骤3 更新: "链路数据已注入, 无需重复查询"
- 步骤4 前加入指引: "基于以上数据, 直接进入决策步骤"

### 3. feishu_notify.py (新增, 上一轮已完成)
- 轮结束后向飞书群 `openclaw2_improve_self` 发送本轮总结

## 工作流 (改后)

```
openclaw2-resume.timer (1min)
  → openclaw2-resume.service (oneshot)
    → openclaw2_resume.sh
      1. pre_round_stats.py  ← 新增: 拉 DB 数据, 生成分析报告
      2. 报告注入 prompt       ← 新增: agent 首条消息就含链路分析
      3. claude -p "$FULL_PROMPT" (840s, 新 session)
      4. gen_status.py (UI 状态)
      5. feishu_notify.py (飞书群通知)
      6. exit 0
```

## 预期效果

- agent 不用自己跑 DB 查询, 节省每轮 2-3min 数据收集时间
- 数据维度全面 (比 agent 自己临时拼 SQL 更完整)
- 自动分析要点给出 SR 评级 + top error 诊断建议, 引导 agent 聚焦
- agent 可直接进入决策步骤, 更多时间用于分析+改码+验证

## 验证

- pre_round_stats.py 手动执行: 输出完整, 含 12 个数据段 + 自动分析要点 ✅
- openclaw2_resume.sh bash -n 语法检查: OK ✅
- 下一轮 timer 触发后自动走新脚本 (验证中)
