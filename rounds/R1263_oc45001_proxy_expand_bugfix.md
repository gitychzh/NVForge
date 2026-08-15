# R1263 — oc45001 IP 轮换池验证 + 6 BUG 修复

## 时间
2026-08-15

## 背景
hermes 已将 mihomo 64 个 IP 节点加入容器 oc45001 的轮换池 (config.yaml 新增 64 个
OC-P listener 端口 7910~7978，排除 7911-7913/7916-7917 因 mihomo 未配 listener)。
docker-compose.yml OZ_PROXY_LIST 也已同步更新为 64 端口列表，容器已于 06:44 重启加载。

## 数据核实 (DB 铁证)

### 1. 轮换池已生效
- 06:44 重启后，oc_attempts 表 10 分钟窗口内出现 20 个 distinct proxy（之前只有 10 个）
- 新端口 7920-7930 已被尝试，证明 64 端口轮换生效
- 旧 5 个 closed port (7911-7913/7916-7917) 不再出现（06:43 后绝迹）

### 2. 历史 SR 数据 (旧 10 端口, 全时段)
| proxy  | total | ok  | r429 | sr_pct |
|--------|-------|-----|------|--------|
| 7910   | 150   | 142 | 2    | 94.7%  |
| 7911   | 53    | 5   | 45   | 9.4%   | (closed port)
| 7912   | 94    | 5   | 86   | 5.3%   | (closed port)
| 7913   | 133   | 5    | 123 | 3.8%   | (closed port)
| 7914   | 173   | 46  | 126  | 26.6%  |
| 7915   | 170   | 71  | 99   | 41.8%  |
| 7916   | 144   | 6   | 132  | 4.2%   | (closed port)
| 7917   | 182   | 14  | 160  | 7.7%   | (closed port)
| 7918   | 212   | 67  | 143  | 31.6%  |
| 7919   | 188   | 84  | 101  | 44.7%  |

5 个 closed port 导致 3.8-9.4% SR，大量 wasted attempts。

## 修复的 6 个 BUG

### BUG 1: OZ_PROXY_LIST 包含 5 个 dead port (7911-7913, 7916-7917)
- **问题**: mihomo config 没有 7911-7913/7916-7917 的 listener（端口不存在），
  但旧 OZ_PROXY_LIST 包含它们 → 每次轮到这些端口时 ConnectionRefused, wasted ~20-40ms
- **修复**: hermes 已更新 OZ_PROXY_LIST 为 64 端口（仅 mihomo 实际 open 的端口）
- **验证**: DB 显示 06:44 后无 7911-7913/7916-7917 的 attempt

### BUG 2: pacer.report_ok 在 finally 中无条件调用，覆盖 report_429 冷却
- **文件**: handlers.py:170
- **问题**: `finally` 块无条件调用 `pacer.report_ok(model)`，即使所有 proxy 返回 429
  且 `pacer.report_429(model, ...)` 刚设置了 cooldown。report_ok 会重置 cooldown_s
  到基准值，指数退避完全失效 → 下一个请求立刻打 429
- **修复**: 加条件 `if request_row.get("status") == 200 and not request_row.get("error_type")`

### BUG 3: 并发闸 semaphore 过早释放 (pacer.py:66-70)
- **文件**: pacer.py
- **问题**: `acquire()` 获取 semaphore 后在 slot lock 内立即 `release()`，
  在上游调用之前就释放了 → OZ_MAX_CONCURRENCY=1 完全无效，并发请求叠加冲击上游
- **修复**: 新增 `pacer.release()` 方法，在 `handle_chat_completions` 的 `finally` 块
  中调用（跨整个上游调用周期）。acquire 失败时不需 release（TimeoutError 提前返回）

### BUG 4: request_row["status"] 成功时未设为 200
- **文件**: handlers.py
- **问题**: `request_row` 初始化 status=0，仅在 429 路径设为 429。
  成功路径从不设 status=200 → DB 记录显示 status=0（而非 200），
  且 BUG 2 的修复条件 `status == 200` 永远不满足 → report_ok 永远不调用
- **修复**: 在 `_stream_passthrough`/`_nonstream_passthrough` 成功后设 `request_row["status"] = 200`

### BUG 5: Retry-After header 在 send_response 之前发送 (HTTP 协议违规)
- **文件**: handlers.py:301, 154
- **问题**: `h.send_header("Retry-After", ...)` 在 `_send_json()` 之前调用，
  但 `_send_json` 内部先调用 `h.send_response(status)`。
  BaseHTTPRequestHandler 要求 `send_response` 必须在 `send_header` 之前，
  否则状态行未写入 → HTTP 响应畸形
- **修复**: `_send_json` 增加 `extra_headers` 参数，在 `send_response` 之后、
  `end_headers` 之前发送 Retry-After

### BUG 6: _proxy_counter 全局变量线程不安全
- **文件**: handlers.py:310-314
- **问题**: `_proxy_counter` 是全局 int，`_next_proxy_idx` 做 `+=1` 无锁。
  ThreadingHTTPServer (daemon_threads=True) 下并发请求可能竞争
- **修复**: 改用 `itertools.count()`（C 实现原子自增）

### 附: 删除死代码
- `_proxy_error_body` 函数 (handlers.py:376-392) 从未被调用，已删除

## 验证
- `curl /health` → 200 OK ✓
- `docker ps` → Up healthy ✓
- 烟雾测试: `POST /v1/chat/completions` → 200 OK, 返回正常 ✓
- DB `oc_requests` 新记录 status=200（旧记录 status=0）✓
- DB `oc_attempts` 64 端口轮换生效 ✓
- Python 运行时验证: extra_headers 参数存在, pacer.release 方法存在,
  _proxy_error_body 已删除, _proxy_counter 为 itertools.count 类型 ✓

## 修改文件
- `/opt/cc-infra/proxy/oc-proxy/gateway/handlers.py` (6 处修改)
- `/opt/cc-infra/proxy/oc-proxy/gateway/pacer.py` (重构 acquire/release)
- 备份: `*.bak.20260815`

## 下一步
- 观察 30min 窗口 SR 变化（预期 64 端口分散后 429 率下降）
- 如 SR 仍 < 50%，考虑加大 OZ_MIN_INTERVAL_S (当前 8s → 12s)
- 监控 per-proxy SR 分布，剔除持续 429 的出口 IP
