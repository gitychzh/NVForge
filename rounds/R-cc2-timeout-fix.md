# R-cc2-timeout-fix: cc2-resume exit code 143 根因修复 (HM2)

## 时间
2026-08-01 13:19 CST

## 问题
cc2-resume.service 每轮报 `Claude Code process exited with code 143`，连续 70+ 轮空转零产出。

## 根因
exit code 143 = 128 + 15 (SIGTERM)。**两层 timeout 都太短**：

1. **systemd `TimeoutStartSec=300`**（5分钟）—— cc2 的请求走 nv_gw buffer 层（5 attempts × 90s = 450s/请求），单个大请求就可能耗 450s，加上 claude 多轮 tool_use + git commit，正常一轮需要 10-15 分钟。300s 只够 3 个 buffer 周期，大请求一轮就 SIGTERM。

2. **cc2_resume.sh 内部 `timeout -k 15 300`**（5分钟）—— 脚本内 setsid 包裹的 claude 进程也有 300s 限制，即使 systemd 给了更多时间，脚本内部先杀掉 claude，然后降级裸跑（又是 300s），形成双重截断。

### 证据链
- cc2.log: 06:11→13:07 连续 70+ 轮，每轮模式相同：轮前统计→新 session→5min后被SIGTERM
- cc2.parse_errors.log: 早期还有 Bun crash 记录 (`panic: Bus error, no_avx2`)，07-29 已修复 symlink 到 native ELF v2.1.186
- DB: cc4101-primary 最后成功请求 05:14 UTC，之后零新请求（claude 进程从未跑完一轮）
- cc4101 日志: 13:13 新 session 发了请求 (msgs=1→2→4→6→8→11→13 递增)，证明 claude 在工作但被 timeout 杀掉
- nv_gw buffer: 当前 session 的请求 `773bc576` attempt 1-5 全部失败 (zombie_partial + all_keys_exhausted)，耗时 450s+，远超 300s timeout

## 修复
1. **systemd `TimeoutStartSec`: 300→1200**（20分钟）
   - 文件: `~/.config/systemd/user/cc2-resume.service`
   - 备份: `cc2-resume.service.bak.R-cc2-timeout-fix`

2. **cc2_resume.sh 内部 `timeout -k 15`: 300→1080**（18分钟）
   - 1080s < 1200s systemd timeout，留 120s 给脚本收尾（R-guard + feishu_notify）
   - 文件: `~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh`
   - 备份: `cc2_resume.sh.bak.R-cc2-timeout-fix`

## deadline 链对齐验证
```
nv_gw buffer: 5 × 90s = 450s (单请求最长)
cc4101 STREAM_TOTAL_DEADLINE: 470s
CC SDK idle timeout: 500s (CLAUDE_STREAM_IDLE_TIMEOUT_MS)
cc2_resume.sh 内部 timeout: 1080s (覆盖 2-3 个 buffer 周期 + tool_use)
systemd TimeoutStartSec: 1200s (覆盖脚本 timeout + 收尾)
```

## 验证
- 修复后新 session (13:29 CST) claude 进程存活 7min+ 未被杀
- cc4101 日志显示 msgs=1→2→4→6→8→11→13 递增（claude 在多轮 tool_use 对话中）
- 之前 300s timeout 下每轮 5min 就被 SIGTERM，零产出

## 参数快照
| 参数 | 旧值 | 新值 |
|---|---|---|
| systemd TimeoutStartSec | 300 | 1200 |
| cc2_resume.sh timeout | 300 | 1080 |
