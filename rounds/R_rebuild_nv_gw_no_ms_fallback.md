# R-rebuild: nv_gw 链路重构 — 消除 ms_gw fallback, 纯 NVCF 5key 自恢复

**日期**: 2026-07-27
**主机**: HM2 (100.109.57.26)
**目标**: "仅凭 glm5.2_nv 就能稳住，不 fallback 到 ms，让系统能稳定运行"

## 背景

R-buf2key 已部署 buffer-then-flush + key2→key5 轮转，但 4-key 全挂后仍 fallback 到 ms_gw。
用户明确要求消除 ms_gw fallback，改为纯 NVCF 5key 自恢复机制。

数据分析结论：
- 429 是 per-function_id 级别，不是 per-account (dsv4p 和 glm5.2 独立 429)
- k2 的 429 streak 持续 20-50 分钟 (streak1=19min, streak2=30min, streak3=35min)
- 全挂后 3-4 分钟内某个 key 开始恢复
- 旧 KEY_COOLDOWN_S=60 远太短，k2 429 streak 期间反复撞 429

## 架构设计 (4 phases + feature flags)

### Phase 1: KeyManager (key_manager.py, 新建)
- 替代旧 cooldown.py 的简单 per-key cooldown
- 429: 长冷却 120s→600s 指数退避 (base=120, max=600)
- 连接异常: 短冷却 30s→60s (连续3次→120s 长冷却)
- 成功: 重置该 key 的 conn-fail 计数
- 全局单例，线程安全 (threading.Lock)
- 向后兼容: cooldown.py 重导出所有旧 API (is_key_cooling, mark_key_cooling, reset_key429_count)

### Phase 2: upstream.py 连接异常记录
- 在 `_glm52_single_attempt` 的 3 个异常处理器中加 `_km_mark_conn()` 调用:
  - `socket.timeout` → mark_conn_error(tier_model, key_idx, "timeout")
  - `RemoteDisconnected/ConnectionRefusedError` → mark_conn_error(tier_model, key_idx, type(e).__name__)
  - SSL 异常 → mark_conn_error(tier_model, key_idx, error_class)
- `_km_mark_conn` 是安全包装 (try/except pass)，不影响原有逻辑

### Phase 3: ProbeWorker (probe_worker.py, 新建)
- 后台守护线程，每 15s 探测 cooling 中的 key
- 通过该 key 专属的 mihomo 代理发最小 "hi" 请求
- 恢复 → mark_success + set Event (唤醒 WaitQueue)
- 在 app.py 中 `start_probe_worker()` 启动

### Phase 4: WaitQueue (buffer_stream.py 修改)
- 4-key 全挂后不再立即 fallback ms_gw
- 新流程:
  1. `NVU_WAIT_QUEUE_ENABLED=1`: clear recovery event, `wait_for_recovery(timeout=120)`
  2. 恢复 → 重置, 用恢复的 key 重试 `_execute_and_drain`
  3. 成功 → flush to CC, return True
  4. 失败或超时 → 检查 `NVU_DISABLE_MS_FALLBACK`
  5. ms disabled → 发 error event to CC (502)
  6. ms enabled → 旧 `_try_ms_gw_fallback()` 行为

### Feature Flags (env)
| Env | 默认 | 说明 |
|---|---|---|
| `NVU_KEYMGR_ENABLED` | 1 | KeyManager (429/conn 分离 cooldown) |
| `NVU_PROBE_ENABLED` | 1 | ProbeWorker 后台探测 |
| `NVU_WAIT_QUEUE_ENABLED` | 1 | WaitQueue (event-driven 等恢复) |
| `NVU_WAIT_QUEUE_MAX_WAIT` | 120 | 最长等待秒数 |
| `NVU_DISABLE_MS_FALLBACK` | 1 | 禁用 ms_gw fallback |
| `NVU_KEYMGR_429_BASE_COOLDOWN` | 120 | 429 基础冷却 |
| `NVU_KEYMGR_429_MAX_COOLDOWN` | 600 | 429 最大冷却 |
| `NVU_KEYMGR_CONN_BASE_COOLDOWN` | 30 | 连接异常基础冷却 |
| `NVU_KEYMGR_CONN_MAX_COOLDOWN` | 60 | 连接异常最大冷却 |
| `NVU_KEYMGR_CONN_FAIL_THRESHOLD` | 3 | 连续连接异常阈值 |
| `NVU_KEYMGR_CONN_LONG_COOLDOWN` | 120 | 连续异常后长冷却 |
| `NVU_PROBE_INTERVAL` | 15 | 探测间隔 |
| `NVU_PROBE_TIMEOUT` | 10 | 探测超时 |

