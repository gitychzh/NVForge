# R-rebuild: nv_gw 整体链路重构 — 去除 ms_gw 依赖

> 与本机 ChatGPT 讨论后制定。核心目标：**仅靠 NVCF glm5.2_nv 5 key 稳住，不 fallback 到 ms_gw**。

## 背景数据（3h 实况）

| 指标 | 数值 |
|---|---|
| 总 buffer 拦截 | 122 |
| k2 首key即成功 | 53 (43.4%) |
| k2 失败 k5 救回 | 43 (35.2%) |
| 2-key 失败 k3 救回 | 4 (3.3%) |
| 3-key 失败 k4 救回 | 2 (1.6%) |
| 4-key 全挂 → ms 兜底 | 3 (2.5%) |
| NVCF 自成功率（含轮转） | 97.5% |

### k2 429 streak 数据

- streak1: 13:31-13:50 (19min, 7次429) → 8min 后恢复
- streak2: 14:24-14:54 (30min, 12次429) → 2min 后恢复
- streak3: 15:21-15:56 (35min, 11次429) → 18min 后恢复

**关键发现**：429 是 per-function_id 的，持续 20-50 分钟。全挂后 3-4 分钟 NVCF 端点恢复（某个 key 成功），但 k2 的 429 可能仍持续。

### 3 次全挂详情

| 请求 | k2 | k5 | k3 | k4 | 总耗时 | ms 救回 |
|---|---|---|---|---|---|---|
| 9dde4341 | 429 (4s) | RemoteDisc (45s) | SSLEOF (5s) | RemoteDisc (41s) | 95s | 36s |
| d48a3357 | RemoteDisc (61s) | RemoteDisc (40s) | fault (66s) | RemoteDisc (36s) | 204s | 75s |
| eb5d4165 | 429 (69s) | RemoteDisc (51s) | fault (77s) | timeout (42s) | 240s | 136s |

## 问题分析

当前架构的核心缺陷：

1. **k2 被 429 后仍然每次都从 k2 开始** — 429 streak 持续 20-50 min，这段时间 k2 每次必败，浪费 4-70s
2. **4-key 全挂后无路可走** — 只能 fallback ms_gw，用户不想要
3. **k2 的 429 cooldown 太短** — `KEY_COOLDOWN_S=60`，指数退避 cap 30s，但实际 429 streak 持续 20-50 min，60s 后重试仍 429
4. **没有异步探测** — 不知道哪个 key 已恢复，每次请求盲目尝试

## 重构方案

### 架构设计

```
cc4101 → nv_gw handlers.py (intercept) → BufferStreamSession
                                                │
                                    ┌───────────┴───────────┐
                                    │ KeyManager (全局)      │
                                    │ - per-key 健康状态     │
                                    │ - 429 breaker (长冷却) │
                                    │ - conn-error tracker   │
                                    └───────────┬───────────┘
                                                │
                                    选 healthy key → _try_glm52_mode_chain
                                                │
                                        ┌───────┴───────┐
                                        │ 成功 → flush   │
                                        │ 失败 → 换 key  │
                                        └───────┬───────┘
                                                │
                                    4-key 全挂? → ProbeWorker 等待
                                                │
                                    后台探测任意 key 恢复 → 唤醒请求
                                                │
                                        成功 → flush
                                        超时(deadline) → 502
```

### 组件设计

#### 1. KeyManager（新文件 `key_manager.py`）

全局 per-key 健康状态管理器，替代当前 cooldown.py 的简单 per-key 冷却。

```python
# key_manager.py 核心逻辑

class KeyState:
    HEALTHY = "healthy"
    COOLING_429 = "cooling_429"      # 429 限流，长冷却
    COOLING_CONN = "cooling_conn"    # 连接异常，短冷却
    AUTH_FAILED = "auth_failed"      # 401/403，跨 tier

class KeyManager:
    """全局 5-key 健康状态管理。进程内单例，线程安全。"""

    # 429 冷却：递增式，首次 120s，每次翻倍，cap 600s（10min）
    # 对应 k2 streak 20-50min 的实际情���
    429_BASE_COOLDOWN = 120
    429_MAX_COOLDOWN = 600

    # 连接异常冷却：短，30s（NVCF 端点间歇故障恢复快）
    CONN_BASE_COOLDOWN = 30
    CONN_MAX_COOLDOWN = 60

    # 连续 conn-error 计数：3 次连续 conn-error → 长冷却 120s
    CONN_FAIL_THRESHOLD = 3

    def get_healthy_keys(self) -> list[int]:
        """返回当前可用的 key 列表，按优先级排序。"""

    def mark_429(self, key_idx):
        """记录 429，递��冷却。"""

    def mark_conn_error(self, key_idx, error_type):
        """记录连接异常。连续 3 次 → 长冷却。"""

    def mark_success(self, key_idx):
        """成功 → 重置该 key 所有计数。"""

    def is_available(self, key_idx) -> bool:
        """key 是否当前可用。"""
```

