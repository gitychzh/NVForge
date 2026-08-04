# R-dsv4f0731-deploy: 自优化任务切换至 dsv4f0731_nv 全链路部署

- **日期**: 2026-08-05 02:40 CST
- **容器**: dsvf0731_nv40666 (port 40666, DeepSeek V4 flash via NVCF)
- **类型**: 自优化任务目标模型切换 + 全链路部署
- **前置**: R-dsv4f0731-fix 已修复 404 (model 名对齐 FID 52e1ddb6)

## 背景

用户要求: "修改这个自优化任务, 优化 dsv4f0731_nv 模型, 部署在 40666 容器上"。

原自优化 cron job (`a7acb71b05e9`) 目标 `dsv4f_nv`, 现切换为 `dsv4f0731_nv`。
`dsv4f0731_nv` 与 `dsv4f_nv` **共享同一 FID `52e1ddb6`** (ai-deepseek-v4-flash),
但作为独立 tier 独立调优参数, track 独立历史数据。

## 数据/决策依据

- 原 `dsv4f_nv` 24h 成功率仅 52.3% (149 请求, 71 错误, 62 all_tiers_exhausted)
- fallback `dsv4f0731_ms` 100% 成功率 (28/28, avg 11.7s)
- 方案选择: 同 FID `52e1ddb6` 改名 dsv4f0731_nv, 独立调优参数 (方案1)

## 修改清单

| # | 文件 | 修改 | 状态 |
|---|---|---|---|
| 1 | `/opt/cc-infra/proxy/nv-gw/gateway/config.py` | 新增 dsv4f0731_nv: NV_MODEL_TIERS, NV_MODEL_IDS, MODEL_MAP, MODEL_INPUT_TOKEN_SAFETY (复用 FID 52e1ddb6) | ✅ |
| 2 | `/opt/cc-infra/docker-compose.yml` | (a) 40666: 新增 NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_FID_DISCOVERY_MODEL=dsv4f0731_nv, NVU_PEER_FB_SKIP_MODELS 加 dsv4f0731_nv; (b) hm4104: PRIMARY_MODEL=dsv4f0731_nv | ✅ |
| 3 | `/home/opc2_uname/.hermes/scripts/dsv4f_self_opt_collect.sh` | 全量替换 dsv4f_nv → dsv4f0731_nv (25 处, 0 残留) | ✅ |
| 4 | `~/.hermes/cron/jobs.json` (job a7acb71b05e9) | name → dsv4f0731_nv40666 自优化, model → dsv4f0731_nv, prompt 3处 dsv4f_nv 替换 | ✅ |
| 5 | 容器重启 | 40666: `docker restart` (重载最新 config.py); hm4104: `docker restart` (重置 circuit breaker) | ✅ |

## 关键坑 (记录)

1. **bind-mount 不自动重载**: config.py 改了文件, 但 Python 进程 import 时已缓存旧值。
   `docker compose up -d` 如果判断无变化不 recreate, 必须 `docker restart` 强制重载。
   这是 404 修复 (R-dsv4f0731-fix) 后仍只认旧 model 名 `-0731` 的根因。

2. **`docker restart` 不读取 compose 新 env**: 改 compose environment 后必须
   `docker compose up -d` (触发 recreate) 才能应用新 env。本次 hm4104 的
   PRIMARY_MODEL 变更用 `docker compose up -d` 应用, 之后 config.py 修复用
   `docker restart` 重载。

3. **NVCF 环境污染 (非配置问题)**: 复用 FID 52e1ddb6 意味着 dsv4f0731_nv 继承
   dsv4f_nv 的 NVCF 端点健康状况。当前 NVCF 端点退化 (SSLEOFError/529/连接重置),
   与 dsv4f_nv 之前 62/71 all_tiers_exhausted 一致。短 curl (stream=false) 恰好命中
   健康 key 成功; 流式长请求全 5 key 失败 → NV-PEER-FB → 502 → hm4104 fallback。

4. **peer-fb skip list 语义**: `NVU_PEER_FB_SKIP_MODELS` 含 dsv4f0731_nv 是**正确**做法
   (与 dsv4f_nv 一致)。它在 all_tiers_exhausted 时跳过 peer 二次尝试 (同 function 同坏,
   省 ~180s), 直接返回 502 让 agent 落 ms_gw。不是错误。

## 验证 (全部通过)

- 40666 /health: status ok, tiers 含 dsv4f0731_nv (>kimi/dsv4p/dsv4f/glm5_2)
- 4104 /health: primary_model=dsv4f0731_nv, primary_url=http://dsvf0731_nv40666:40666/v1
- 40666 env: NVU_TIER_BUDGET_DSV4F0731_NV=180, NVU_FID_DISCOVERY_MODEL=dsv4f0731_nv,
  NVU_PEER_FB_SKIP_MODELS 含 dsv4f0731_nv
- hm4104 env: PRIMARY_MODEL=dsv4f0731_nv, FALLBACK_MODEL=dsv4f0731_ms
- collect 脚本: dsv4f_nv=0 残留, dsv4f0731_nv=25
- cron job: name=dsv4f0731_nv40666 自优化, model=dsv4f0731_nv, prompt 无 dsv4f_nv 裸引用
- DB (10min): dsv4f0731_nv 17 请求, 64.7% SR (11/17), avg 32.1s

## 当前状态

- hm4104 primary=dsv4f0731_nv 已生效, 但 NVCF 端点退化导致间歇 fallback (正常兜底)
- 40666 dsv4f0731_nv 成功请求存在 (NV-SUCCESS), 也有 NVCF 529/SSL 重试 (环境问题)
- 自优化 cron 每 2min 运行, collect 脚本按 tier_model='dsv4f0731_nv' 过滤 track

## 下一步

- 待 NVCF 端点恢复后, 观察 30min 窗口 dsv4f0731_nv SR 是否达标
- 若 SR 稳定, 自优化任务将基于 dsv4f0731_nv 独立调参
- 若 NVCF 持续退化, 评估是否回退 hm4104 primary 到其它可用模型