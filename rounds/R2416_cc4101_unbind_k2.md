# R2416 — cc4101-primary 解除固定 k2 绑定 (HM2)

## 时间
2026-07-28 02:20 UTC (10:20 CST)

## 背景
cc2 session f4abcefb 中断，报 502 upstream failed。DB 30min 窗口显示 cc4101-primary 连续 502 `all_tiers_exhausted`，根因是 NVU_CALLER_KEY_MAP 固定绑 cc4101→k2 (idx=1)，而 k2 被 NVCF 账户级 429 限流进入 600s cooldown，KeyManager 直接拒绝所有 cc4101 请求 (6-9ms 秒级 502)。NVU_DISABLE_MS_FALLBACK=1 无兜底。

## 数据 (30min 窗口, 01:57-02:07 UTC)
- nv_requests cc4101-primary: 11×502 all_tiers_exhausted, 8×200 (SR 42%)
- 502 duration: 多数 6-9ms (KeyManager 直接拒绝), 最长 9.1s
- 200 全走 k2 (nv_key_idx=1), k2 恢复时才能成功
- nv_tier_attempts: k2 429 count=12, cooldown=600s; probe k2 status=404 持续不可用
- cc_requests: 502 全是 upstream_error/server_5xx, fallback_triggered=f
- kimi_nv (caller=unknown, 不绑固定key) 正常轮转 k0-k4

## 根因
cc4101 固定绑 k2 → k2 被 NVCF 429 限流 → cc4101 所有请求秒级 502 → cc2 session 中断 → cc2-resume.timer 新轮也立即 502

## 修复
从 `NVU_CALLER_KEY_MAP` 中移除 `cc4101-primary:1`，让 cc4101 回退到正常 5-key 轮转 (与 kimi_nv/unknown caller 一样)。

```
# 改前
NVU_CALLER_KEY_MAP=cc4101-primary:1;hermes:2;openclaw:3;opencode:4

# 改后
NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
```

备份: `docker-compose.yml.bak.R2409_ccaller_unbind`

## 验证
1. `docker compose up -d nv_gw` → health ok, `NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4` ✓
2. E2E curl cc4101 → 200, 返回 glm5_2_nv 正常内容 ✓
3. DB 铁证: 重启后 cc4101-primary 请求用了 nv_key_idx=0 (k1) 和 nv_key_idx=2 (k3)，egress_ip 不同 (134.195.101.193 vs .195)，完全绕开挂掉的 k2 ✓
4. 3×200 连续成功, 0×502 (重启后) ✓

## 参数表
| 参数 | 改前 | 改后 | 说明 |
|---|---|---|---|
| NVU_CALLER_KEY_MAP | `cc4101-primary:1;hermes:2;openclaw:3;opencode:4` | `hermes:2;openclaw:3;opencode:4` | cc4101 不再固定绑 k2 |

## 预期效果
- cc4101 单 key 挂不再拖垮全部请求，5-key 轮转自动绕开 cooling key
- cc2 session 不再因单 key 450 而中断
- hermes/openclaw/opencode 仍保持各自固定 key 绑定不变

## 注意
- k2 仍在 NVCF cooldown (404)，但不再影响 cc4101
- hermes:2/openclaw:3/opencode:4 固定绑定保留不动
- NVU_DISABLE_MS_FALLBACK=1 不变 (R-nvonly 方向)
- 如果 cc4101 也有 buffer 层 (NVU_BUFFER_CALLERS=cc4101-primary)，buffer 层也会受益于不绑单 key
