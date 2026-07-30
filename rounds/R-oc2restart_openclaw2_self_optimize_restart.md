# R-oc2restart: openclaw2 自优化定时任务重启

**日期**: 2026-07-30 (HM2)
**改动**: 重启 openclaw2 自优化系统, 适配 dsv4p_nv

## 背景

openclaw2 自优化系统于 2026-07-20 部署, 跑到 R2307 后停用 (约 2026-07-24).
用户要求重启, 间隔 1min, 每次新 session, 自动总结 (类似 cc2).

## 改动 (HM2 only)

### 1. settings.json
- model: `glm5_2_nv` → `dsv4p_nv`
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW`: 新增 `80000` (dsv4p context 120K, 不需要 glm5.2 的 1M)
- 备份: `.bak.R-oc2restart`

### 2. openclaw2_resume.sh
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW`: `900000` → `80000`
- 备份: `.bak.R-oc2restart`

### 3. CLAUDE.md
- 链路图: `NVCF glm5_2_nv` → `NVCF dsv4p_nv`
- "当前已知状态" 整段重写: 从 2026-07-20 启动时 → 2026-07-30 重启时
  - 更新架构描述: R-rebuild 4 层 (KeyManager/ProbeWorker/WaitQueue/BufferStreamSession)
  - 更新 env 状态: NVU_DISABLE_MS_FALLBACK=1, NVU_PEER_FB_SKIP_MODELS 含 dsv4p_nv
  - 更新当前 SR: dsv4p_nv 60min ~79%, 主要失败 zombie_empty_completion
  - 更新核心任务: 挖 dsv4p_nv /v1/messages 路径 zombie BUG + caller 识别
- "少 fallback" → "少失败" (ms_gw 已禁用, 没有 fallback 可走)
- 备份: `.bak.R-oc2restart`

### 4. systemd
- `systemctl --user enable --now openclaw2-resume.timer`
- timer: `OnBootSec=1min`, `OnUnitInactiveSec=1min` (上一轮结束后 1min 触发下一轮)
- service: `Type=oneshot`, `TimeoutStartSec=1500` (25min), `KillMode=control-group`

## 验证

1. timer active+enabled: ✅
2. 第一轮于 00:14:05 CST 启动: ✅ (PID 612427, claude CLI 3.1% CPU 291MB)
3. DB 确认 caller=openclaw2 流量出现: ✅ (3 条请求, 正确识别)
4. cc2-resume.timer 同时在跑: ✅ (两套自优化并行)
5. parse_errors.log 无新错误: ✅ (旧条目 2026-07-24)

## 架构

```
openclaw2 (claude CLI, anthropic /v1/messages)
  → nv_gw (40006, dsv4p_nv, /v1/messages)
    → NVCF pexec (function_id=12acbc62, deepseek-ai/deepseek-v4-pro)

cc2 (claude CLI, anthropic)
  → cc4101 (4101, anthropic→openai 转换)
    → nv_gw (40006, dsv4p_nv, buffer-then-flush)
      → NVCF pexec
```

两套自优化并行, 零撞车:
- openclaw2 直走 nv_gw /v1/messages (format/ 转换层视角)
- cc2 走 cc4101 buffer 路径 (cc4101 转换层视角)
- 轮号前缀: hm2_oc2 vs hm2_cc2

## 本地仓 commit

```
9449577 R-oc2restart: 重启 openclaw2 自优化定时任务
```

HM2 only. 未碰 ms_gw / agent config / nv_gw 源码.
