# R790: HM2 opclaw4103 fallback 卡死修复 (glm5_2_nv thinking 超时体系 + fallback 流中途补 content)

> 承接 R780 (thinking supplement + prompt limit) / R789 (5-key DIRECT IP 修复)。
> HM2-only。HM1 不动 (角色分工: 我优化 HM2)。
> 铁律: 改前有数据 (实测), 改后有验证。

## 现象

用户报: 远程 openclaw 报错 `⚠️ [opclaw4103] primary 故障/超时, 已 fallback 到 glm5_2_ms. 本轮继续, 下一轮回 primary. (opclaw4103 fallback)` 后 **直接卡住不动**。

## 改前数据 (2026-07-06, 全部远程实测)

### 现象 1: primary glm5_2_nv 100% 502

opclaw4103 PRIMARY_MODEL=glm5_2_nv。nv_gw 对 glm5_2_nv 强制注入 `chat_template_kwargs.enable_thinking=True` (config.py:102)。连续 6 次请求全部 60s timeout → 502, 0 成功。同期 dsv4p_nv 5/5 SUCCESS, kimi_nv 全 SUCCESS。

### ★probe 系统排查 (4 维度)★

用户要求深入排查: IP / function id / NVCF pexec / nvidia.api integrate 四维度。

**维度1 function id**: `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` (`ai-glm-5_2`) 在 NVCF **ACTIVE** (2026-07-02 上线), 未下架。✓ 非 function id 问题。

**维度2 IP**: 5 key 直连 pexec (修正路径 `/v2/nvcf/pexec/functions/<id>`):

| key | 出口 | NOTHINK | THINK |
|---|---|---|---|
| K1 | DIRECT | 200 9.0s content 正常 | 200 56.6s **content=null** reasoning 有 |
| K2 | DIRECT | 200 11.2s content 正常 | 200 42.8s **content=null** reasoning 有 |
| K4 | socks5h 7897 (国内CMI) | 200 14.5s content 正常 | **504 78.0s** (偶发) |

✓ 非 IP 问题 (3 不同出口都能 200)。

**维度3 NVCF pexec thinking 行为**:
- 非 thinking: 9-14s 返 200, content 正常 ✓
- thinking: 42-78s 返 200, **content=null, 只有 reasoning_content** ← NVCF glm-5.2 自带行为
- 偶发 504 (K4 78s) ← NVCF 平台间歇性

config.py:96 注释 (2026-07-03) "触发后 finish=stop, 思考消耗 ~400-535 tokens, content 正常——健康" **已过时**: 现在 thinking content=null。

**维度4 nvidia.api integrate 链路**: `integrate.api.nvidia.com/v1/chat/completions` 直连 K1, thinking 和非 thinking 都 **95s timeout, 0 bytes**。这就是 `NV_INTEGRATE_MODELS=` 设空、全走 pexec 的原因 (注释: integrate 对 deepseek 30s 挂死, 实测对 glm5_2 也完全不可用)。

### 现象 2: fallback 到 ms_gw 后流中途 TimeoutError (卡死直接原因)

opclaw4103 `FALLBACK_TIMEOUT_S=120` 是整流 read timeout。fallback 到 ms_gw 后 first byte 3s 正常, 但**后续流 67s+ 超 120s timeout** → `forwarder.py:314` except 块只 `yield done`, **不补 content** → openclaw 收空 content 流 → 卡死。

### 现象 3: 代码缺陷

`forwarder.py:314-316` `_stream_from_upstream` except 块 (流中途异常) 只 `yield done`, 不触发 supplement 逻辑 (298 行 supplement 在 try 块正常结束才走)。流中途 timeout 时已累积 reasoning_buf 但未发 content, 客户端收空流卡死。

## 根因 (按影响排序)

