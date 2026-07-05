# R747: HM2 — GLM-5.1 全量清除 + legacy_* 退役 + 链路工程化

> 仅 HM2。HM1 不动 (HM1 仍用 legacy 40001 链, GLM-5.1 在 HM1 仍是现役).

## 改动背景 (用户三项要求)
1. **删除 GLM-5.1 任何信息**: NVCF 全系下架 GLM-5.1 (R703 起 6155636e/af904f0c/46f4fb53 均 INACTIVE).
   HM2 上残留的 glm5_1_nv tier / legacy glm5.1 后端 / litellm-glm51 配置 / rr_counter 残留键 全清.
2. **dsv4p_ms 是 hermes 一级回退, 删 glm5_2_ms 回退**: HM2 hermes fallback_providers 早已只含 dsv4p_ms
   (R703 部署). 本轮把 cc4101 (CC 自身链路) 的 fallback 也从 glm5_2_ms 改 dsv4p_ms, 全链一致.
3. **全系统扫描, 清除冗余, 工程化模块化**: 删 6 个 legacy 容器 + 5 个 legacy 源码目录 + 3 个
   litellm 死配置目录 + 4 个 legacy postgres DB + 全部 .bak 历史快照 (26+ 个) + __pycache__.

## 改前数据
- HM2 settings.json: ANTHROPIC_BASE_URL=4101 (走 cc4101, 不走 legacy 40001).
- legacy_cc_2 (40005) stream.py:223 SyntaxError, 容器虽 healthy 但 import 失败, 无法服务.
- legacy_cc_1/dispatch/codex/passthrough (40000-40003) + legacy_ms_litellm (41001) 在 HM2 零流量.
- cc4101 链路实测: claude-opus-4-8→glm5_2_nv, fallback glm5_2_ms (PRIMARY-FAIL 频繁, 502 占多数).

## 改动清单

### A. legacy_* 容器全退役 (6 容器 + 5 源码目录)
- 停并删: legacy_ms_litellm / legacy_cc_1 / legacy_cc_2 / legacy_dispatch / legacy_codex / legacy_passthrough.
- 删源码: proxy/legacy-ms-gateway / legacy-cc / legacy-dispatch / legacy-codex / legacy-passthrough.
- 删 R680 改名备份: proxy/ms-uni.bak.R680 / nv-uni.bak.R680.
- 删 logs: logs/legacy-40001..40005 / legacy-ms-gateway.
- compose: 删 6 个 service 块; NO_PROXY 去掉 legacy 服务名, 改为 `logs_db,nv_gw,ms_gw`.

### B. GLM-5.1 从 nv_gw 源码彻底移除 (bind-mount gateway/)
- config.py:
  - NVCF_PEXEC_MODELS 删 glm5_1_nv 条目 (留 kimi_nv / dsv4p_nv / glm5_2_nv).
  - NV_MODEL_TIERS: ["kimi_nv","dsv4p_nv","glm5_2_nv"] (原含 glm5_1_nv).
  - NV_MODEL_IDS / MODEL_MAP / MODEL_INPUT_TOKEN_SAFETY / FALLBACK_GRAPH 删 glm5_1_nv.
  - 注释中 GLM-5.1 字样全清 (R704 注释保留版本说明, 不留 glm5.1 literal).
- rr_counter.py: _TIER_RR_KEYS / _OLD_RR_KEY_MAP 删 glm5_1 相关 (nv_glm5_1 / hm_nv_glm5.1).
- pexec.py / handlers.py / upstream.py: 注释中 glm5.1 → glm5_2 或删除.
- rr_counter.json: 清除 nv_glm5_1:2 残留键 (重启后自愈为 {nv_dsv4p, nv_kimi}).
- compose env: 删 NVCF_GLM51_FUNCTION_ID.

### C. cc4101 fallback 改 dsv4p_ms (CC 自身链路)
- compose: FALLBACK_UPSTREAM_MODEL glm5_2_ms → dsv4p_ms.
- config.py / handlers.py / __init__.py / upstream.py: 默认值与注释同步 dsv4p_ms.
- converters.py: 删 "glm5.1-specific" 历史注释.

### D. 死配置目录 + postgres DB 清理
- 删 litellm-nv / litellm-glm51 / litellm-glm51-fb / litellm-nv-hm (4 个死目录).
- 删 scripts/verify.sh (引用已删容器).
- postgres drop: litellm_glm51 / litellm_glm51_fallback / litellm_glm51_7168 / litellm_nv (4 个死 DB, 共 80MB).
- compose: POSTGRES_MULTIPLE_DATABASES 去掉 litellm_nv_hm, 只留 hermes_logs.
- ms_gw config.py: 注释 "copy from litellm-glm51/config.yaml" 改为内联说明.

### E. 冗余 .bak 全清
- proxy 下 26 个 .bak.R* 全删 (含 19 个 GLM-5.1 痕迹).
- compose 17 个 .bak.* 全删.
- postgres schema .bak 删.
- 隐藏 .env.bak.* / .bak.R507_*.yml 删.
- 容器内 + 宿主 __pycache__ 清.
- 保留: .env.template (HM1/HM2 共享模板, HM1 仍用 legacy 链, 不动).

## 改后验证 (2026-07-05 18:00)
- 容器: 仅 cc4101 / ms_gw / nv_gw / logs_db (4 个).
- compose services: cc4101 / logs_db / ms_gw / nv_gw.
- nv_gw /health: nvcf_pexec_models=["kimi_nv","dsv4p_nv","glm5_2_nv"], tiers 同, 无 glm5_1.
- ms_gw /health: models=["glm5_2_ms","dsv4p_ms"], default=glm5_2_ms.
- cc4101 /health: primary=glm5_2_nv, fallback=dsv4p_ms.
- 端到端: curl cc4101 /v1/messages (claude-opus-4-8) → primary conn-refused (nv_gw 重启瞬时) →
  FALLBACK-OK dsv4p_ms 2344ms 返回 thinking content. CC 链路通.
- rr_counter.json: {"nv_dsv4p":1989,"nv_kimi":9} (无 nv_glm5_1).
- postgres DB: 仅 hermes_logs + litellm + postgres.
- GLM-5.1 全局扫描 (排除 .env.template): ZERO TRACES.

## HM2 最终链路
```
hermes   → 127.0.0.1:40006 (nv_gw dsv4p_nv)     → fallback dsv4p_ms (ms_gw 40007)
openclaw → 127.0.0.1:40006 (nv_gw glm5_2_nv)    → fallback glm5_2_ms (ms_gw 40007)  [openclaw 自己的回退, 未动]
opencode → 127.0.0.1:40006 (nv_gw kimi_nv)      → fallback glm5_2_ms (ms_gw 40007)  [声明, 未动]
CC 自身  → 127.0.0.1:4101  (cc4101 glm5_2_nv)    → fallback dsv4p_ms (ms_gw 40007)  [R747 改]
```

## 风险/注意
- HM1 未动: HM1 settings 走 legacy 40001, HM1 仍有 legacy 容器 + glm5.1 后端. 本轮严格只 HM2.
- .env.template 保留 GLM-5.1 注释 (服务 HM1, 跨机共享).
- HM2 如需重启 logs_db, POSTGRES_MULTIPLE_DATABASES=hermes_logs, 不再建旧 DB.
- peer fallback (nv_gw → HM1 nv_gw) 仍指向 100.109.153.83:40006, 未动.
