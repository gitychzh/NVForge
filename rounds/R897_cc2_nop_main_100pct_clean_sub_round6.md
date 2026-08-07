# R897 — cc2 NOP 巡检轮 (不改码)

> cc2 主链路连续第 **6** 轮 100% 干净。SR=100% ≥ 99% 且无新错误 → NOP。
> 全新 session 接棒，轮前数据已注入，直接判稳。

## 数据 (30min, live DB now()≈2026-08-07 08:30 CST approx)

### 轮前注入 30min 链路总览 (caller × status)
| caller | status | count |
|---|---|---|
| cc4101-primary | 200 | **126** |
| hermes | 502 | 6 |

- 按模型 SR: dsv4f0731_nv = 96.2% (126/131) — 但因 5 bad 全属 hermes (越界), cc2 主链实为 **126/126 = 100%**。
- cc4101-primary 专属: **200|126|10357|** → 全 200。
- fallback 触发: 0 (cc2 线)。

### 本轮复核 (实拉补证)
- **`nv_requests` caller×status**: cc4101-primary|200|126; hermes|502|6。bad 全为 hermes|502|all_tiers_exhausted|6。
- **cc4101-primary fid**: `281478d0 | 126` (0×52e1ddb6)。
- **request_id JOIN 铁证**:
  - cc4101-primary: 全 5 key (k0-k4) `281478d0 | pexec_success` 23~27 each → 主链 100% 成功。
  - hermes: 坏 fid `52e1ddb6` 失败共 21 条 (RemoteDisconnected 16, Timeout 3, 504 2) → **100% 归属 hermes caller**。
- **buffer 日志 (nv_gw --since 30m)**: cc4101-primary 全 attempt=1/5 `success_tool_call`, elapsed 7~10s, done=True closed=False, 0 重试/0 cooldown/0 429。无 BUFFER failed 链。
- **健康**: curl 4101 ok (primary=dsv4f0731_nv) / 40006 ok (5 keys) / 40066 ok。

## 改了什么: 无 (NOP)

### 依据
1. cc2 主链 (cc4101-primary, nv_gw 40006) 30min = **126/126 = 100% SR, 0 bad**, fid 全 281478d0。
2. 连续 6 轮干净 (R892 139/139, R893 153/153, R894 143/143, R895 137/137, R896 134/134, **R897 126/126**)。
3. 坏 fid 52e1ddb6 失败仍 100% 归属 hermes caller (JOIN 铁证), 未进主链候选池, 不触 cc2 范围。

## ⚠️ 新观察 (vs R896)
- R896 时 dsvf0731_nv40666 已不在 docker ps (疑似停)。**本轮重启后图像显示 40666 又回来了: `dsvf0731_nv40666 Up 15 hours`**（已在 docker ps）。
- hermes 线 bad (6× all_tiers_exhausted, 全带 52e1ddb6) 持续，与 40666 归来吻合 → R896 "泄漏疑似自愈" 判断不成立，泄漏源容器仍活动。
- **结论不变**: 40666 越界 (非 40006/40066)，JOIN 铁证 52e1ddb6 100% 属 hermes 线，未进 cc2 主链。不改码。

## 验证
- curl 4101/40006/40066 全 ok。
- 30min nv_requests cc4101-primary 实拉 = 126/126 (0 bad)。
- 30min nv_tier_attempts + JOIN = 主链 281478d0 全 success, 52e1ddb6 全属 hermes。

## 下一步
- 主链连续 6 轮 100%，维持 NOP 预期。
- 关注点: ①40666 容器是否长期存活 → hermes 线 52e1ddb6 泄漏持续 (不属 cc2, 但若污染到 40006/40066 候选再介入); ②主链 dsv4f0731 rotation 只出 281478d0 保持。

## 参数快照 (env, 本轮未改)
- nv_gw(40006): NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_FORCE_STREAM_UPGRADE=0,
  TIER_TIMEOUT_BUDGET_S=180, TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30, NV_INTEGRATE_KEY_COOLDOWN_S=90,
  NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  MIN_OUTBOUND_INTERVAL_S=10, NVU_BUFFER_MAX_RETRIES=5 (90×5=450s)
- cc4101(4101): PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, primary=dsv4f0731_nv,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions
  (铁律4 不主动改 fallback)
- config.py: dsv4f0731_nv function_ids=[281478d0-...]; dsv4f_nv function_ids=[52e1ddb6-...]
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle

## 铁律遵从
- ✅ 改前有数据 (轮前注入 + 实拉补证) / 改后验证 (NOP 无改动)
- ✅ 只改 HM2 40006/40066 范围 (本轮未改)
- ✅ ms_gw fallback 未动
- ✅ 所有记录写入仓库 (commit + push)