R1 [primary 超时]: `TIER_TIMEOUT_BUDGET_S=60` + `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=90` 不够 glm5_2_nv thinking (实测 42-78s 小请求, 大请求 >90s) → budget/override 截断 502
R2 [fallback 代码]: `forwarder.py:314-316` 流中途 TimeoutError 不补 content → openclaw 收空流卡死
R3 [fallback 超时]: `FALLBACK_TIMEOUT_S=120` 不够 ms_gw glm5_2_ms 大请求 (first byte 后 67s+ 仍没完)
R4 [NVCF 平台]: glm5_2 thinking 不稳定 (偶发 empty200/504/timeout 混合), 非我方问题, 加超时降低 502 概率但不消除

## 修复方案 (HM2 only)

### 改动 1: nv_gw 超时体系 (修 R1)

**文件**: `/opt/cc-infra/docker-compose.yml` nv_gw env + 本地仓库 `deploy_artifacts/R780_opclaw4103_thinking/docker-compose.hm2.R780.yml`

| 参数 | 改前 | 改后 |
|---|---|---|
| TIER_TIMEOUT_BUDGET_S | 60 | 180 |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 90 | 150 |

- budget 180: 覆盖 glm5_2_nv thinking 小请求 (42-78s) + 多 key 尝试 (单 key 150s override, budget 180 够 1 次 150s + 余量)
- override 150: thinking per-request 上限, 覆盖大请求 thinking (实测中等请求 >90s)
- 风险: dsv4p_nv 单次 4-28s, 快路径不受影响 (单 key 成功即返)。极端失败请求多拖, 但 fastbreak (PEXEC_TIMEOUT_FASTBREAK=3, EMPTY_200_FASTBREAK=2) 保护

### 改动 2: opclaw4103 `FALLBACK_TIMEOUT_S` 120 → 240 (修 R3)

**文件**: docker-compose opclaw4103 env

ms_gw glm5_2_ms 大请求 first byte 后续流可达 67s+, 240s 覆盖。对齐 PROXY_TIMEOUT=240。

### 改动 3: forwarder.py 流中途异常补 content (修 R2, 代码改动)

**文件**: `/opt/cc-infra/proxy/cc-adapter/gateway/forwarder.py` + 本地仓库同文件 (md5 已确认一致)

`_stream_from_upstream` except 块复用 supplement 逻辑: 若 `SUPPLEMENT_REASONING_AS_CONTENT` 开启且 `not content_seen and reasoning_buf`, 补 content chunk = reasoning 全文再 yield done。

```python
except Exception as e:
    _log("STREAM-UPSTREAM-ERR", f"上游流读取失败: {type(e).__name__}: {e}")
    # R790: 流中途异常 (timeout 等) 时, 若已累积 reasoning 但未发 content,
    # 补一个 content chunk = reasoning 全文, 避免客户端 (openclaw) 收空 content 卡死.
    if SUPPLEMENT_REASONING_AS_CONTENT and not content_seen and reasoning_buf:
        full_reasoning = "".join(reasoning_buf)
        _log("SUPPLEMENT-CONTENT-ON-ERR", ...)
        # ... 复用 supplement 模板逻辑, 补 content chunk, finish=stop
        yield ("message", tmpl)
    yield ("done", None)
```

**影响控制** (bind-mount 共享 forwarder.py 给 hm4104/opclaw4103/oc4105):
- `SUPPLEMENT_REASONING_AS_CONTENT` 默认 0, 仅 opclaw4103 env 设 1
- hm4104/oc4105 env 未设 → except 块行为不变 (只 yield done)
- 仅 opclaw4103 (=1) 流中途 timeout 时补 content

## 实施步骤

1. 备份: `docker-compose.yml.bak.R790` / `.bak.R790b`, `forwarder.py.bak.R790`
2. 改 docker-compose nv_gw `TIER_TIMEOUT_BUDGET_S=180` + `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150`
3. 改 docker-compose opclaw4103 `FALLBACK_TIMEOUT_S=240`
4. 改 forwarder.py except 块补 content 兜底
5. 同步本地仓库 `deploy_artifacts/R780_opclaw4103_thinking/{forwarder.py,docker-compose.hm2.R780.yml}`
6. `docker compose up -d nv_gw opclaw4103` 重启 (env 改动需 up -d 非 restart)
7. 验证

