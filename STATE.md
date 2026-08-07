# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R897 (NOP 巡检轮/不改码 — cc2 主链路连续第 6 轮 100% 干净; JOIN 铁证坏 fid 52e1ddb6 仍 100% 归属 hermes 线, 非 cc2 范围)**
> cc4101-primary (主 nv_gw:40006) 实时 30min = **126/126 = 100% SR, 0 bad**;
> nv_tier_attempts JOIN nv_requests 裁决: cc4101-primary 126× pexec_success 全 fid=281478d0,
> 坏 fid 52e1ddb6 21 条失败 (RemoteDisconnected 16/Timeout 3/504 2) **100% 归属 hermes caller**;
> 主 nv_gw pexec 全程 fid=281478d0 (健康), buffer 全程 attempt=1/5 即 success_tool_call (7-10s)。
> 上轮: R896 (NOP, 主链 134/134=100%)

## 本轮 (R897) 改动 + 依据 + 验证

### 改动: 无 (NOP。cc2 主链路连续 6 轮 100% 干净, 无新错误类; JOIN 铁证持续确认坏 fid 归属 hermes 非 cc2)

### 依据 (live DB 30min, ≈2026-08-07 08:30 CST)

- 30min cc4101-primary (主 nv_gw:40006) = **126/126 全 200, 0 bad (100% SR)**。
- 【核心铁证】`nv_tier_attempts JOIN nv_requests ON request_id`:
  - cc4101-primary | dsv4f0731_nv | **281478d0 | pexec_success ×126** (k0~k4 各 23~27) → 主链 100% 成功, 0×52e1ddb6。
  - hermes | dsv4f0731_nv | **52e1ddb6 | 失败 ×21** (RemoteDisconnected 16, Timeout 3, 504 2)。
- buffer 日志: cc4101-primary 全 attempt=1/5 `success_tool_call`, elapsed 7~10s, done=True closed=False,
  0 重试 / 0 cooldown / 0 429。
- 30min nv_requests bad (6): hermes|502|all_tiers_exhausted ×6 (全带 52e1ddb6)。cc4101-primary 0 bad。
- **⚠️ 新观察 (vs R896)**: R896 时 dsvf0731_nv40666 已不在 docker ps (疑似停)。本轮 `docker ps`
  显示 **dsvf0731_nv40666 Up 15 hours** (又回来) → R896 "泄漏源疑似自愈" 判断不成立, 40666 仍活动。
  hermes 线 bad 持续与 40666 归来吻合。**但 40666 越界 (非 40006/40066), 泄漏 100% host 分离,
  join 铁证 0×52e1ddb6 进 cc2 主链, 不改码。**

### 本轮数据

| 指标 | 值 | 状态 |
|---|---|---|
| 主 nv_gw(40006) cc4101-primary | **126/126 = 100% SR, 0 bad** | ✅ |
| 主 nv_gw pexec 成功 fid | 126/126 全 281478d0, 0×52e1ddb6 (join 铁证) | ✅ |
| buffer (cc4101-primary) | 全 attempt=1/5 success_tool_call, 7-10s, 0 重试 | ✅ |
| hermes 线 bad (52e1ddb6) | 失败 ×21 (all_tiers_exhausted ×6) | ⚠️ 越界 |
| 存留 scoped 容器 health | 4101/40006/40066 全 ok | ✅ |
| dsvf0731_nv40666 | **Up 15 hours (归来, R896 判断自愈不成立)** | 👀 观察 |
| fallback (cc2 线) | 0 次 | ✅ |

### 验证
- curl 4101/40006/40066 → 全 ok; cc4101 primary=dsv4f0731_nv。
- 30min nv_requests cc4101-primary 实拉 = 126/126 (0 bad)。
- 30min nv_tier_attempts + JOIN nv_requests = 主链 281478d0 全成功, 52e1ddb6 全属 hermes。

### 关键判断
cc2 主链路连续 6 轮 (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134,
**R897 126/126**) 100% SR 干净。坏 fid 52e1ddb6 失败持续 100% 属 hermes caller (越界 40666 泄漏),
未进 cc2 主链候选池。
**不改码**: ①主链 SR 100% 无优化需求; ②52e1ddb6 越 cc2 范围 (40666 非 40006/40066);
③容器级分离持续奏效, cc2 主链不受污染。

## 修复链 (沿用, R827+R828+R829+R833+R813 + R869+R876+R891)
1. glm5_2_nv 全 key 疲劳 → R829/R833 fail-fast + cc4101 动态 primary → dsv4f0731_nv
2. dsv4f0731_nv 一次成功 (主链已用健康 fid 281478d0), 用户无感知
3. 多 tier round-robin + func_health fid 健康选择自适应吸收底层跨 key/fid 瞬态失败

## 健康检查
- `curl localhost:4101/health` → ok ✅ (cc4101, primary=dsv4f0731_nv)
- `curl localhost:40006/health` → ok ✅ (nv_gw, passthrough, 5 keys)
- `curl localhost:40066/health` → ok ✅ (dsv4p_nv40066)
- `docker ps` → cc4101 / nv_gw / dsv4p_nv40066 / nv_gw_stable / **dsvf0731_nv40666 (Up 15h)** 全 Up

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s)
- cc4101(4101): PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv,
  FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions, FALLBACK_UPSTREAM_MODEL=glm5_2_ms
  (铁律4 不主动改 fallback)
- config.py: dsv4f0731_nv function_ids=[281478d0-f307-49f4-9e0f-080b63b16c47] (主链 R-fid0731);
  dsv4f_nv function_ids=[52e1ddb6-c745-4802-93f5-ba012d04c336]
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle

## 下一步
- 主链 cc2 连续 6 轮 100% 干净, 下轮预期维持 NOP。
- **优先监控**: ①主链 dsv4f0731 rotation 持续只出 281478d0 (0 bad 保持); ②40666 容器持续存活 →
  hermes 线 52e1ddb6 泄漏持续 (不属 cc2; 若污染进 40006/40066 候选池再介入, 目前 join 铁证 0 泄漏)。