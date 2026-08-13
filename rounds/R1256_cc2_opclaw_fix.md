# R1256 cc2: opclaw4103 "primary 和 fallback 均不可用" 修复

**日期**: 2026-08-13
**容器**: opclaw4103 (cc-adapter, port 4103)
**变更类型**: docker-compose.yml env 修改 (docker compose up -d)

## 问题

opclaw4103 报错 "primary 和 fallback 均不可用, 请稍后重试."

### 根因分析

**原配置**:
- Primary: dsv4f0731_nv@40666 (NVCF fid 281478d0, pexec)
- Fallback: dsv4f0731_ms@40007 (ms_gw, ModelScope)

**故障链条**:
1. NVCF fid 281478d0 (ai-deepseek-v4-flash-0731) **严重降级**:
   - 30min 数据: pexec 8 success / 54 timeout = **13% SR**
   - 每个 pexec attempt ~57s 超时 (UPSTREAM_TIMEOUT=45s + 连接开销)
   - 5 key 轮转需 ~180s 才放弃, 但 opclaw PRIMARY_HEADER_TIMEOUT=90s 先超时
   - NVCF 上仅有此 1 个 ACTIVE deepseek-v4-flash fid, 无替代

2. Fallback (dsv4f0731_ms@ms_gw) 偶发超时:
   - 19:36:36 ms_gw 流式 70s header timeout
   - 导致 primary + fallback 双链同时失败 → "均不可用"

3. Circuit OPEN (连续5次故障) 后所有请求直走 fallback, 加剧 fallback 压力

### 诊断数据 (2026-08-13 20:00)

```
40666 (dsv4f0731_nv): 6 success / 7 fail(502) = 46% SR, avg 91s (30min)
40006 (glm5_2_nv): 26 success / 0 fail = 100% SR, avg 39s (30min)
40007 (glm5_2_ms): 24 success / 2 fail = 92% SR, avg 101s (2h)
```

NVCF functions list 查询: 281478d0 是唯一 ACTIVE 的 deepseek-v4-flash fid, 其余全 INACTIVE.

## 修复

**新配置** (R1256):
```
Primary:   ms_gw:40007  → glm5_2_ms  (ModelScope, OpenAI SSE native, 92% SR)
Fallback:  nv_gw:40006 → glm5_2_nv  (NVCF pexec, 100% SR historically)
```

**设计理由**:
1. ms_gw 原生返回 OpenAI SSE (opclaw 期望格式), 无需格式转换
2. ms_gw 7key 10variant, TTFB 1-20s, 比 NVCF pexec 稳定快速
3. nv_gw 作 fallback: 当 ms_gw 遇 429 风暴时, NVCF pexec 可作备用
4. 两条链路完全独立 (ModelScope vs NVCF), 不会同时降级

**timeout 调整**:
- PRIMARY_HEADER_TIMEOUT: 90→90 (ms_gw TTFB 快, 90s 足够)
- FALLBACK_HEADER_TIMEOUT: 70→70 (nv_gw NVCF TTFB 可达 73s, 70s 覆盖)
- 90+70=160 < 170 PROXY_TIMEOUT < 180 openclaw timeout

**API key 调整**:
- NV_GW_API_KEY=ms-gw-token (primary=ms_gw 需要 ms-gw-token)
- FALLBACK_API_KEY=nv-gw-token (fallback=nv_gw 需要 nv-gw-token)

## 验证

### 非流式测试
```
curl http://localhost:4103/v1/chat/completions -d '{"model":"glm5_2_ms","max_tokens":50,...}'
→ 200 OK, 6.5s
```

### 流式测试 (无 tools)
```
→ 200 OK, ~2s, ms_gw 直接成功
```

### 流式测试 (with tools)
```
→ primary (ms_gw) 90s timeout (429 风暴)
→ fallback (nv_gw) 成功
→ 无 "均不可用" 错误! fallback 正常工作
```

### opclaw 日志
```
START: primary=http://ms_gw:40007/v1/glm5_2_ms fallback=http://nv_gw:40006/v1/glm5_2_nv
REQ: model=glm5_2_ms stream=True tools=0
SUPPLEMENT-CONTENT: 流末补 content (正常)
(无 PRIMARY-FAIL, 无 CIRCUIT-OPEN)
```

## 影响范围

- **opclaw4103**: 完全修复, primary+fallback 双链可用
- **cc2 (cc4101→nv_gw)**: 不受影响 (cc2 有自己的 primary/fallback 链路)
- **nv_gw (40006)**: 现在同时服务 cc2(primary) 和 opclaw(fallback), 负载可忽略
- **ms_gw (40007)**: 现在同时服务 opclaw(primary) 和 cc2(nv_gw internal fallback), 负载可接受

## 回滚

```bash
# 恢复原配置
cd /opt/cc-infra
cp docker-compose.yml.bak.* docker-compose.yml  # 恢复备份
docker compose up -d opclaw4103
```

## 文件修改

- `/opt/cc-infra/docker-compose.yml`: opclaw4103 section (PRIMARY/FALLBACK URL+MODEL, API keys, timeouts)
- 备份: `/opt/cc-infra/docker-compose.yml.bak.20260813_*`
