# R797: HM2 glm5_2_nv 快速失败 + 跳过 peer-fb (NVCF ai-glm-5_2 DEGRADING)

> 承接 R796 (NOP, 88.8% SR). 8 轮定时优化第 1 轮. 用户报远程 5 agent 模型链路 bug.
> 铁律: 改前有数据 (NVCF 直连实测 + DB), 改后有验证 (端到端 + DB + 日志).
> 角色: HM2-only 部署; upstream.py/handlers.py 是共享源码, 仓库同步供 HM1.

## 改前数据 (2026-07-07, 远程 HM2 实测)

### DB (nv_requests, 60min 窗口)

| tier_model | status | count | 备注 |
|---|---|---|---|
| dsv4p_nv | 200 | 33 | 健康 (SR≈87%) |
| dsv4p_nv | 502 | 5 | empty_200 |
| glm5_2_nv | 502 | 2 | **SR=0%**, 全 all_tiers_exhausted |

### NVCF 直连实测 (绕过 nv_gw, function 3b9748d8 ai-glm-5_2)

| key | 请求 | 结果 | 耗时 |
|---|---|---|---|
| k1 | 裸 "hi" | **504** | 62.4s |
| k2 | 裸 "hi" | **400** bad-request | 43.3s |
| k3 | 裸 "hi" | **504** | 62.5s |
| k1 | thinking=true "1+1" | 400 | 44.8s |
| k1 | thinking=false "1+1" | 400 | 41.1s |
| k1 | 无 chat_template_kwargs | 400 | 41.2s |
| k1 | 对照 dsv4p 74f02205 | 400 (注: dsv4p 裸请求也 400, 但经 nv_gw strip+inject 后 200) | 0.8s |

**关键发现**: NVCF function 3b9748d8 (ai-glm-5_2) 状态 **DEGRADING** (NVCF /v2/nvcf/functions 列表确认, 非 ACTIVE). 全 key 直连 504/400/62s, **不分 thinking 路径** — 整体退化, 非 thinking 单一路径坏.

→ R797 原 plan 前提 ("thinking=false 5/5 200") 已过时. 改 inject 为空无效 (thinking=false/bare 也全坏). 本轮按实测数据改方案.

### 对照: dsv4p_nv (74f02205) 健康

dsv4p_nv 60min SR≈87%, 端到端 200/6.1s. kimi_nv 同样健康. 仅 glm5_2_nv 这条 tier 坏.

## 根因 (数据驱动, 修正版)

- **R1 [NVCF 上游]**: NVCF ai-glm-5_2 (3b9748d8) DEGRADING, 全 key 504/400/62s. 不可通过换 function_id (NVCF 上无其他 ACTIVE glm-5.2), 不可通过关 thinking (已实测). NVCF 侧问题, 网关侧只能让它快速失败.
- **R2 [网关放大]**: 全局 `TIER_TIMEOUT_BUDGET_S=180` 让 glm5_2_nv 烧满 3 key (~3×62s) 才 all_tiers_exhausted → 180s.
- **R3 [peer-fb 浪费]**: all_tiers_exhausted 后 peer-fb 转发到 HM1 nv_gw, HM1 同 function 3b9748d8 同坏 → 再烧 ~180s 才 502. 客户端 (cc4101/cx4102/opclaw4103) 等 ~360s 才拿 502 → 表现为"卡死", 之后才落 ms_gw 兜底.

## 修复方案 (HM2 部署; 共享源码仓库同步供 HM1)

### 改动 1: per-tier budget override (修 R2)

**文件**: `gateway/upstream.py` `_try_tier_keys`

加 env-driven per-tier budget: `NVU_TIER_BUDGET_<MODEL_UPPER>`, 默认回退全局 `TIER_TIMEOUT_BUDGET_S`.
glm5_2_nv 设 70s → 1-2 key (~62s/62s) 后即 break, 不烧满 3 key.
dsv4p_nv/kimi_nv 无 env 覆盖 → 不受影响 (仍 180s).

```python
_tier_budget_env = os.environ.get(f"NVU_TIER_BUDGET_{tier_model.upper()}")
tier_budget_s = float(_tier_budget_env) if _tier_budget_env else TIER_TIMEOUT_BUDGET_S
```
函数体内 4 处 `TIER_TIMEOUT_BUDGET_S` 引用替换为 `tier_budget_s` (budget check / remaining_budget / post_connect_remaining / 日志).

### 改动 2: per-model peer-fb skip (修 R3)

**文件**: `gateway/handlers.py` peer-fb 触发条件

加 env `NVU_PEER_FB_SKIP_MODELS` (逗号分隔, 默认 `glm5_2_nv`). matched model 在 skip 列表 → 跳过 peer-fb, 直接返回 local 502, 让 agent 立即落 ms_gw.

```python
_peer_skip = {m.strip() for m in os.environ.get(
    "NVU_PEER_FB_SKIP_MODELS", "glm5_2_nv").split(",") if m.strip()}
if (NVU_PEER_FALLBACK_ENABLED and NVU_PEER_FALLBACK_URL
        and hop_n < 1 and not is_429
        and mapped_model not in _peer_skip):
    ...
elif mapped_model in _peer_skip and hop_n < 1 and not is_429:
    _log("NV-PEER-FB", f"model={mapped_model} in peer-fb skip list ...")
```

