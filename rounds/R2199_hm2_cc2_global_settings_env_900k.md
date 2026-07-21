# R2199 (hm2_cc2): 全局 settings.json env 块才是 CLAUDE_CODE_AUTO_COMPACT_WINDOW 最终赢家 — 证伪 R2191 项目级改法

**日期**: 2026-07-21 23:30-00:09
**主机**: HM2 only
**作用面**: cc2 自优化基础设施 (非 nv_gw 参数, 非 /opt/cc-infra)
**关联**: R2191 (ULTIMATE GOAL 撤40007前置 — 499归零), R2192 (路径B zombie内部重试)

## 改动

| 文件 | 改动 | 备份 |
|---|---|---|
| `~/.claude/settings.json` (HM2 全局) | env 块 `CLAUDE_CODE_AUTO_COMPACT_WINDOW`: `"155000"` → `"900000"` | `.bak.R2199_20260721` |
| `~/cc_ps/openclaw2_repair_self/.claude/openclaw2_resume.sh` 第13行 | `export ...=155000` → `export ...=900000` (对齐全局) | `.bak.R2199_20260721` |
| `~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh` 第12行 | R2199 已是 `export ...=900000` (R2191 改过, 保留作 fallback) | (R2191 已备份) |

## 根因 (铁证链)

1. cc2 进程 `/proc/PID/environ` 实测 `CLAUDE_CODE_AUTO_COMPACT_WINDOW=155000` (旧值, 23:32 启动的 PID 1511964)
2. 父 bash (resume.sh) `/proc/environ` 无此变量 (启动快照), 但 resume.sh 第12行已 `export 900000` → 注入 bash 环境表, 子进程 claude 本应继承 900000
3. 但 claude 拿到 155000 → 唯一来源 = **全局 `~/.claude/settings.json` env 块** (`"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "155000"`)
4. cc2 **项目级** settings.json 已是 900000 (R2191 改过) 但**不生效** → 证伪 R2191 假设"项目级覆盖全局"

**机制**: claude CLI 启动时读 `~/.claude/settings.json` 的 env 块, 显式 setenv 注入自己进程环境, **覆盖**了 (a) 从父 bash 继承的 shell export 值 (b) 项目级 settings.json 的同名 key。全局 env 块是最终赢家。

## 验证

| 进程 | 启动时点 | 改前/后 | `/proc/environ` 实测 |
|---|---|---|---|
| 旧 cc2 PID 1511964 | 23:32:08 | 改前 | `=155000` ❌ |
| 新 cc2 PID 1520353 | 23:58:59 | 改后 | `=900000` ✅ |

对比即证: 改全局 settings.json 是唯一生效路径。R2191 改项目级 + resume.sh export 双双被全局盖。

## 影响

改全局 155000→900000 波及三方, 都更宽松无害 (glm5.2 nv+ms 早已开放 1M, DB 实测 max 253797c status=200):
- **cc2** (目标): 155000→900000, 150K prompt 不再中途触发 auto-compact → 不再中途断流 → 499 应归零
- **openclaw2**: 155000→900000 (其 resume.sh 也对齐 900000)
- **interactive cc** (我): 155000→900000, 更宽松

R2191 "禁碰全局" 决策的前提 (项目级覆盖全局) 被证伪, 用户拍板改全局。

## 499 基线 (改前)

`cc_requests` 表, 6h before fix (17:58-23:58):
- status=200: 404 条
- status=499: **14 条** (每小时 1-3 个稳定渗出)
- status=502: 3 条

499 是低频事件 (1-3/h), 判断"归零"需 3-6h 观察窗。

## 待验证 (下一轮)

改后 cc2 用 900000 跑, 3-6h 后拉 `cc_requests` 看 499 计数:
- 若 499=0 → auto-compact 是 499 唯一根因, R2191 ULTIMATE GOAL (撤40007前置) 达成
- 若 499 仍渗出 → auto-compact 非唯一根因, 转走路径 B (nv_gw 侧 zombie 内部重试, 撤40007核心, 见 R2192)

## 铁律

- 以后要让 claude CLI 用某 env 值, **改全局 ~/.claude/settings.json env 块**, 不能只改项目级 settings.json 或 resume.sh export (两者都被全局盖)
- 若要三方各取所需, 改从全局**删 key** 让 claude fall back 到 shell env — 但 R2199 选了直接改值 (三方都更宽松无害)
