# Plan: NVForge 整体规范化、模块化、修正不符合实际 (2026-08-09)

> 目标: 整理整个 NVForge 项目。规范文件名/目录结构, 找出与 live 实际不符的事实并修正,
> 模块化/工程化, 符合长期优化。工作落主仓 `~/hm_ps/hermes_improve_self`, 过期工作区
> `/home/opc_uname/cc_ps/NVForge/NVForge` 只同步权威 CLAUDE.md 与说明。

## 0. 现状核实 (改前必有数据)

**live 实际 (ground truth, 来自 live STATE.md + git 历史):**
- 当前轮: **R1240** (cc2 loop, NOP 巡检), git 主支已到 R1235 (dsv4f0731 self-opt NOP)。
- **live 主模型: `dsv4f0731_nv`** (FID `281478d0-f307`), 容器 `dsvf0731_nv40666` (port 40666)。
  **不是** CLAUDE.md 里写的 `glm5_2_nv`/`dsv4p_nv`。
- live 序列: cc2 loop `R12xx_cc2_nv_gw(_NOP)`, dsv4f0731 self-opt loop `R12xx_dsv4f0731_self_opt_nop`,
  HM2→HM1 optimize loop `R12xx_hm2_optimize_hm1` — **三者共用同一 R12xx 编号空间, 已碰撞**。

**命名混乱定量 (rounds/ 3600+ 文件, 6+ 平行序列, 同号多义):**
| 序列 | 数量 | 说明 |
|---|---|---|
| `R<4d>_hm2_optimize_hm1` | 1561 | 旧 R569 取消的交替优化机制, 与 live 序列撞号 |
| `R<4d>_cc2_nop_*` / `cc2_R*` / `R<4d>_cc2_nv_gw` | ~994 | cc2 loop, 多命名 |
| `R<4d>_dsv4f**/dsvf0731_self_opt` | ~218 | dsv4f0731 self-opt loop (live) |
| `R-nvonly-post*` | 216 | 旧 nv-only 序列, 与 live 撞号 |
| `RN<4d>_*` | 62 | RN 平行序列 |
| `R_buffer_post`/`R_keyretry_post`/`R_dsv`/`R_cc`/`R-glm` | 18 | 零星 |
| `R1xxx_hm2_cc2_nop_rNNN` | — | 双重编号 (R1xxx + 内嵌 rNNN) |

**同号多义铁证**: `R1234` 同时存在 `_cc2_nv_gw` / `_dsv4f0731_self_opt_nop` / `_hm2_optimize_hm1`
三个不同 loop 的文件。

**顶层杂散**: STATE.md.bak.* ×15, 根目录星散 plan/R*.md, 过期 memory/, logs/, 重复 STATE_cc2.md。

**依赖面**: round 文件名被 ~40 个 .md 交叉引用 (plans/memory/其他 rounds), 但**不被任何 live
脚本/配置依赖** (cc2/hermes2 自优化在 HM2 独立 `~/cc_ps/cc2_repair_self/rounds/`, 自行命名)。
→ 改名安全, 但需批量更新 .md 交叉引用。

---

## 1. 命名标准 (目标规范)

**round 文件名**: `R<seq>-<loop>-<desc>.md`
- `<seq>`: 该 loop 自身计数器 (每个 loop 独立、不共享)
- `<loop>`: 规范化 loop 标识符 (见下映射)
- `<desc>`: 短 kebab-case 描述 (无则省略)

**loop 标识符映射** (把现有多种命名归一到一个 loop 名):
| 现有文件名模式 | → loop 标识符 |
|---|---|
| `_hm2_optimize_hm1` | `hm2opt` |
| `_dsv4f0731_self_opt_nop` / `_dsvf0731_self_opt` / `RN<4d>_dsvf*` | `dsv4f0731` |
| `_cc2_nv_gw` / `_cc2_nop` / `cc2_R*` / `R<4d>_cc2_nop` | `cc2` |
| `R-nvonly-post*` | `nvonly` |
| `RN<4d>_*` (非 dsvf) | `rn` |
| `R_buffer_post*` / `R_buf*` | `buffer` |
| `R_keyretry_post*` | `keyretry` |
| `R_dsv*` / `R-glm*` / `R-cc*` / `R_cc*` / `R_rebuild*` | 各自主题 |

> 注意: 因 loop 各自计数, 目标名 `R1234-cc2-...` 与 `R1234-dsv4f0731-...` 不再冲突 ——
> loop 名成为消歧字段。

