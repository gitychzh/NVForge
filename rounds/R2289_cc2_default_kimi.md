# R2289 (cc2, HM2 only): cc2 默认模型 dsv4p_nv→kimi_nv + 1M 上下文 settings 回退到 120K 量级

## 背景

用户要求: 把远程 cc2 的默认模型改为 kimi-k2.6 (kimi_nv), 并因 kimi 上下文只有 128K,
把之前为 GLM5.2 1M 设的相关参数做相应修改, 让 cc2 自优化任务正常跑起来优化 kimi_nv.

## 数据基础 (改前必有数据)

kimi 变体可用性裸测 (HM1+HM2 真直连, N=10/key, 5 key):
- kimi-k2.6 pexec: 两台均 10/10 100% (avg 0.86s/0.83s, 三模型里最快)
- kimi-k3 / kimi-k2.7-code (pexec 借 k2.6 fid + integrate): 全 0/10 404 ("Inference error" / "404 page not found") — NVCF 账户上 kimi 只有 f966661c (nvquery-kimi-k2_6) 一个 function, 无 k2.7/k3 登记.
- 对照: minimax-m2.7 pexec 两台 100%, integrate 90-100% (意外收获, 非 kimi).

cc4101 MODEL_MAP 机制 (R1648 终态): 所有前端名 (cc-glm5-2 / claude-* / 裸名) 都映射到
`PRIMARY_UPSTREAM_MODEL` 变量, 改一处 env 即全跟随. nv_gw config.py:
- `MODEL_INPUT_TOKEN_SAFETY["kimi_nv"]=131072` (128K, 本就正确, 无需改)
- kimi tier `inject={"reasoning_effort":"low"}`, `strip_params=["thinking_budget"]` (L72-73, 已正确, 不动)

## 改动清单 (HM2 only, 全程不碰 HM1)

### 1. /opt/cc-infra/docker-compose.yml L209 (cc4101 env)
`PRIMARY_UPSTREAM_MODEL=dsv4p_nv` → `kimi_nv`
- 备份: docker-compose.yml.bak.R2286_kimi
- MODEL_MAP 全跟随, cc2 发 model=cc-glm5-2 → cc4101 重写为 kimi_nv → nv_gw 路由到 NVCF kimi function (f966661c).
- 回滚: 改回 dsv4p_nv (或 glm5_2_nv) + `docker compose up -d cc4101`.

### 2. ~/cc_ps/cc2_repair_self/.claude/settings.json (cc2 项目级)
kimi ctx=128K, 旧的 1M 窗 (R2191 为 glm5.2 设) 会让 cc2 请求塞进 >128K input → NVCF 400/挂死 → 0 数据可优化. 回退到 120K 量级:
- `contextWindow`: 1000000 → 120000
- `autoCompactWindow`: 900000 → 100000
- `env.CLAUDE_CODE_AUTO_COMPACT_WINDOW`: 900000 → 100000
- `env.CLAUDE_CODE_MAX_OUTPUT_TOKENS`: 8192 (不动, kimi max_tokens 足够)
- 备份: settings.json.bak.R2286_kimi

### 3. ~/cc_ps/cc2_repair_self/.claude/cc2_resume.sh L12 (export, 生效值)
`export CLAUDE_CODE_AUTO_COMPACT_WINDOW=900000` → `100000`
- 注: resume.sh 的 export 最终生效覆盖 settings.json env 块 (R2199 已证), 故此处必须同步改, 否则项目级 settings 改了也白搭.
- 备份: cc2_resume.sh.bak.R2286_kimi

### 4. ~/cc_ps/cc2_repair_self/CLAUDE.md (cc2 认知文档)
- 链路图: `nv_gw(40006, glm5_2_nv)` → `nv_gw(40006, kimi_nv)`
- 正反馈段: "glm5_2_nv 流量" → "kimi_nv 流量"; "尽量多走 glm5_2_nv(40006)" → "kimi_nv(40006)"
- R2191 段(1M context)顶部插入 R2286 覆盖告示: 说明 1M settings 已回退到 120K, 原 1M 前提是 glm5.2 不适用 kimi; R2191 段保留作历史背景.
- 备份: CLAUDE.md.bak.R2286_kimi

### 未改 (有意)
- nv_gw config.py `MODEL_INPUT_TOKEN_SAFETY["kimi_nv"]` 本就 131072, 无需改.
- kimi tier `inject`/`strip_params` 本就正确 (reasoning_effort=low + strip thinking_budget), 不动.
- NVU_MS_FALLBACK_MODELS / NVU_BIG_INPUT_MODELS 仍只 glm5_2_nv: kimi 不在 ms_fallback/big_input breaker 列表 → kimi 失败直接暴露给 cc2 (cc4101 层仍有 ms_gw 兜底不硬中断), cc2 才有真实 kimi 数据可优化. 这是刻意的: 让 cc2 自己看到 kimi 的真实故障, 才能据此优化.
- HM1 全程不动 (铁律之铁律: 只改 HM2).

## 验证 (改后必有验证)

1. `docker compose up -d cc4101` → cc4101 Recreated.
2. env: `docker exec cc4101 env | grep PRIMARY_UPSTREAM_MODEL` = `kimi_nv` ✅
3. /health: `{"primary":"kimi_nv"}` ✅
4. cc4101 日志: `[REQ] model=cc-glm5-2→kimi_nv cc_stream=True` ✅
5. E2E 直测 cc4101→nv_gw→NVCF kimi:
   `curl /v1/messages model=cc-glm5-2` → 返回 `model: kimi_nv`, content `KIMI-OK`,
   `stop_reason: end_turn`, input_tokens 17. ✅
6. cc2 自优化 timer 已 active + enabled, 重启 cc4101 后下一轮 (15:10) 自动起跑,
   生成 kimi_nv 流量: cc4101 5min 内记 5+ 条 `[REQ] model=cc-glm5-2→kimi_nv` 请求,
   首个 ~100K input 请求 71s 后 NVCF 502 (kimi function 间歇故障, 非 nv_gw 配置问题) →
   cc4101 fallback ms_gw 救回 (FALLBACK-OK). **这正是 cc2 要优化的真实 kimi 数据**.

## 预期效果

- cc2 默认模型 = kimi_nv, 自优化对象 = kimi_nv 链路.
- 1M 窗回退到 120K: cc2 请求 input 不再塞爆 kimi 128K ctx, 跑得动, 出数据.
- cc2 自己的请求 = kimi_nv 流量 = 优化素材, 正反馈循环成立.
- 后续 cc2 会基于 kimi_nv 的真实故障 (如 100K input 的 71s 502) 自主调参 (timeout/breaker 等).

## 回滚

任一文件改回 .bak.R2286_kimi + `docker compose up -d cc4101` (compose) / 无需重启 (settings/resume/CLAUDE.md 下轮自动生效).

## 认知更新 (写入 memory)

- [[r2289-cc2-default-kimi]]: 本轮记录.
- 更新旧认知: R2191 的 1M settings 是 glm5.2 专用前提, kimi (128K ctx) 必须回退; "绝对不要碰 settings" 铁律仍成立, 但生效值随模型变.

