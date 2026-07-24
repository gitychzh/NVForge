# R2192 (HM2→HM1): 悬空 .py 改动止血 + cc2-resume restart 守卫

**Date**: 2026-07-24 14:00 CST (HM2)
**Author**: opc2_uname (HM2, 交互式 CC session)
**Target**: HM2 nv_gw (40006) + cc2-resume 脚本
**Iron Law**: 改前必有数据, 改后必有验证, 聚焦40006, 写入仓库

## 根因 (改前数据)

cc2/openclaw2 两个自优化 agent 各自 Edit `gateway/*.py` 后都没 `docker compose restart nv_gw`,
导致 bind-mount 文件磁盘改了、容器同 inode 能看到文本, 但 Python 进程内存跑的还是
启动时的旧字节码. 后果:

1. agent 下一轮看 probe 没数据 → 判断"没生效" → 再改一遍 → 改动堆积.
2. 下次有人 restart, 多份悬空改动一次性全激活, 不可控.
3. cc2-resume timer 频繁空转/超时 (今天 22 次超时), 部分根因即此 (cc2 写 probe 后
   没数据, 下一轮又来一轮空转).

悬空实例 (止血前):
- `handlers.py` mtime=2026-07-24 13:20 CST, R2191 t2 wire passthrough zombie probe (+4行, cc2 改)
- `logger.py` mtime=2026-07-24 03:09 CST, R2306 field-passage dump probe (+134行, openclaw2 改)
- nv_gw StartedAt=2026-07-23T18:05Z (昨天 02:05 CST, 从未 restart)
- 两份改动均未加载 (跑旧字节码)

## 改动

### 止血 (HM2 nv_gw)
1. `docker exec nv_gw python3 -m py_compile /app/gateway/handlers.py /app/gateway/logger.py` → COMPILE OK
2. `cd /opt/cc-infra && docker compose restart nv_gw` → Started
3. `curl /health` → ok
4. 新 StartedAt=2026-07-24T05:53:54Z RC=0
5. 日志见 `[NV-PROXY] Starting` + `Listening on 0.0.0.0:40006` = 新字节码已加载

### 治本 (cc2-resume 脚本 restart 守卫)
文件: `~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh`
在 `exit 0` 前插入 R-guard 块: 每轮 agent 退出后, 若 `gateway/*.py` 任一 mtime >
nv_gw StartedAt, 则 py_compile 检查 + restart nv_gw + /health 验证, 并记进 RUNLOG.
py_compile 失败 (语法错) 则不 restart, 留待人工.
备份: `cc2_resume.sh.bak.R_guard_*`.
`bash -n` 语法检查通过. 守卫逻辑测试: 无悬空时 skip, touch 造悬空时正确检出.

## 验证

- py_compile 两文件 COMPILE OK
- restart 后 /health = ok, StartedAt 更新, 日志见启动行
- 守卫 `bash -n` 通过, 悬空检出测试通过

## 影响范围

- 仅 HM2 nv_gw (cc2-resume 脚本只服务 cc2, 但守卫检查的是 nv_gw 共享 .py, 顺带
  覆盖 openclaw2 的悬空改动 — openclaw2 改 .py 后即便不 restart, cc2 下一轮
  守卫也会兜底 restart 激活).
- 不碰 ms_gw / 40007.

## 下一步

- 观察下一轮 cc2-resume (timer 每1min) 的 RUNLOG, 确认守卫正确执行 (应 skip, 因
  刚 restart 过无悬空).
- openclaw2-resume.sh 是否也要加同款守卫, 留待下轮决定 (cc2 守卫已覆盖 nv_gw
  共享 .py, openclaw2 加是冗余但更稳).