**与现有 cooldown.py 的关系**：KeyManager 替代 cooldown.py 的 `mark_key_cooling`/`is_key_cooling`，但保留 `mark_key_auth_failed`/`is_key_auth_failed`（401/403 跨 tier 逻辑不变）。旧函数转为调用 KeyManager 的代理。

#### 2. ProbeWorker（新文件 `probe_worker.py`）

后台线程，持续探测处于 cooling 状态的 key，恢复后立即标记 healthy。

```python
class ProbeWorker:
    """后台异步探测 NVCF key 恢复状态。

    每 15s 对所有 cooling key 发轻量 probe（HEAD 或最小 chat 请求）。
    probe 成功 → mark healthy + 通知 WaitQueue。
    """

    PROBE_INTERVAL = 15  # 每 15s 探测一轮
    PROBE_TIMEOUT = 10   # 单 key probe 超时

    def start(self):
        """启动后台线程。"""

    def probe_key(self, key_idx) -> bool:
        """对 key 发轻量探测请求。"""

    def _run(self):
        """主循环：每 15s 扫描 cooling keys，逐个 probe。"""
```

**probe 请求**：用最小 input（`"hi"`），非 stream，走该 key 绑定的 mihomo 代理端口。NVCF 正常返回 200 = 恢复。429 = 仍在冷却。conn error = 仍然间歇故障。

#### 3. WaitQueue（在 buffer_stream.py 中）

4-key 全挂后，不立即走 ms_gw，而是进入等待队列。

```python
class BufferStreamSession:
    def run(self):
        # ... 现有 4-key 轮转逻辑不变 ...

        # 全挂后：
        if all_failed:
            # 新增：等 NVCF 恢复，不走 ms
            _recovered = self._wait_for_recovery()
            if _recovered:
                # 用恢复的 key 重试一次
                verdict, reason = self._execute_and_drain(...)
                if success:
                    return True
            # 恢复后仍失败，或等待超时 → 502
            self._send_error_to_cc()
            return False

    def _wait_for_recovery(self, max_wait=120):
        """等待 ProbeWorker 发现任意 key 恢复。

        事件驱动（threading.Event），不是固定 sleep。
        超时 max_wait 秒后放弃。
        """
```

**等待机制**：`threading.Event`，由 ProbeWorker set。请求不是 sleep 2 分钟，而是阻塞等待，一旦有 key 恢复就立即唤醒。

#### 4. 动态 key 调度（改 `_execute_and_drain`）

当前：固定轮转表 `_KEY_ROTATION = [k2, k5, k3, k4]`。

改为：从 KeyManager 获取 healthy key 列表，动态排序。

```python
def _execute_and_drain(self, timeout_s, is_first=False):
    # 新：从 KeyManager 获取可用 key 列表
    healthy_keys = _key_manager.get_healthy_keys()
    if not healthy_keys:
        return None, "no_healthy_keys"

    _use_key_idx = healthy_keys[0]  # 取最优 key
    _use_caller = _key_idx_to_caller(_use_key_idx)
    # ... 后续调 _try_glm52_mode_chain 不变 ...
```

## 代码改动点

### 新文件

| 文件 | 行数（估） | 说明 |
|---|---|---|
| `gateway/key_manager.py` | ~150 | KeyManager + KeyState |
| `gateway/probe_worker.py` | ~100 | 后台探测线程 |

### 修改文件

| 文件 | 改动 |
|---|---|
| `gateway/buffer_stream.py` | `_execute_and_drain` 改用 KeyManager 选 key；`run()` 全挂后改走 `_wait_for_recovery()`；移除 `_try_ms_gw_fallback` 调用（保留代码但默认不触发） |
| `gateway/upstream.py` | `_glm52_single_attempt` 内 429/conn-error 改调 KeyManager.mark_429/mark_conn_error；成功调 KeyManager.mark_success |
| `gateway/cooldown.py` | `mark_key_cooling`/`is_key_cooling` 转为 KeyManager 代理（向后兼容） |
| `gateway/config.py` | 新增 KeyManager/ProbeWorker/WaitQueue 相关 env |
| `gateway/handlers.py` | 启动时初始化 ProbeWorker |
| `/opt/cc-infra/docker-compose.yml` | 新增 env 配置 |

## 参数配置

### 新增 env

```yaml
# KeyManager
NVU_KEYMGR_429_BASE_COOLDOWN=120     # 429 首次冷却 120s（streak 20-50min, 旧 60s 太短）
NVU_KEYMGR_429_MAX_COOLDOWN=600      # 429 最大冷却 600s（10min）
NVU_KEYMGR_CONN_BASE_COOLDOWN=30      # 连接异常首次冷却 30s
NVU_KEYMGR_CONN_MAX_COOLDOWN=60      # 连接异常最大冷却 60s
NVU_KEYMGR_CONN_FAIL_THRESHOLD=3     # 连续 3 次 conn-error → 长冷却

# ProbeWorker
NVU_PROBE_INTERVAL=15                # 探测间隔 15s
NVU_PROBE_TIMEOUT=10                 # 单 key 探测超时 10s
NVU_PROBE_ENABLED=1                  # 开关

# WaitQueue
NVU_WAIT_QUEUE_ENABLED=1             # 全挂后等 NVCF 恢复（替代 ms fallback）
NVU_WAIT_QUEUE_MAX_WAIT=120          # 最多等 120s
NVU_WAIT_QUEUE_POLL_INTERVAL=2       # Event 超时检查间隔

# Feature Flags
NVU_DISABLE_MS_FALLBACK=1            # 关闭 ms_gw fallback（最终目标）
```