## docker-compose.yml 变更

```yaml
# KeyManager env (Phase 1)
NVU_KEYMGR_ENABLED: "1"
NVU_KEYMGR_429_BASE_COOLDOWN: "120"
NVU_KEYMGR_429_MAX_COOLDOWN: "600"
NVU_KEYMGR_CONN_BASE_COOLDOWN: "30"
NVU_KEYMGR_CONN_MAX_COOLDOWN: "60"
NVU_KEYMGR_CONN_FAIL_THRESHOLD: "3"
NVU_KEYMGR_CONN_LONG_COOLDOWN: "120"
# ProbeWorker (Phase 3)
NVU_PROBE_ENABLED: "1"
NVU_PROBE_INTERVAL: "15"
NVU_PROBE_TIMEOUT: "10"
# WaitQueue (Phase 4)
NVU_WAIT_QUEUE_ENABLED: "1"
NVU_WAIT_QUEUE_MAX_WAIT: "120"
NVU_DISABLE_MS_FALLBACK: "1"
# CC4101 timeout 650→800
CC4101_STREAM_TOTAL_DEADLINE_S: "800"
```

## cc2_resume.sh 变更

```bash
API_TIMEOUT_MS=850000         # was 700000
CLAUDE_STREAM_IDLE_TIMEOUT_MS=850000  # was 700000
```

## 部署文件

| 文件 | 位置 | 类型 |
|---|---|---|
| key_manager.py | gateway/ | 新建 |
| probe_worker.py | gateway/ | 新建 |
| cooldown.py | gateway/ | 替换 (re-export from key_manager) |
| upstream.py | gateway/ | 修改 (+_km_mark_conn) |
| buffer_stream.py | gateway/ | 修改 (WaitQueue 替代 ms fallback) |
| app.py | gateway/ | 修改 (+start_probe_worker) |
| docker-compose.yml | /opt/cc-infra/ | 修改 (+env vars) |
| cc2_resume.sh | ~/cc_ps/cc2_repair_self/.claude/ | 修改 (timeout) |

备份: 所有原文件已备份为 `*.py.bak.R-rebuild` / `*.bak.R-rebuild` on HM2。

## 验证结果

1. **py_compile 全通过**: key_manager.py, probe_worker.py, cooldown.py, upstream.py, buffer_stream.py, app.py
2. **nv_gw restart 成功**: health=ok, StartedAt 更新
3. **E2E 测试**: 通过 cc4101 发送请求 → 200 OK, 返回 ZhipuAI/GLM-5.2
4. **KeyManager 活跃**: 日志 `[NV-KEYMGR] 429 tier=kimi_nv k4 count=1 cooldown=120s`
5. **ProbeWorker 运行**: 后台线程已启动
6. **Buffer 层正常**: `[NV-BUFFER-SUCCESS] flushed 2187b/21601b after 1 attempt(s)`

## 预期效果

- ms_gw fallback 率: 33.3% → 0% (NVU_DISABLE_MS_FALLBACK=1)
- 4-key 全挂后: 不再立即 fallback，而是等 NVCF 恢复 (≤120s)
- k2 429 streak 期间: 不再反复撞 429 (指数退避 120s→600s)
- 整体 SR: 目标 ≥ 97.5% (需持续监控)

## 待验证

- [ ] 生产环境 4-key 全挂时 WaitQueue + ProbeWorker 端到端工作
- [ ] 30-min 窗口 SR ≥ 97.5%, ms fallback = 0
- [ ] 6h 窗口稳定性

## 回滚方案

```bash
# 1. 恢复 .bak 文件
ssh -p 222 opc2_uname@100.109.57.26
cd /opt/cc-infra/proxy/nv-gw/gateway/
for f in key_manager.py probe_worker.py cooldown.py upstream.py buffer_stream.py app.py; do
  cp ${f}.bak.R-rebuild ${f}
done
cd /opt/cc-infra && cp docker-compose.yml.bak.R-rebuild docker-compose.yml
docker compose up -d nv_gw

# 2. 或快速回滚: 关 flag
# 在 compose 中设 NVU_DISABLE_MS_FALLBACK=0 即恢复 ms fallback
# NVU_KEYMGR_ENABLED=0 / NVU_PROBE_ENABLED=0 / NVU_WAIT_QUEUE_ENABLED=0
``

## 关联

- R-buf2key: buffer-then-flush + key2→key5 轮转 (前置工作)
- R-buffer: cc2 zombie 流 buffer-then-flush 根治
- R-cc-s3: per-agent 固定 key 绑定 + 阶梯超时重试
- R2082: dsv4p 5 独立美国 socks5 (dsv4p 作备选 fallback 的数据基础)
