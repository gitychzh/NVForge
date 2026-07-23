# R2302 (HM2 only): openclaw2 自优化 title-zombie 根治 — 瘦身 prompt + STATE 不预贴入 (同 cc2 R2299)

> 承接 R2299 (cc2 端已验证有效). openclaw2 是 title zombie 大头 (改前 14/21 dump 来自 openclaw2).
> 用户原则: 层 1 够用就不加网关代码. 本轮纯 prompt 改造, 不碰 nv_gw/cc4101/ms_gw 源码.

## 改前数据 (HM2 nv_gw zombie_dumps + nv_requests, R2299 部署后 13:56 UTC+)

### R2299 对 cc2 已验证有效 (铁证)
- cc2 title 请求: input_chars 11464 → **2442** (降 79%), 全部 200 成功 (改前 zombie 502)
- cc2 title zombie dump 改后 = 0 (改前 7/21)
- 近 2h 小输入请求对照 (铁证):
  | 时间 | input_chars | status | 来源 |
  |---|---|---|---|
  | 15:41 | 2442 | ✅200 | cc2 (改后) |
  | 15:30 | 11464 | ❌502 zombie | openclaw2 (未改) |
  | 15:29 | 2442 | ✅200 | cc2 (改后) |
  | 15:15 | 11464 | ❌502 zombie | openclaw2 (未改) |
  | 15:15 | 2442 | ✅200 | cc2 (改后) |
  | 15:03 | 2442 | ✅200 | cc2 (改后, 130s 但成功) |

### openclaw2 残留 title zombie (未改, 本轮目标)
- R2299 部署后 7/7 新 zombie dump 全是 openclaw2 (input=11464, 全 TITLE-openclaw2)
- 改前 openclaw2 title zombie 占总量 14/21 (大头)

### 根因 (同 cc2, R2299 已定位)
openclaw2_resume.sh 把 PROMPT heredoc(~4k)+STATE.md 全文(~8k) 拼成首条 user 消息(~11k) →
cc SDK 自动 title 请求把整条当样本 → 11k 输入落 NVCF 对长输入+极短输出系统性 zombie 区.

## 改动 (HM2 only, 单文件, 不碰任何网关源码)

`~/cc_ps/openclaw2_repair_self/.claude/openclaw2_resume.sh` (备份 `.bak.R2302`):

**改法 1 (STATE 不预贴入)**: 删 STATE_CONTENT 拼接, `FULL_PROMPT="$PROMPT"`, STATE.md 改由 openclaw2 步骤 1 自己 cat.

**改法 2 (PROMPT heredoc 瘦身)**: 旧 heredoc ~4k (含重复铁律/详细步骤, 与 CLAUDE.md 重复) → 新 heredoc **1601 字节**骨架, 7 步工作流 + 指向 CLAUDE.md/STATE.md 引用.

**效果**: 首条 user 消息 ~11k → ~1.6k (降 85%), title 请求输入随之降到 <2k, 远低于 NVCF zombie 触发区间.

## 验证 (新 prompt 0:00 CST+ 生效后 shadow 2-6h)
- [ ] openclaw2 title 请求 input_chars 从 11464 降到 <2k
- [ ] openclaw2 title zombie dump 停止增长
- [ ] openclaw2 本身正常跑完一轮 (行为风险: 改为主动 cat STATE/CLAUDE.md, 需观察是否执行 cat 接上任务)
- [ ] 无新增非 title 类 zombie

## 注意: 旧进程残留
部署时(23:51 CST)有个旧进程(23:45 启动)仍在用旧 prompt 跑(已加载旧字节码), 840s timeout 23:59 结束.
0:00 CST timer 触发下一轮才用新 prompt. 故 23:45-23:59 这轮可能还产 1 个 openclaw2 title zombie (旧 prompt), 属预期, 不算新配置失效.

## 回滚
`cp ~/cc_ps/openclaw2_repair_self/.claude/openclaw2_resume.sh.bak.R2302 ~/cc_ps/openclaw2_repair_self/.claude/openclaw2_resume.sh`

## 关联
- 铁律: 改前有数据(R2299 cc2 铁证+openclaw2 7 dump), 改后有验证(shadow 看 dump 停增), 聚焦40006间接, 只改HM2, 写入仓库, 不碰 nv_gw/cc4101/ms_gw 源码, 不碰 agent 模型选择.
- cc2 R2299 已验证层 1 (改 prompt) 有效, 本轮把同款改法套到 openclaw2. 层 2 (网关识别短路) 不做, 因层 1 已够.
