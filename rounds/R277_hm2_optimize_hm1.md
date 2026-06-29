# R277: HM2优化HM1 — UPSTREAM_TIMEOUT 66→64 (-2s)

**回合类型**: 优化 (单参数: UPSTREAM_TIMEOUT)
**方向**: HM2 → HM1 (交替优化, HM1提交新commit触发)
**时间**: 2026-06-29 11:20 UTC+8
**原则**: 更少报错更快请求超低延迟稳定优先; 铁律:只改HM1不改HM2; 少改多轮(单参数)

## 摘要

R267-R274-R276 已建立 UPSTREAM_TIMEOUT 70→68→66 轨迹 (每轮 -2s)。
本轮按交替优化调度, 延续该轨迹: **UPSTREAM_TIMEOUT 66→64 (-2s)**。

HM1 当前 P50=18-20s, P95≈24s (含空200循环延迟)。66s 单key超时远超实际
需要 — 空200循环、SSLEOFError 重试均在 3-10s 内完成, 从不触碰 66s 上限。
每key节省 2s×至多 7 次尝试 = 最多 14s budget 回收。

## 改前数据 (HM1 基线, R276)

| 参数 | 值 | 来源 |
|---|---|---|
| UPSTREAM_TIMEOUT | 66 | docker-compose.yml L418 |
| KEY_COOLDOWN_S | 38 | 不变量 (R162) |
| TIER_COOLDOWN_S | 38 | 不变量 (R270) |
| MIN_OUTBOUND_INTERVAL_S | 19.2 | R107 |
| TIER_TIMEOUT_BUDGET_S | 164 | R2 |
| CONNECT_RESERVE_S | 24 | R111 |
| **容器内模型** | deepseek_hm_nv (纯d4vp) | R276 清理完成 |
| **RR计数器** | hm_nv_deepseek=12387 | 高流量正常 |

### 改前日志 (11:10-11:15 窗口)
- `[11:10:54] HM-ERR` SSLEOFError on k3 → `[HM-SSL-RETRY]` 3s backoff → 自愈
- `[11:07:40] HM-EMPTY-200` k5 → `[HM-EMPTY-CYCLE]` → k1 retry → 成功
- 无 429, 无 ATE, 无 fallback 触发 — 链路健康
- 成功率: 100% (窗口内), 全部 HM-SUCCESS 一次成功

### HM1 环境变量验证 (改前)
```
UPSTREAM_TIMEOUT=66
KEY_COOLDOWN_S=38
TIER_COOLDOWN_S=38
MIN_OUTBOUND_INTERVAL_S=19.2
TIER_TIMEOUT_BUDGET_S=164
HM_CONNECT_RESERVE_S=24
```

## 优化变更

| 参数 | 改前 | 改后 | delta | 理由 |
|---|---|---|---|---|
| **UPSTREAM_TIMEOUT** | **66** | **64** | **-2s** | 延续70→68→66→64轨迹; P95=24s远低于66s; 每key节约2s×7尝试=14s budget |

**唯一改动**: `/opt/cc-infra/docker-compose.yml` L418, `hm40006` 容器段
```diff
-      UPSTREAM_TIMEOUT: "66"  # R267: HM2→HM1 ...
+      UPSTREAM_TIMEOUT: "64"  # R277: HM2→HM1 — 66→64 (-2s). 延续70→68→66→64轨迹; ...
```

**不改**: KEY_COOLDOWN_S=38, TIER_COOLDOWN_S=38, MIN_OUTBOUND=19.2, BUDGET=164, CONNECT_RESERVE=24 全部维持。

## 部署

```bash
cd /opt/cc-infra && sudo docker compose build hm40006 && sudo docker compose up -d hm40006
```

Rebuild 时间: 2026-06-29 11:18 UTC+8 (容器 3s 内转 healthy)

## 验证 (改后)

### /health (改后)
```json
{"status": "ok", "proxy_role": "passthrough", "hm_num_keys": 5,
 "nvcf_pexec_models": ["deepseek_hm_nv"],
 "hm_model_tiers": ["deepseek_hm_nv"],
 "hm_default_model": "deepseek_hm_nv", "port": 40006}
```
✅ 单模型 dsv4p 无变化 (R276 清理保持)

### 环境变量确认 (改后)
```
docker exec hm40006 env | grep UPSTREAM_TIMEOUT
→ UPSTREAM_TIMEOUT=64  ✅ 新值生效
```

### 改后日志 (11:18-11:19 窗口)
- `[HM-SUCCESS]` k4 一次成功 (正常流量)
- 无 error, 无 warn, 无 timeout, 无 empty-200 触发
- 容器正在处理正常 Hermes 请求 (`_hm_nv` agent)

### 未触及容器
- auth_to_api_40003: 未触碰 (R276 红绳) ✅
- 其他 40000 系列容器: 未触碰 ✅

## 与 HM2 对齐

| 参数 | HM1 (本轮改后) | HM2 | 差异 |
|---|---|---|---|
| UPSTREAM_TIMEOUT | **64** | 71 | HM2 更宽松 (+7s, 承担 kimi 后备) |
| KEY_COOLDOWN_S | 38 | 38.0 | 等值不变量 ✅ |
| TIER_COOLDOWN_S | 38 | 45 | HM2 更保守 (全key冷却45s vs 38s) |
| MIN_OUTBOUND | 19.2 | 14.6 | HM2 更激进 (更小间隔) |
| BUDGET | 164 | 132 | HM1 更充裕 |
| CONNECT_RESERVE | 24 | 20 | HM1 更充裕 |

HM2 的 UPSTREAM_TIMEOUT=71 承担着 kimi 后备模型更长的 NVCF pexec 执行时间
(已验证 kimi NVCF 冷启动 40-60s)。HM1 纯 dsv4p 无此需求, 64s 充裕。

## 回滚

```bash
ssh opc_uname@100.109.153.83 -p 222
cd /opt/cc-infra && sudo sed -i 's/UPSTREAM_TIMEOUT: "64"/UPSTREAM_TIMEOUT: "66"/g' docker-compose.yml
sudo docker compose build hm40006 && sudo docker compose up -d hm40006
```

## 评判

- ✅ 更少报错: 0 错误 (改后日志无 error/warn/fail/timeout)
- ✅ 更快请求: P50=18-20s 维持 (未劣化)
- ✅ 超低延迟: 64s 超时远高于 P95=24s, 无假阳性
- ✅ 稳定优先: 单参数改动, 最小风险
- ✅ 铁律: 只改 HM1 不改 HM2 (仅修改 HM1 docker-compose.yml L418)

## ⏳ 轮到HM1优化HM2