### 调整现有 env

```yaml
# 不变
NVU_BUFFER_MAX_RETRIES=4
NVU_BUFFER_TIMEOUT_STAIRS=150,150,150,150
NVU_BUFFER_TOTAL_DEADLINE_S=600

# 调整：cc4101 deadline 需适配 wait queue
CC4101_STREAM_TOTAL_DEADLINE_S=750   # 600s buffer + 120s wait queue
```

### cc2 SDK 超时

```bash
API_TIMEOUT_MS=800000                # 750s + 50s margin
CLAUDE_STREAM_IDLE_TIMEOUT_MS=800000
```

## 分阶段实施

### Phase 1: KeyManager（统计模式）

- 新增 `key_manager.py`，KeyManager 作为 cooldown.py 的底层实现
- `mark_key_cooling` 转调 `KeyManager.mark_429`
- `is_key_cooling` 转调 `KeyManager.is_available`
- **不改**任何调用方逻辑，只是替换底层实现
- 验证：日志确认 KeyManager 正确记录状态，SR 不变

### Phase 2: 动态 key 调度

- `_execute_and_drain` 从固定轮转表改为从 KeyManager 选 healthy key
- k2 在 429 cooling 期间被自动跳过，不浪费 4-70s
- 验证：k2 429 streak 期间请求不再从 k2 开始，直接走 k5/k3/k4

### Phase 3: ProbeWorker

- 新增后台探测线程
- cooling key 每 15s probe 一次
- 恢复 → 立即标记 healthy
- 验证：429 streak 期间 probe 发现 k2 恢复的时间点 vs 自然请求发现

### Phase 4: WaitQueue（替代 ms fallback）

- 4-key 全挂后进入 WaitQueue 等待
- ProbeWorker 发现任意 key 恢复 → 唤醒请求
- 最多等 120s，超时 → 502
- **关闭** ms_gw fallback（`NVU_DISABLE_MS_FALLBACK=1`）
- 验证：全挂率 2.5% → 其中多少被 WaitQueue 救回，多少最终 502

### Phase 5: 调优

- 根据实际运行数据调整 cooldown 参数
- 如果 120s 等待不够，可调到 180s（需同步调 cc4101 deadline）
- 如果 probe 太频繁，调大 interval
- 最终目标：SR ≥ 98%（当前 97.5%），ms fallback = 0

## 验证方法

### 每个 Phase 验证

```bash
# 1. KeyManager 状态日志
docker logs nv_gw 2>&1 | grep "NV-KEYMGR"

# 2. 动态调度效果
docker logs nv_gw 2>&1 | grep "NV-BUFFER-KEYSWAP" | grep -oP "k\d" | sort | uniq -c
# 预期：k2 429 期间 KEYSWAP 到 k5 的比例上升

# 3. ProbeWorker 效果
docker logs nv_gw 2>&1 | grep "NV-PROBE"

# 4. WaitQueue 效果
docker logs nv_gw 2>&1 | grep "NV-WAITQUEUE"
# 预期：全挂后等待 → 恢复 → 成功

# 5. 整体 SR
docker exec logs_db psql -U litellm -d hermes_logs -c "
SELECT count(*), count(*) FILTER (WHERE error_type IS NULL) AS ok,
       ROUND(100.0 * count(*) FILTER (WHERE error_type IS NULL) / count(*), 1) AS sr
FROM nv_requests WHERE created_at >= NOW() - INTERVAL '1 hour'
  AND request_model = 'glm5_2_nv';"

# 6. ms fallback 次数
docker logs nv_gw 2>&1 | grep -c "NV-BUFFER-MS-FB"
# 预期：Phase 4 后 = 0
```

## 回滚方案

全部通过 Feature Flag 控制：

| 开关 | 作用 | 回滚方式 |
|---|---|---|
| `NVU_KEYMGR_ENABLED` | KeyManager 状态管理 | 关闭 → 回固定轮转 |
| `NVU_PROBE_ENABLED` | 后台探测线程 | 关闭 → 停止探测 |
| `NVU_WAIT_QUEUE_ENABLED` | 全挂后等待恢复 | 关闭 → 恢复 ms fallback |
| `NVU_DISABLE_MS_FALLBACK` | 关闭 ms_gw | 关闭 → 恢复 ms fallback |

上线顺序：KeyManager → 动态调度 → ProbeWorker → WaitQueue → 关闭 ms

每阶段可独立回滚。最坏情况：关闭所有 flag，回到当前 4-key 轮转 + ms fallback。
