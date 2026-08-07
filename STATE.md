# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R892 (NOP 巡检轮/不改码 — cc2 主链路 100% 干净; 精确定位 52e1ddb6 泄漏源 = 独立容器 dsvf0731_nv40666, 非主 nv_gw)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **139/139 = 100% SR, 0 bad**;
> 52e1ddb6 坏 fid 全由 **dsvf0731_nv40666** (host opc2sname-dsv4f40666, hermes 线) 在记
> (30min 21/21 全败, RemoteDisconnected/529/Timeout/empty_200), 未进主 nv_gw 候选池。
> 主 nv_gw pexec 全程 fid=281478d0, 干净。40666 根因: NVU_FID_DISCOVERY 扫到 281478d0 但
> 其 probe 恒 404 (body model 用 `-flash` 非 `-0731`) → 恒卡坏 fid 52e1ddb6。
> live DB now()=2026-08-07 00:01 UTC (08:01 CST)
> 上轮: R891 (NOP, 误判 52e1ddb6 在主 nv_gw rotation; 本轮实拉澄清其隔离在 40666)

## 本轮 (R892) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路 100% 干净, 无新错误类; 只定位 + 记录 52e1ddb6 泄漏根因)

### 依据 (live DB now()=2026-08-07 00:01 UTC)

- 30min cc4101-primary (host opc2sname, 主 nv_gw:40006) = **139/139 全 200, 0 bad (100% SR)**。
  注入数据中 502×2/499×1 为 ≤23:35 UTC 上一片已滑出, 当前窗口 0 失败。
- pexec 日志 (07:31→08:01 CST) 全程 tier=dsv4f0731_nv **fid=281478d0**, 无 52e1ddb6。
- **52e1ddb6 泄漏源定位 = `dsvf0731_nv40666` 容器**: nv_tier_attempts 中 52e1ddb6 全带
  host_machine=`opc2sname-dsv4f40666`, caller=`hermes`, tier=dsv4f0731_nv, 30min 21/21 全败
  (RemoteDisconnected×15, 529×2, Timeout×2, empty_200×2, ~31-57s)。主 nv_gw(40006) 0 次 52e1ddb6。
- 40666 env: NVU_FID_DISCOVERY_ENABLED=1, MODEL=dsv4f0731_nv, NAME_MATCH=deepseek-v4-flash,
  NVCF_DEEPSEEK_FLASH_FUNCTION_ID=52e1ddb6。discovery 每 30min 扫到 281478d0+52e1ddb6 双 ACTIVE,
  但 281478d0 probe 恒 404 ("Keeping current") → 恒卡坏 fid 52e1ddb6。
- host 分离确认: cc4101-primary→`opc2sname`(40006), hermes→`opc2sname-dsv4f40666`(40666), 互不影响。

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **139/139 = 100% SR, 0 bad** | ✅ |
| 主 nv_gw pexec fid | 全程 281478d0 (健康), 0×52e1ddb6 | ✅ |
| 三 scoped 容器 health | 40006/40066/4101 全 ok | ✅ |
| 40666 容器 (hermes 线) 52e1ddb6 | 30min 21/21 全败 (~31-57s, RemoteDisconnected) | ⚠️ 越界容器 |
| 主 nv_gw env fid | 无 0731 覆盖 → config 默认 281478d0 | ✅ |
| fallback (cc2 线) | 0 次 | ✅ |
| host_machine | 主=opc2sname, 40666=opc2sname-dsv4f40666 | 分离 |

### 验证
- curl 40006/40066/4101 → 全 ok; cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 139/139 (0 bad); pexec 日志全 `fid=281478d0`。
- host_machine 实拉确认 52e1ddb6 归属 40666, 未入主 nv_gw。

### 关键判断
R891 疑"52e1ddb6 泄漏进主 nv_gw 的 dsv4f0731 rotation" **不准确** — 实拉铁证: 52e1ddb6 全由
**dsvf0731_nv40666** (hermes 线) 产生, 未进主 nv_gw(40006) 候选池。cc2 主链路 139/139 干净。
**不改码**: ①40666 不在 cc2 改动范围 (铁律: 只改 40006+40066); ②对 cc2 SR 无影响; ③若修 40666
(discovery probe 用 -0731 model 或 env 覆盖 fid) 属独立容器运维决策, 待归属确认后单独评估。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin (dsv4p/dsv4f/dsv4f0731/glm5_2_nv) + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `docker ps` → nv_gw(5h) / nv_gw_stable(5d) / dsv4p_nv40066(2d) / dsvf0731_nv40666(14h) 全 Up ✅

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0, TIER_TIMEOUT_BUDGET_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv
- cc4101(4101): PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv, CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions (铁律4 不主动改)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (主链, R-fid0731); dsv4f_nv function_ids=[52e1ddb6-c745-4802-93f5-ba012d04c336]
- ⚠️ dsvf0731_nv40666 (越界容器, 记录): NVU_FID_DISCOVERY_ENABLED=1, MODEL=dsv4f0731_nv, NAME_MATCH=deepseek-v4-flash, NVCF_DEEPSEEK_FLASH_FUNCTION_ID=52e1ddb6 → discovery probe 281478d0 恒 404, 卡坏 fid

## 下一步
- 主链 cc2 已 100% 干净, 下轮预期维持 NOP (无新事件)。
- **优先监控**: 主 nv_gw(40006) dsv4f0731 rotation 是否持续只出 281478d0 (0 bad 保持)。
- 52e1ddb6 浪费归属 **dsvf0731_nv40666 (hermes 线)**, 非 cc2 范围; 可选修复 = discovery probe 用
  `-0731` model 名 或 显式 env `NVCF_DEEPSEEK_FLASH_0731_FUNCTION_ID`=281478d0。待归属确认单独评估。
- 保持 cc4101-primary fallback=dsv4f0731_nv 不动。