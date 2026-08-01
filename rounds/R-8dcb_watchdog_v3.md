# R-8dcb: cc-stuck-watchdog v2 误杀 session 8dcb0ee6 根因修复

**日期**: 2026-08-02
**主机**: HM2
**session**: 8dcb0ee6-8d90-45bf-808b-2dc9457c0516 (cloudcli webui session, JSONL: f9781ce9)

## 现象

cloudcli webui 报 `Claude Code process exited with code 143` (SIGTERM)。

## 根因 (journal+JSONL 铁证)

**kill 链:**

| 时间(CST) | 事件 |
|---|---|
| Aug 1 19:24:35 | cloudcli webui (node PID 3323016) 创建 session 8dcb0ee6 |
| Aug 2 00:48:03 | 最后一条 assistant 输出 (dsv4p_nv 测试报告完成, `16:48:03.683Z`) |
| 00:48~01:00 | session 闲置等用户输入 (12min) |
| **01:00:45** | **用户发新 prompt**: "继续帮我测试nvidia的kimi模型…" (`17:00:45.779Z`) |
| **01:00:45** | **同一秒!** cc-stuck-watchdog v2 判定 idle=761s>600s → kill PID=3621500 |
| 01:00:46 | cloudcli SDK 报 exit code 143 |

**cc-stuck-watchdog v2 两个 bug:**

1. **Bug-A: 不检查新 user 输入** — 只看"距上次 assistant 的间隔", 不检查 user 是否在之后发了新消息。session 闲置等用户输入 12 分钟, 用户发新 prompt 的同一秒被 kill。
   - 修复: 扫 tail -20 里最后一条 type=user (排除 tool_result), 若 user 在最后 assistant 之后 → 不 kill (正在处理)

2. **Bug-B: 新 PID 出现即杀(竞态)** — 之前多次扫描报告 "no live PID found", 01:00:45 cloudcli 因用户发 prompt 启动新 claude 进程, watchdog 立刻发现新 PID 并 kill, 没给任何宽限期。
   - 修复: 记录 PID 首次出现时间, 给 120s grace period, 不杀新 PID

## 修复

### 1. cc-stuck-watchdog v2→v3

- 备份: `cc_stuck_watchdog_v2.sh.bak.R-8dcb`
- 新脚本: `~/cc_ps/cc_watchdog/cc_stuck_watchdog_v3.sh`
- systemd unit 更新: `cc-stuck-watchdog.service` ExecStart→v3, 加 `PID_GRACE_PERIOD_S=120`
- daemon-reload + restart

### 2. claude binary v2.1.186→v2.1.220

- symlink `/home/opc2_uname/.npm-global/bin/claude` 从 v2.1.186 (Bun 编译, HM2 无 AVX2 → 间歇 Bus error) 更新到 v2.1.220 (native ELF)
- 验证: `claude --version` → 2.1.220

### 3. cc2-resume.timer 重新 enable

- timer 之前被 disable (原因不明), 重新 enable + start
- 验证: 新 session 5fa5e92d 已启动, JSONL 增长中 (18K→35K), 无 Bun crash

## 验证

| 项 | 结果 |
|---|---|
| v3 watchdog 运行 | active (running), 日志 "v3 fixes: (A) check user input (B) PID grace 120s" ✓ |
| claude binary | v2.1.220, ELF 64-bit, ldd OK ✓ |
| cc2-resume timer | enabled, active, 新 session 在跑 ✓ |
| cc2 新 session JSONL | 5fa5e92d, 18K→35K 增长中 ✓ |
| 无 Bun crash | 新 session 无 panic/bus error ✓ |

## 参数快照

| 参数 | 旧值 | 新值 |
|---|---|---|
| watchdog 脚本 | v2 | v3 |
| ASSISTANT_IDLE_THRESHOLD_S | 600 | 600 (不变) |
| PID_GRACE_PERIOD_S | (无) | 120 (新增) |
| claude binary | v2.1.186 (Bun) | v2.1.220 (native ELF) |
| cc2-resume.timer | disabled | enabled+active |

## 下一步

- 观察 v3 watchdog 在下一个 idle 场景中是否正确跳过 (不误杀)
- cc2 agent 用 v2.1.220 binary 正常产出轮文件
- 考虑 cloudcli webui 的 `CLAUDE_STREAM_IDLE_TIMEOUT_MS=900000` 是否仍需调整 (当前 900s > watchdog 600s, watchdog 先杀)
