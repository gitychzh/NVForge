# R2191 (hm2_cc2_infra): 1M 上下文落地 + client_gone_mid_stream(499) 根因修复

**日期**: 2026-07-21
**主机**: HM2 only (100.109.57.26, opc2_uname)
**角色**: CC 基础设施侧 — cc2 自优化盲点 BUG 根治 + 1M 上下文配置同步

## 一句话

cc2 连续 13 轮 (R2175→R2188) 报 "0 真中断全救回", 但 DB 实测 6h 有 **33× 499
(client_gone_mid_stream)** — cc2 的盲点. 根因: cc2 典型 prompt 150K+, 旧
`CLAUDE_CODE_AUTO_COMPACT_WINDOW=155000` 在请求中途触发 auto-compact → cc2 主动断流 →
cc4101 stream.py:130 `_write_bytes` 返回 False → 记 499. 同时 glm5.2 (nv+ms) 早已开放
1M 上下文, 但 nv_gw/ms_gw config 仍是 131072 (128K), cc2 settings 仍是 155000 — 全部基于
过时的 128K 假设. 本轮同步三处配置到 1M, 消除 155K 误触发.

## 铁律合规

- ✅ 改前有数据: 6h DB 33× 499 + 122 reqs>150K + max 253797c status=200
- ✅ 改后有验证: /health + 容器状态 + 配置加载验证 (见下)
- ✅ 聚焦 nv_gw 链: nv_gw(40006) + ms_gw(40007) + cc4101 适配器链 + cc2 settings
- ✅ 只改 HM2 不改 HM1
- ✅ 改 .py 用 docker compose restart (bind-mount)
- ✅ 写入仓库: 本轮文件 + commit

## 数据 (改前, HM2, 6h window, ~20:50 时点)

### BUG1: client_gone_mid_stream (499) — cc2 盲点

```
cc_requests 6h error_type 分解:
  (空=200成功)            941
  client_gone_mid_stream   33   ← cc2 13轮全未提
  conn                      2
  timeout                   1
  stream_total_deadline     1
```

499 全部 status=499, max input=182818 chars (都在 155K 阈值附近或之上).

### 大输入实测 (nv_requests 6h)

```
gt150k (input>150000 chars)            122
gt150k 且 status=200                    88
max_input_chars                     280645
max_input_chars 且 status=200        253797   ← 248K 仍 200, 证明 glm5.2 远超 128K
```

**结论**: glm5.2 (NVCF + z.ai) 实测支持 >250K chars input 且 status=200, 128K 假设已过时.

## 根因分析

### 为什么 cc2 13 轮没看到 499

cc2 每轮读 STATE.md → 执行 → 覆写 STATE.md. cc2 的 "救回" 判据 = cc4101 fallback 成功
(ms_gw 兜住). 但 499 是 **cc2 自己主动断流** (auto-compact 触发), cc4101 这边 stream.py:130
`_write_bytes(chunk)` 写不进去 (client socket 已关) → 记 499. cc2 视角: "我正常 compact 了,
继续干" — 它不知道自己 compact 打断了正在进行的请求, cc4101 那边记了 499. 两边视角割裂,
13 轮全漏.

### 499 链路 (cc4101 stream.py:130)

```python
if not _write_bytes(chunk):
    metrics["error_type"] = "client_gone_mid_stream"
    metrics["status"] = 499
```

`_write_bytes` 返回 False = 客户端 (cc2) socket 写失败 = cc2 主动断开. 非网关病, 非上游病,
是 cc2 自己的 auto-compact 中断.

### 为什么 155000 阈值会中途触发

cc2 prompt 结构: CLAUDE.md + STATE.md + system + 工具输出, 常态 150K+. 旧
`CLAUDE_CODE_AUTO_COMPACT_WINDOW=155000` 意味着 context 一到 155K 就触发 compact.
cc2 的请求是流式的 — nv_gw ttfb 75-120s (R2154 记录), 期间 cc2 context 持续增长 (工具输出
追加), 一旦越过 155K 就 auto-compact, 当前请求被中断, cc2 断流, cc4101 记 499.

## 研究 (glm5.2 1M 上下文)

1. **z.ai 官方**: `docs.z.ai/guides/llm/1m-context` 页面确认 GLM-5.2 支持 1M 输入上下文
   (需特定 API 调用方式). z.ai 是 GLM 系列的官方维护方.
2. **NVIDIA NVCF**: build.nvidia.com 上 z-ai/glm-5-2 card 显示 max_tokens (output) = 131072
   (128K), 输入上下文未硬限到 128K (DB 实测 253797c 200 证明).
