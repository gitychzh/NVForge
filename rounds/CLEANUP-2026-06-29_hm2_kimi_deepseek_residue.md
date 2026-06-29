# 清理：HM2 hm40006 链路 kimi/deepseek 残留注释/映射

日期：2026-06-29
执行者：HM1（opc_uname）对 HM2 操作
性质：维护性清理（非参数调优轮次，不翻转交替优化标记）

## 背景

用户要求"彻底清理 HM2 模型链路、配置信息，干干净净不再有干扰"。
核对发现 hm40006 实际已是单模型 glm5.1（R262 起），但源码与注释里
仍残留 deepseek/kimi 三模型措辞，造成"远程还有别的模型信息"的误解。

## 核对结论（先纠正印象偏差）

- HM1（本机）：**没有** hm40006 链路在跑。NVCF pexec / mihomo 全在 HM2。
  "5 个 key 都是 deepseek、key3 直连、其他走 mihomo" 实为 HM2 的 env，
  且 HM2 是 **glm5.1**（不是 deepseek），key3 直连（HM_NV_PROXY_URL3 为空）。
- HM2：单模型 `glm5.1_hm_nv`，5 key RR，key1/2/4/5 走 mihomo 7894/7895/7897/7899，
  key3 直连。**key3 维持直连不改**（用户确认）。

## 清理内容（仅 HM2，符合铁律"只改对端"）

1. `proxy/hm-proxy/gateway/config.py`
   - `_OLD_RR_KEY_MAP`：删除 `nv_kimi`/`nv_deepseek`/`hm_nv_kimi`/`hm_nv_deepseek`
     四条残留映射，仅保留 glm5.1 与 `hm_nv` 别名（rr_counter.json 已只有
     `hm_nv_glm5.1`，迁移映射纯残留）。
   - 文件头 docstring 与各段注释：删除 R262/R208 历史里对 deepseek/kimi 的
     提及，仅保留指向当前 glm5.1 单模型的说明。
2. `proxy/hm-proxy/gateway/upstream.py`
   - 文件头 docstring：去掉"deepseek primary → glm5.1 → kimi last-resort"
     三模型措辞，改为单模型 glm5.1 说明。
   - `_build_pexec_body` docstring：去掉 deepseek/kimi strip_params 描述，
     tier_model 注释改为 `glm5.1_hm_nv, the only supported model`。
3. `proxy/hm-proxy/gateway/handlers.py`
   - 文件头 docstring：去掉"Three-tier fallback: deepseek→glm5.1→kimi"，
     改为单模型 glm5.1 说明。
4. `proxy/hm-proxy/gateway/error_mapping.py`
   - 文件头 docstring：去掉"R38.7: deepseek restored as tier 3"三模型措辞。

## 未改动（有意保留）

- `ms_uni41001` / `ms_uni41002` 容器：保留不动（CLAUDE.md：不在热路径，
  留作手动 fallback；用户确认保留）。
- key3 直连：维持现状（用户确认不改）。
- `~/.hermes/config.yaml` 第 593-594 行 `kimi-coding` 注释：这是 hermes 自身
  fallback provider 可选项枚举（整段 `#` 注释、未启用），属 hermes 上游
  文档，非 hm40006 链路残留，不动。
- `docker-compose.yml`：未改（env 已是单模型 glm5.1，无需动）。
- 所有 `.bak.20260629-174435` 备份：保留在 HM2 原地。

## 部署与验证

- 备份：HM2 `/opt/cc-infra/proxy/hm-proxy/gateway/{config,upstream,handlers,error_mapping}.py.bak.20260629-174435`
  + `/opt/cc-infra/docker-compose.yml.bak.20260629-174435`。
- config.py 非挂载、构建时 COPY 进镜像 → 必须 rebuild。ghcr.io 拉基础镜像
  被墙 EOF，按铁律第 6 条用 HM2 本地 mihomo 代理（docker0 网关 172.17.0.1:7892）
  `HTTP_PROXY=http://172.17.0.1:7892 docker compose build hm40006` 成功。
- restart 后验证：
  - 容器内 config.py 时间戳 = 17:45:49（更新版）
  - `_OLD_RR_KEY_MAP` 仅剩 glm5.1 三项
  - `/health`：5 keys、`nvcf_pexec_models=["glm5.1_hm_nv"]`、
    `hm_model_tiers=["glm5.1_hm_nv"]`、`hm_default_model="glm5.1_hm_nv"`
  - `grep -rIn "kimi\|deepseek" gateway/*.py` → 无残留
  - 端到端：`POST /v1/chat/completions` model=glm5.1_hm_nv → 200，
    返回 `z-ai/glm-5.1`，内容正常
- 4 文件 `python3 -m py_compile` 语法 OK。

## 当前 HM2 hm40006 链路全景（清理后）

```
Hermes(HM2) → 127.0.0.1:40006 (hm40006, 单模型 glm5.1_hm_nv)
  → NVCF pexec ai-glm5_1 (function_id 822231fa-…, ACTIVE)
  → 5 key 轮询 (k1..k5, HM_NV_KEY1..5)
    k1 → mihomo:7894   k2 → mihomo:7895   k3 → 直连
    k4 → mihomo:7897   k5 → mihomo:7899
  → NV integrate API
无模型级 fallback；5 key 全耗尽（429/空200/超时）才失败。
strip_params: thinking_budget (NVCF pexec 拒绝→400)；reasoning_effort 透传。
```

## 调优参数当前值（HM2，未本轮改动，仅记录）

| 参数 | 值 | 来源轮 |
|---|---|---|
| UPSTREAM_TIMEOUT | 70 | R273 |
| TIER_TIMEOUT_BUDGET_S | 128 | — |
| MIN_OUTBOUND_INTERVAL_S | 7.0 | R292 |
| KEY_COOLDOWN_S | 38 | R275 |
| TIER_COOLDOWN_S | 22 | R1 |
| HM_CONNECT_RESERVE_S | 22 | R1 |

> 注：本清理不翻转交替优化标记，下一轮仍按 RN_hm1_optimize_hm2.md /
> RN_hm2_optimize_hm1.md 既有约定继续。