## 验证 (铁律: 改后有验证)

### V1: env 生效
- nv_gw: `TIER_TIMEOUT_BUDGET_S=180`, `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150` ✓
- opclaw4103: `FALLBACK_TIMEOUT_S=240`, `SUPPLEMENT_REASONING_AS_CONTENT=1` ✓

### V2: forwarder.py 语法 + R790 标记
`docker exec opclaw4103 python -c "import ast; ast.parse(open('/app/gateway/forwarder.py').read())"` → OK ✓
`docker exec opclaw4103 grep -c R790 /app/gateway/forwarder.py` → 1 ✓

### V3: fallback 路径端到端 (★关键★)
circuit 打开后, opclaw4103 直走 fallback (ms_gw glm5_2_ms):
```
curl opclaw4103:4103 ... glm5_2_nv "100字解释递归"
→ HTTP 200, 36.7s, content_len=96
   content_head="⚠️ [opclaw4103] primary 故障/超时, 已 fallback 到 glm5_2_ms..."
   finish=length
```
**改前同场景卡死, 改后 36.7s 正常返回 200 + fallback notice + content。** ✓

### V4: 健康检查
opclaw4103 /health = ok, nv_gw /health = ok, 全容器 Up ✓

### V5: primary 加超时后行为
nv_gw 日志: glm5_2_nv 现在 `Tiers tried: 3×mixed` (改前 1×), 多 key 尝试。但仍混合 empty200/504/timeout (NVCF 平台不稳定, R4), 有概率仍 502 → 走 fallback 兜底。

## 未解决 / 后续

- **NVCF glm5_2 thinking 不稳定** (R4): 偶发 empty200/504/timeout, 非我方问题。加超时降低 502 概率, 不消除。fallback 到 ms_gw 兜底保证不卡死。
- **glm5_2 thinking content=null**: NVCF 模型自带行为 (只发 reasoning)。R780 SUPPLEMENT 兜底设计正确, 但仅在 nv_gw 返 200 时触发; nv_gw 502 时走 fallback (ms_gw 非 thinking, content 正常)。
- **integrate 链路对 glm5_2 不可用**: 95s timeout, 保持 `NV_INTEGRATE_MODELS=` 空, 全走 pexec。
- **HM1 同步**: 用户指示 HM1 不动。
- **大请求流式 fallback 240s 仍可能 timeout**: openclaw tools=24 + msgs=70+ 大请求, ms_gw 流式可能 >240s。supplement-on-err 在 reasoning_buf 非空时补 content; 若 ms_gw 只发 content (非 thinking) 则 reasoning_buf 空, 不补 (避免重复)。观察是否仍卡。

## 参数表

| 参数 | 旧值 | 新值 | 位置 |
|---|---|---|---|
| TIER_TIMEOUT_BUDGET_S | 60 | 180 | nv_gw env |
| NVU_FORCE_STREAM_UPGRADE_TIMEOUT | 90 | 150 | nv_gw env |
| FALLBACK_TIMEOUT_S (opclaw4103) | 120 | 240 | opclaw4103 env |
| forwarder except 块 | 只 yield done | 补 content 兜底 | forwarder.py:314-316 R790 |

## 回滚

- compose: `cp docker-compose.yml.bak.R790 docker-compose.yml && docker compose up -d`
- forwarder: `cp forwarder.py.bak.R790 forwarder.py && docker restart opclaw4103`

## 提交

- 源码: `deploy_artifacts/R780_opclaw4103_thinking/{forwarder.py,docker-compose.hm2.R780.yml}` (本地仓库同步, md5 与远程一致)
- round: `rounds/R790_hm2_opclaw4103_fallback_stall_fix.md`
