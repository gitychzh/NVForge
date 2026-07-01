# OC-R9 — openclaw 卡死紧急修复 (G-lite + J)

> 轨道: openclaw 链路. 承接 OC-R8 收口. **非** NVCF 优化主线 (R484 系列无关).
> 性质: 紧急修复 (用户报"openclaw 又卡住"), 非优化推进. 铁律合规: 只动本机 HM1
> (openclaw 本地 agent 网关 + 本地 hm40006 已属 HM1 自有, 非对端).

## 起因

用户报本机 openclaw 再次卡死 (2026-07-01 凌晨). 调用 CC2 反对者 (HM2 非交互
claude session) 三轮批判式讨论, 先规划后执行.

## 数据 (改前必有数据)

抓取卡死 session `193c1c1c-...` (feishu group oc_0c8175...):
- 时间窗 23:48→00:21, 65 行, **33 次 exec 工具调用, 参数大多不同** (渐进式探索:
  openclaw status / cat configuration.md / curl API / openclaw logs --tail ...).
- hm40006 metrics 同窗: 12 条 openclaw REQ, 全 `status=200 finish_reason=tool_calls`,
  output_tokens 极小 (148–666). **NVCF 持续返回 no-progress tool_calls, openclaw
  忠实执行, context 40K→45K, 走向 compaction.**
- openclaw 自身 log 22min 沉默 (但 hm40006 侧流量不停) → "log-silent tool loop".
- 既有诊断纠误 (CC2 批判后修正):
  - 我先说"收响应→循环" → 错. hm40006 记 `NVCF pexec timeout 23s`, 但 12 条 REQ
    实测 status=200 (CC2 方向对, 细节错: 是 "no-progress tool_call 螺旋" 非
    error-poisoning).
  - 我说"20min黑洞" → 错. openclaw 持续发 REQ (1–12/min), 只是它自己 log 沉默.
  - sessionKey 因果未对齐: caller=openclaw 只证进程非 lane, 4 条 REQ 是否来自该
    stuck session 未严格对齐 (但 msgs 74→92 增长与 44k/131k session 一致).

## 根因

`tools.loopDetection.enabled` **默认 FALSE** → openclaw 内置工具循环断路器关闭.
33+ 次 no-progress exec 调用从未被中断, 直至 compaction.

## 止血

`openclaw daemon restart` 打破循环 (30s 后 0 openclaw req), 功能测试通过.

## 本轮改动 (G-lite + J, 同轮部署)

### G-lite (假设性治本)
- `openclaw config patch --stdin` 置 `tools.loopDetection.enabled = true`
- 备份: `~/.openclaw/openclaw.json.bak.loopdetect_20260701_0826`
- **阈值本轮不动** (CC2 指令: 一次一变量). globalCircuitBreakerThreshold=30 /
  criticalThreshold=20 / warningThreshold=10 维持默认.
- 已知风险 (CC2 提出): genericRepeat detector 可能对 "不同参数 exec 调用" 不触发
  (本次卡死正是渐进式探索, 参数各异). G-lite 未必能拦这类 loop → J 兜底.

### J (无条件兜底)
- 脚本: `/home/opc_uname/bin/openclaw-stall-watcher.sh`
- 逻辑: openclaw log 静默 >5min **且** hm40006 侧同窗仍有 openclaw REQ →
  `openclaw daemon restart`. 静默但 hm40006 也无流量 → idle/compaction-internal, 不抢.
- 部署: systemd user `openclaw-stall-watcher.timer` (OnUnitActiveSec=60s, 已 enable).
- 监控日志: `/tmp/openclaw/stall-watcher.log`
- 保证最多 ~6min 恢复窗口 (5min 静默检测 + restart).

## 验证 (改后必有验证)

- G-lite: `openclaw config get tools.loopDetection.enabled` → `true` ✓
- J: timer `active`+`enabled`, 首次运行 exit=0, 服务 unit 0/SUCCESS ✓
- openclaw daemon: `live` ✓
- 功能测试: `openclaw agent --agent main -m "reply with exactly: OK" --json`
  → `status=ok summary=completed text="OK" provider=nv_cus model=deepseek-v4-pro` ✓

## 待观察

- 下一轮 openclaw 卡死是否仍发生.
- 若 G-lite 未拦住 (genericRepeat 对渐进式探索不触发) → 启动 H-lite
  (hm40006 侧对 no-progress tool_calls 打 tag, 让 detector 有靶可绕). 阈值仍不动.
- J 的 `/tmp/openclaw/stall-watcher.log` 累积触发记录, 作为 G-lite 有效性的实证.

## 锚定

本轮为 openclaw 紧急修复, 非交替优化轮次. NVCF 主线 (R484) 状态不变, 仍
`⏳ 轮到HM2优化HM1` (见 R484 末尾).