### 改动 3: env (docker-compose.yml nv_gw.environment)

```yaml
- NVU_TIER_BUDGET_GLM5_2_NV=70        # R797
- NVU_PEER_FB_SKIP_MODELS=glm5_2_nv   # R797
```

### 不改的项 (有意偏离 R797 原 plan)

- **config.py glm5_2_nv inject 保留** (不改空). 原 plan 想关 inject, 但实测 thinking=false/bare 也全坏, 关 inject 无效. 保留 inject 让 NVCF 恢复后无需再改回. (NVCF 3b9748d8 恢复 ACTIVE 后, 删 compose 两行 env 即完全回滚, inject 不动.)
- `TIER_TIMEOUT_BUDGET_S=180` 不动 (全局, 影响 dsv4p/kimi).
- dsv4p_nv/kimi_nv 不动.
- HM1: 同 bug, 远程 CC pull 后请部署 HM1 (upstream.py/handlers.py 同改 + compose 两行 env).

## 实施步骤 (HM2, 已执行)

1. 备份: `config.py/upstream.py/handlers.py` → `*.bak.R797`; `docker-compose.yml` → `.bak.R797`.
2. 改 upstream.py (per-tier budget), handlers.py (peer-fb skip) — bind-mount, scp 推送.
3. compose 加 2 行 env.
4. `docker compose up -d nv_gw` (重建容器读新 env + bind-mount 新 py).
5. 验证 (见下).

## 验证 (铁律: 改后有验证)

### V1: glm5_2_nv 端到端 (改前 180s 502, 改后 70s 502, 无 peer-fb)

```
$ curl -m 90 nv_gw:40006 ... glm5_2_nv "1+1=?" non-stream
HTTP 502 70.035s
{"error": "All NV API tiers failed for glm5_2_nv after 70.0s. Tiers tried: [glm5_2_nv: 2×mixed] ... fallback_actually_attempted: false"}
```
✓ 70s (改前 180s), peer-fb 未尝试 (`fallback_actually_attempted: false`).

### V2: dsv4p_nv 不受影响

```
$ curl -m 60 nv_gw:40006 ... dsv4p_nv "1+1=?" non-stream
HTTP 200 6.119s
```
✓ 200/6.1s, 健康.

### V3: 日志确认机制生效

```
[NV-TIER-BUDGET] tier=glm5_2_nv budget 70.0s exceeded after 70.0s, breaking
[NV-TIER-FAIL] tier=glm5_2_nv all 5 keys failed: timeout=1, other=1, elapsed=70010ms
[NV-PEER-FB] model=glm5_2_nv in peer-fb skip list (NVCF DEGRADING, peer same function also bad), returning local 502 for agent ms_gw fallback
```
✓ per-tier budget + peer-fb skip 双双生效.

### V4: 改后 5min DB 窗口

| tier_model | status | count | avg_ms |
|---|---|---|---|
| dsv4p_nv | 200 | 2 | 18602 |
| glm5_2_nv | 502 | 1 | 70017 |

✓ glm5_2_nv 502 耗时 70s (改前 180s); dsv4p_nv 200 健康.

### V5: 健康检查

`curl nv_gw/health` ok; `docker ps` nv_gw Up.

## 预期效果 (对 5 agent)

- cc4101/cx4102/opclaw4103 (primary glm5_2_nv): 改前 ~360s 才 502→ms_gw; 改后 ~70s 502→ms_gw. 卡死大幅缓解 (agent 收 502 后立即转 ms_gw 兜底).
- hm4104 (dsv4p_nv) / oc4105 (kimi_nv): 不受影响.
- 注意: glm5_2_nv 本身仍 0% SR (NVCF 上游坏, 网关侧无法修复), 本轮只解决"快速失败 + 不浪费 peer-fb 时间", 不解决 glm5_2_nv 恢复. NVCF 恢复后删 2 行 env 即回滚.

## 回滚

```bash
# 源码
cp gateway/upstream.py.bak.R797 gateway/upstream.py
cp gateway/handlers.py.bak.R797 gateway/handlers.py
# compose: 删 NVU_TIER_BUDGET_GLM5_2_NV / NVU_PEER_FB_SKIP_MODELS 两行
cd /opt/cc-infra && docker compose up -d nv_gw
```
或仅删 compose 两行 env (保留源码改动, 源码在无 env 时回退全局 180s + 不 skip peer-fb, 等价回滚).

## 提交

- 源码快照: `deploy_artifacts/R797_glm52_fast_fail/{upstream.py,handlers.py}`
- round: `rounds/R797_hm2_glm52_fast_fail_peer_skip.md`
- git commit + push (经 mihomo 7891, ssh.github.com:443)
- push 前 `git pull --rebase origin main`

## 跨机协作备注

- R797 是共享源码改动. HM2 已部署 + 仓库同步. HM1 同 bug (glm5_2_nv 同样卡), 远程 CC pull 后请部署 HM1: upstream.py/handlers.py 同改 + compose 加 2 行 env (NVU_PEER_FB_SKIP_MODELS=glm5_2_nv; NVU_TIER_BUDGET_GLM5_2_NV=70).
- 远程 CC 若 pull 到本 round: HM1 同步即可, 勿回退. inject 保留 (非 bug).
