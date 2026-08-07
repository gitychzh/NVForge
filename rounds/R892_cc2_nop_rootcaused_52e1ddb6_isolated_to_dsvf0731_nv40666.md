# R892 (cc2) — NOP 巡检轮 — 定位 52e1ddb6 泄漏源 = 独立容器 dsvf0731_nv40666 (hermes), NOT 主 nv_gw

> 状态: **NOP 不改码**。cc2 主链路 (nv_gw:40006) 当前 30min=139/139 全 200 (100% SR, 0 失败)。
> 本轮关键成果: **精确定位 R891 遗留的"52e1ddb6 泄漏" — 注入源不是主 nv_gw 的 dsv4f0731 rotation,
> 而是独立容器 `dsvf0731_nv40666`（host opc2sname-dsv4f40666, 服务 caller=hermes）在用它且 100% 全败。**
> cc2 请求线不受影响 (hermes→40666, cc4101-primary→40006 分离)。

## 本轮改动

**无 (NOP)。** 四容器 health 全 ok, cc2 主链路 100% 干净, 无新错误类; 只定位 + 记录根因。

## 根因 (本轮实拉定位, live DB now()=2026-08-07 00:01 UTC / 08:01 CST)

- **cc2 主链路 nv_gw(40006): 30min cc4101-primary = 139/139 = 100% SR, 0 bad**。注入数据里
  502×2 + 499×1 是上一时间片 (≤23:35 UTC 簇2 尾部) 已滑出窗口 — 当前窗口 0 失败。
  pexec 日志全程 `fid=281478d0` (健康 fid), 无 52e1ddb6。
- **52e1ddb6 坏 fid 泄漏源 = `dsvf0731_nv40666` 容器** (host_machine=`opc2sname-dsv4f40666`,
  caller=`hermes`, Up 14 hours, 同一 cc-infra-nv_gw 镜像跑 40666 端口):
  - 30min nv_tier_attempts: 52e1ddb6 记于 tier=dsv4f0731_nv, 21/21 全败
    (NVCFPexecRemoteDisconnected×15, 529×2, Timeout×2, empty_200×2), 每次 ~31-57s,
    egress_ip 空, 每批 5 key 同时间戳 (BufferStreamSession 样)。
  - 根因: 40666 env `NVU_FID_DISCOVERY_ENABLED=1` + NAME_MATCH=`deepseek-v4-flash` +
    MODEL=`dsv4f0731_nv`。discovery 每 30min 扫到两个 ACTIVE 候选 (281478d0 与 52e1ddb6),
    **但 281478d0 的 probe 恒 404** (body model 用 `deepseek-ai/deepseek-v4-flash` 非
    `-0731`, 与 config.py L116 注释一致) → "No new candidates passed probe. Keeping current"
    → 恒卡在坏 fid 52e1ddb6, 永远不切到健康 281478d0。
  - 这是 40666 容器 discovery 探针 bug (probe body model 名不匹配 -0731 fid), 非主链路问题。

## 依据数据 (30min, live)

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **139/139 = 100% SR, 0 bad** | ✅ |
| 三 scoped 容器 health | 40006/40066/4101 全 ok | ✅ |
| cc2 请求 pexec fid | 全程 281478d0 | ✅ |
| 主 nv_gw env fid | 无 0731 覆盖 → config 默认 281478d0 | ✅ |
| 40666 容器 (hermes) 52e1ddb6 | 21/21 全败 (30min) | ⚠️ 越界容器, 未改 |
| fallback (cc2 线) | 0 次 | ✅ |

## 验证
- curl 40006/40066/4101 → 全 ok; cc4101 primary=dsv4f0731_nv。
- 30min cc4101-primary 实拉 = 139 全 200, 0 bad; pexec 日志全 `fid=281478d0`,
  零 52e1ddb6/cooldown/429/exhaustion。
- host 分离确认: cc4101-primary→`opc2sname`(40006), hermes→`opc2sname-dsv4f40666`(40666), 互不影响。

## 关键判断
R891 疑 "52e1ddb6 泄漏进主 nv_gw 的 dsv4f0731 rotation" — **不准确**。实拉铁证:
52e1ddb6 全由 **dsvf0731_nv40666** (hermes 线) 产生, 未进入主 nv_gw(40006) 的 dsv4f0731
候选池 (主 nv_gw 用 281478d0, 干净)。**不改码**:
1. 40666 不在 cc2 改动范围 (铁律: 只改 nv_gw:40006 + dsv4p_nv40066:40066)。
2. 它对 cc2 (cc4101-primary) 的 SR 无影响 (139/139)。
3. 若需修 40666 (让 discovery probe 用 -0731 model 或显式 env 覆盖 fid), 属独立容器运维决策,
   须单独确认归属与数据后处理 — 非本轮 cc2 工件。

## 修复链 (沿用)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw 主链, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `docker ps` → nv_gw(5h) / nv_gw_stable(5d) / dsv4p_nv40066(2d) / dsvf0731_nv40666(14h) 全 Up ✅

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101(4101): primary=dsv4f0731_nv, PRIMARY_HEADER_TIMEOUT=400,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
- config.py: dsv4f0731_nv function_ids=[281478d0...] (主链); dsv4f_nv=[52e1ddb6...]
- ⚠️ dsvf0731_nv40666 (越界, 信息记录): NVU_FID_DISCOVERY_ENABLED=1, MODEL=dsv4f0731_nv,
  NAME_MATCH=deepseek-v4-flash, NVCF_DEEPSEEK_FLASH_FUNCTION_ID=52e1ddb6... → discovery 恒卡 52e1ddb6

## 下一步
- 主链 cc2 已 100% 干净, 下轮预期维持 NOP (窗口右移, 无新事件)。
- **优先监控**: 主 nv_gw(40006) dsv4f0731 rotation 是否持续只出 281478d0 (0 bad 保持)。
- 若需处理 52e1ddb6 浪费: 那是 **dsvf0731_nv40666 (hermes 线)** 的问题, 可选修复 =
  ① discovery probe 改用 `-0731` model 名, 或 ② 显式 env `NVCF_DEEPSEEK_FLASH_0731_FUNCTION_ID`=281478d0。
  但 40666 不在 cc2 改动范畴, 待归属确认后单独评估 (须先有该容器流量归属数据)。