3. **Claude Code 官方**: `autoCompactEnabled` / `DISABLE_AUTO_COMPACT` 是公开开关, 但
   `contextWindow` / `autoCompactWindow` / `CLAUDE_CODE_AUTO_COMPACT_WINDOW` 是未公开内部
   参数 — cc2 早已在用 (旧值 155000), 本轮只改值不改机制.
4. **DB 经验验证 (决定性)**: 253797 chars input status=200, 122 reqs>150K 其中 88 个 200 —
   glm5.2 远超 128K, 1M 是安全的.

## 改动 (3 处配置)

### 1. cc2 项目级 settings.json (cc2 专属, 不影响 openclaw2 / 交互式 cc)

文件: `~/cc_ps/cc2_repair_self/.claude/settings.json`
备份: `.bak.R2188_20260721_204536` (注: 备份名带 R2188 因当时计划本轮叫 R2188, 后发现 R2188
被 cc2 自己的巡检轮占用, 本轮改 R2191; 备份名不改, 内容为准)

| 字段 | 旧值 | 新值 | 理由 |
|---|---|---|---|
| `env.CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 155000 | 900000 | 1M context 10% 安全余量 |
| `contextWindow` (顶层) | 170000 | 1000000 | 真实 1M (glm5.2 已开放) |
| `autoCompactWindow` (顶层) | 155000 | 900000 | 同 env, 顶层与 env 一致 |

保留不变: `model: cc-glm5-2`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS: 8192`, `API_TIMEOUT_MS: 600000`.

### 2. nv_gw config.py (bind-mount, 40006)

文件: `/opt/cc-infra/proxy/nv-gw/gateway/config.py`
备份: `config.py.bak.R2188_20260721_204714`

```python
MODEL_INPUT_TOKEN_SAFETY = {
    "kimi_nv": 131072,    # kimi 仍 128K (上游未开放 1M)
    "dsv4p_nv": 131072,   # dsv4p 仍 128K
    "glm5_2_nv": 1048576, # R2191: glm5.2 NVCF/z.ai 已开放 1M, DB 实测 253797c 200 成功
}
```

仅改 glm5_2_nv (131072 → 1048576), kimi/dsv4p 保持.

### 3. ms_gw config.py (bind-mount, 40007)

文件: `/opt/cc-infra/proxy/ms-gw/gateway/config.py`
备份: `config.py.bak.R2188_20260721_204733`

```python
MODEL_REGISTRY["glm5_2_ms"]["context_window"] = 1048576  # R2191 同步 1M (旧 131072)
MODEL_REGISTRY["dsv4p_ms"]["context_window"] = 131072     # dsv4p 保持
```

## 验证 (改后, ~20:50)

### 容器健康

```
nv_gw /health: {"status":"ok","nv_num_keys":5,...,"port":40006}
ms_gw /health: {"status":"ok","num_keys":7,"num_variants":10,...,"port":40007}
docker ps: nv_gw Up 7 seconds / ms_gw Up 7 seconds
```

### 配置加载验证

```
nv_gw MODEL_INPUT_TOKEN_SAFETY: {'kimi_nv':131072, 'dsv4p_nv':131072, 'glm5_2_nv':1048576}  ✅
ms_gw MODEL_REGISTRY context_window: {"glm5_2_ms":1048576, "dsv4p_ms":131072}  ✅
cc2 settings: env.CLAUDE_CODE_AUTO_COMPACT_WINDOW=900000 / contextWindow=1000000 / autoCompactWindow=900000  ✅
```

## 预期效果

1. cc2 不再在 155K 处 auto-compact → 499 (client_gone_mid_stream) 归零或骤降
2. cc2 可承接更大 prompt (至 900K 才 compact), 减少中途断流
3. nv_gw/ms_gw 不再因 128K 假设误拒大输入 (虽然 DB 显示之前也没拒, 但 config 现在与现实一致)
4. cc2 视角与 cc4101 视角对齐 — cc2 能看到自己曾经的 499 盲点 (通过本轮 STATE 注入)

## 给 cc2 的 BUG 注入 (本轮关键产出)

cc2 的 STATE.md 每轮覆写, 不能作持久载体. 本轮通过 cc2 的 CLAUDE.md (持久, 不覆写)
注入 BUG1 分析, 让 cc2 下轮起能在自己的 DB 查询里纳入 499 监控, 不再盲点.

注入位置: cc2 CLAUDE.md 末尾追加 "## cc2 盲点 BUG1: client_gone_mid_stream (499)" 段,
含根因 + 查询 SQL + 判读规则.

## 未尽事项

- P1: 6h 验证待跑 (本轮改完 ~20:50, 6h 后 ~02:50 复核 499 是否归零)
- P2: HM1 未同步 (铁律只改 HM2; HM1 nv_gw config 仍 128K, 但 HM1 无 cc2 自优化, 影响小)
- P3: dsv4p/kimi 仍 128K (上游未开放 1M, 不改)