**同号多义固定原则**: 一个 round 文件若同时属于多个序列 (如 `R1991_hm2_cc2_nop_inspect_r101`),
取**主 loop = 文件名后缀最具体的那个** (此处 cc2), seq 用其内嵌计数器 (r101)。

---

## 2. 执行阶段 (分批, 每批验证)

### Phase A — 建权威事实层 (先修正"不符合实际")
1. 重写主仓 `CLAUDE.md`: 模型层级/容器/轮次对齐 live 实际
   - live 主模型 `dsv4f0731_nv` (FID `281478d0-f307`), 容器 `dsvf0731_nv40666` (40666)
   - 四 adapter cc4101/cx4102/hm4104/opclaw4103 → 40666/dsv4f0731_nv 主链
   - 当前轮 R1240, 序列 = cc2/dsv4f0731 self-opt
   - 修正容器表 (加 40005/40666, 说明 40006 nv_gw 与 40666 主链关系)
   - 附"round 命名规范"一节 (本 plan §1)
2. 同步修正后的 CLAUDE.md 到过期工作区 (两边一致)
3. 修正 `README.md` / `rule.md` 中过时事实 (若与 CLAUDE.md 冲突)

### Phase B — 顶层模块化 (归入 `_archive/`)
4. 新建 `_archive/` 目录, 移入:
   - `STATE.md.bak.*` ×15, `CLAUDE.md.bak.pre-*`
   - 根目录星散 plan (`.claude_plan.md`, `R1xxx_plan.md`, `R17xx_plan.md` 等)
   - 过期 `memory/` (HM2 有独立自优化 memory; 本仓 memory/ 是旧快照)
   - `logs/` (本地监控日志, 入 .gitignore 档)
5. 顶层精简为规范入口: `README.md` + `CLAUDE.md` + `rule.md` + `doc/` + `rounds/` + `plans/` + `scripts/` + `deploy_artifacts/` + `STATE.md`(单份) + `upstream_current.py`
6. 合并重复 STATE: `STATE_cc2.md` (R1181 旧) 归档, 保留单份 `STATE.md` (R1240 新)

### Phase C — round 全量统一改名 (批量 + 分批验证)
7. 写 `scripts/normalize_rounds.py`:
   - 输入: 每行一个现有 round 文件名
   - 按 §1 映射 loop, 提取该 loop 计数器, 生成目标名 `R<seq>-<loop>-<desc>`
   - 冲突检测: 目标名已存在 → 附加序号或保留 desc 消歧
   - 输出: rename 映射表 (`rounds/_rename_map.csv`) + 干跑报告
8. 分批执行 (每批 ~300 文件), 每批后 `git add` + 校验: 无目标名冲突、无重复
9. 批量更新 `.md` 交叉引用: 用 rename map 做 `sed` 替换全部 `rounds/旧名` → `rounds/新名`
10. 更新 symlink (`latest.md` 等) 指向新名
11. 重建 `rounds/README.md` 索引: 各 loop 序列 → 最新轮对照表

### Phase D — 验证与提交
12. 干跑 + 抽查: 随机抽 20 个改名前后文件 diff 确认内容一致
13. `git add -A && git commit` (分批 commit, 每批一个 tag-ish 说明)
14. push 到 `origin/main` (HM1 可直连 github, R1627 已验证; 超时走 mihomo 9090)
15. 更新 auto-memory + 本 plan 回收

---

## 3. 风险与缓解
- **git 历史断链**: 全量改名必然断链 (用户已接受)。缓解: `_rename_map.csv` 永久保留,
  提供旧名→新名可追溯; 分批 commit 便于 revert。
- **.md 交叉引用失效**: 用 rename map 批量 sed 更新, 覆盖 ~40 引用文件。
- **live loop 撞号残留**: loop 名消歧后, 各 loop 计数器独立, 不再互相覆盖。
- **改名误伤**: 每批干跑 + 抽查 diff, 冲突文件单独处理不盲改。

## 4. 交付物
- 主仓 + 工作区一致的权威 `CLAUDE.md` (符合 live 实际)
- `_archive/` 收纳散件, 顶层规范
- `scripts/normalize_rounds.py` + `rounds/_rename_map.csv` (可追溯)
- 统一后的 `rounds/` (命名规范, loop 消歧) + `rounds/README.md` 索引
- 全部 commit + push