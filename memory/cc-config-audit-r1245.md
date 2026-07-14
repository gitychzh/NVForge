---
name: cc-config-audit-r1245
description: "HM2 CC(cc4101)配置体检结论: zombie与token弱相关, primary故障非配置可修, 已修注释+bak"
metadata: 
  node_type: memory
  type: project
  originSessionId: 05e4dd84-b93e-4691-967c-84f53de52569
---

2026-07-13 系统性体检远程 HM2 Claude Code 配置（R1245, commit 9629066）。

**数据结论（推翻假设）**：cc4101 7天1430请求里 zombie 与 token 规模**弱相关** — <80k 反而 23% 最高，88-105k 16%，105-155k 10%。所以"下调 autoCompactWindow 避 88k 僵尸窗口"**无效**，别再做。288个失败里 81.6% 是 primary timeout（nv_gw glm5_2_nv 直测 60s 卡死），是 NVCF 后端 function 3b9748d8 DEGRADED（R825/R1242 已记），**非配置层可修**。cc4101 熔断器正确 OPEN+skip primary，fallback ms_gw glm5_2_ms 70% 成功撑着——这是当前架构最优，不要去调 PRIMARY_HEADER_TIMEOUT 试图治本。

**已修（零风险，已推送 main）**：
1. cc4101 config.py 注释/default `dsv4p_ms`→`glm5_2_ms` 对齐 R805（env 已配，default 兜底，零影响无重启）
2. 删 3 份过时 settings.json.bak（指向废弃 litellm 40001），用当前 live 生成新 bak

**待做（用户已同意但未执行，需确认范围）**：
- CLAUDE.md 重写：仓库根 + NVForge/CLAUDE.md 仍写 legacy 40001/glm5.1，未跟上 R827 CC→cc4101 迁移。R682 "legacy 不退役"决策仍对，但 CC 段需补 cc4101。涉及多文件措辞，独立任务。
- memory 同步：远程 NVForge memory 仅 3 条（已加本次），本地 22 条，待 rsync 共享方法学。
- session-env 清理：远程 152 目录（最老 6/14），加**系统 cron**（非 CronCreate，见 [[cron-session-only-unreliable]]）清理 >30d。

详见 rounds/R1245_hm2_cc_config_audit.md。相关：[[r842-88k-zombie-window-root-cause]]、[[r840-openclaw-zombie-empty-stall-fix]]、[[nvcf-testing-methodology]]。
