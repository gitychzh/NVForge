# R-hm4104-fix: hermes adapter 三 bug 修复 (HM2)

## 摘要

hm4104 (hermes adapter) 存在三个 bug 导致 hermes cron job 报 "⚠️ primary 和 fallback 均不可用, 请稍后重试.":
1. `FALLBACK_ENABLED=1` + `FALLBACK_URL=none` 配置矛盾 — primary 失败后空跑 fallback 连接 `none` URL
2. `CC4101_TOTAL_BUDGET_S=80` < `PRIMARY_HEADER_TIMEOUT=180` — primary-retry-after-fallback 条件永远不成立 (死代码)
3. forwarder.py 不发 `X-Caller` header — nv_gw 记录 caller=unknown, `CALLER_KEY_MAP=hermes:2` 固定 key 绑定不生效

## 数据 (改前 2h 窗口, 2026-07-31 13:30~15:00)

### hm4104 adapter.jsonl
- 总请求: 112
- PRIMARY-FAIL-STREAM: 7 次 (5×429, 2×502)
- FALLBACK-FAIL-STREAM: 7 次 (全部 ConnectionRefusedError: connect to none failed)
- PRIMARY-RETRY: 0 次 (重试逻辑死代码, 从未触发)
- SR: ~93.75%

### nv_gw DB (caller=unknown, 即 hermes)
| status | error_type | cnt |
|--------|------------|-----|
| 200 | | 101 |
| 429 | all_tiers_exhausted | 5 |
| 502 | all_tiers_exhausted | 2 |

### 典型故障序列
```
PRIMARY-FAIL-STREAM  nv_gw 流式 server_5xx status=429 after 16927ms, 切 fallback: upstream 429
UPSTREAM-ERR         connect to none failed: ConnectionRefusedError: [Errno 111] Connection refused
FALLBACK-FAIL-STREAM ms_gw 流式 conn status=0 after 16931ms: ConnectionRefusedError: [Errno 111] Connection refused
(无 PRIMARY-RETRY 日志 — retry 条件 remaining=80-elapsed >= 180 永不成立)
```

## 修复

### Fix 1: FALLBACK_ENABLED=0 (docker-compose.yml)
```
- FALLBACK_ENABLED=0  # R_hm4104_fix: 1→0, FALLBACK_URL=none 时 fallback 是空跑, 关掉走 clean error 路径
```
- 效果: primary 失败后不再空跑连接 `none`, 直接返回 "primary 不可用且 fallback 已禁用" 干净错误
- 影响范围: hm4104 (只此一个容器, env 独立)

### Fix 2: CC4101_TOTAL_BUDGET_S=360 (docker-compose.yml)
```
- CC4101_TOTAL_BUDGET_S=360  # R_hm4104_fix: 80→360, 让 primary-retry-after-fallback 条件 remaining>=PRIMARY_HEADER_TIMEOUT(180) 能成立
```
- 效果: 如果未来重启用 fallback (FALLBACK_ENABLED=1 + 真实 FALLBACK_URL), retry-primary 条件 `360-elapsed >= 180` 可以成立
- 当前状态: 因 Fix 1 关了 fallback, 此参数暂时不被读到, 但作为 future-proof 保留

### Fix 3: X-Caller header (forwarder.py + config.py + docker-compose.yml)

**config.py** 新增:
```python
X_CALLER = os.environ.get("X_CALLER", "")
```

**forwarder.py** 两处改动:
1. import 块加 `X_CALLER`
2. `_post_upstream()` headers dict 后加:
```python
if X_CALLER:
    headers["X-Caller"] = X_CALLER
```

**docker-compose.yml** 三个容器加 env:
| Container | X_CALLER | nv_gw CALLER_KEY_MAP 绑定 |
|-----------|----------|--------------------------|
| hm4104 | hermes | key index 2 (k3) |
| opclaw4103 | openclaw | key index 3 (k4) |
| oc4105 | opencode | key index 4 (k5) |

- 效果: nv_gw `_detect_caller()` 优先读 X-Caller header, 现在 caller=hermes 正确识别
- 兼容性: X_CALLER 默认空字符串, 不设不发 header, 不影响现有行为

## 验证

### E2E test (hm4104 → nv_gw → NVCF)
```bash
curl -s -X POST http://127.0.0.1:4104/v1/chat/completions \
  -H "Authorization: Bearer hm-gw-token" \
  -H "Content-Type: application/json" \
  -d '{"model":"dsv4p_nv","messages":[{"role":"user","content":"hi"}],"stream":false,"max_tokens":10}'
# → 200, model=deepseek-ai/deepseek-v4-pro
```

### DB 验证 (caller 从 unknown → hermes)
```sql
SELECT caller, status FROM nv_requests WHERE created_at > NOW() - INTERVAL '2 minutes' ORDER BY created_at DESC LIMIT 5;
-- hermes | 200  ← 之前是 unknown
```

### Config 验证
```python
FALLBACK_ENABLED: False       # was True
CC4101_TOTAL_BUDGET_S: 360.0  # was 80.0
X_CALLER: 'hermes'            # was not set
```

## 参数表

| 参数 | 旧值 | 新值 | 位置 |
|------|------|------|------|
| FALLBACK_ENABLED | 1 | 0 | docker-compose.yml hm4104 |
| CC4101_TOTAL_BUDGET_S | (default 80) | 360 | docker-compose.yml hm4104 |
| X_CALLER | (not set) | hermes | docker-compose.yml hm4104 |
| X_CALLER | (not set) | openclaw | docker-compose.yml opclaw4103 |
| X_CALLER | (not set) | opencode | docker-compose.yml oc4105 |

## 修改文件
- `/opt/cc-infra/docker-compose.yml` — hm4104/opclaw4103/oc4105 env 加 X_CALLER + hm4104 FALLBACK_ENABLED + CC4101_TOTAL_BUDGET_S
- `/opt/cc-infra/proxy/cc-adapter/gateway/config.py` — 新增 X_CALLER 配置项
- `/opt/cc-infra/proxy/cc-adapter/gateway/forwarder.py` — import + _post_upstream headers 加 X-Caller

## 预期效果
1. hermes primary 失败时不再空跑 ConnectionRefusedError, 返回干净的 503 错误
2. nv_gw 正确识别 caller=hermes → 走 CALLER_KEY_MAP 绑定 key3 (不同 egress IP, 避免与其他 agent 共用 key 被 429 连坐)
3. opclaw4103/oc4105 同理识别 caller=openclaw/opencode → 各自绑定独立 key
