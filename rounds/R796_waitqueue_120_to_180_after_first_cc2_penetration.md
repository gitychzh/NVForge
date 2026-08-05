# R796: NVU_WAIT_QUEUE_MAX_WAIT 120→180 — 应对 R735-R795 连续 58 轮后首次 cc2 穿透

## 摘要

R795 注入数据 (09:04 CST) 暴露 cc2 出现 1 次 502 buffer_exhausted (336413ms), 这是
R735-R795 连续 **58 轮 SR 100%** 之后的**首次穿透到 cc4101-primary 的失败**。根因查
到: 08:57 CST 一个请求 (req=9ffbc98a) 遇上 NVCF pexec 端点 7 分钟集中 RemoteDisconnected
风暴, 5 个 buffer attempt 每个只试 1 key 就判 all_keys_exhausted, 全败后进 WaitQueue
等 120s — WaitQueue 120s 超时后 2~30s 内 NVCF 实际恢复 (那段窗口的 01:02 UTC 起出现 7 个
pexec_success)。**擦边超时**: 120s wait 与 NVCF 恢复时点擦边, 超时退出后 2 秒就恢复。

改 `NVU_WAIT_QUEUE_MAX_WAIT=120 → 180` 给集中瞬断风暴多 60s 余量, 数学上:
- 5 attempt + backoff 实测 elapsed = 216s (08:57:05 → 09:00:41)
- 加 wait 180s = 396s < 470s cc4101 STREAM_TOTAL_DEADLINE, 仍有 74s 余量
- 396s < 600s cc2 SDK 超时, < 900s idle

仅改 nv_gw 单 env, 用 `up -d` 应用 (env 改必须 up -d 不能 restart)。

## 改动详情

### 文件 / 改动

- `/opt/cc-infra/docker-compose.yml` line 124 (nv_gw 服务 environment block):
  - `NVU_WAIT_QUEUE_MAX_WAIT=120` → `180`
  - 备份: `/opt/cc-infra/docker-compose.yml.bak.R796`
- 其他 nv_gw_stable / dsv4p_nv40066 的 WAIT_QUEUE 参数**未动**

### 应用方式

```bash
cd /opt/cc-infra
cp docker-compose.yml docker-compose.yml.bak.R796
# 编辑 line 124 → 180
docker compose up -d nv_gw   # env 改必须 up -d, 不能 restart
```

## 根因分析 (502 buffer_exhausted req=9ffbc98a, 08:57-09:02 CST)

### 时序重建 (从 nv_gw 日志 9ffbc98a)

| 时刻 | 事件 | attempt | key | 结果 | elapsed |
|---|---|---|---|---|---|
| 08:57:05 | BUFFER-START 5 attempts, total=450s | - | - | 入 buffer | 0s |
| 08:57:05 | ATTEMPT 1/5 start_key=k5 | 1 | k5 | RemoteDisc (36s) | 36s |
| 08:57:41 | EXEC-FAIL attempt 1, all_keys_exhausted=True | 1 | k5 | backoff 5s | 36s |
| 08:57:46 | ATTEMPT 2/5 start_key=k1 | 2 | k1 | RemoteDisc (36s) | 77s |
| 08:58:22 | EXEC-FAIL attempt 2, backoff 10s | 2 | k1 | - | 77s |
| 08:58:32 | ATTEMPT 3/5 start_key=k2 | 3 | k2 | RemoteDisc (30s) | 118s |
| 08:59:03 | EXEC-FAIL attempt 3, backoff 15s | 3 | k2 | - | 118s |
| 08:59:18 | ATTEMPT 4/5 start_key=k3 | 4 | k3 | RemoteDisc (33s) | 165s |
| 08:59:50 | EXEC-FAIL attempt 4, backoff 15s | 4 | k3 | - | 165s |
| 09:00:05 | ATTEMPT 5/5 start_key=k4 | 5 | k4 | RemoteDisc (36s) | 216s |
| 09:00:41 | BUFFER-LAST-FAIL → BUFFER-WAIT up to 120s | - | - | wait | 216s |
| 09:02:41 | WAIT 超时 → NO-MS → 502 buffer_exhausted | - | - | fail | 336s |
| (09:02:13 实际 NVCF 已恢复, 01:02 UTC 起 k0/k1 pexec_success 持续) | | | | | |

### 关键发现

1. **集中瞬断风暴而非单 key 429 风暴**: 00:55-01:02 UTC 这 7 分钟窗口内 NVCF pexec
   端点对所有 5 key 全部秒断, 5 个 mihomo 美国端口都同样表现. 实测 tier_attempts 这 7
   分钟内 NVCFPexecRemoteDisconnected×4 (k1/k2/k3/k4) 全 pexec_us_rr, integrate 完全
   没试 (MODE_CHAIN 只配单 mode pexec_us_rr).

2. **buffer 设计: 每个 attempt 只试 1 key** (upstream.py line 2213-2217): 当 buffer
   传入 `nv_start_key_override`, `_chain_max_attempts=1` 立刻返回 all_keys_exhausted.
   这是设计意图 ("buffer 层换 key5 重试")。优势是单 key 429 风暴下整齐轮转避开限
   流, 劣势是真集中连接故障时每 key 隔 backoff 5/10/15s 才重试 → 5 attempt 全走 216s.

3. **WaitQueue 120s 边缘超时**: 实际 NVCF 在 01:02 UTC 左右恢复, WaitQueue 在 09:00:41
   起等 120s 到 09:02:41 超时退出, 即 09:02:13 探测出恢复 → 但 wait 阻塞同步且 120s
   也已进入最后 25s 内 → probe 15s 周期下一次在 09:02:43 > 09:02:41 wait 超时退出点.
   如果 wait=180s, 探测会在 09:02:13 拿到 event, 第 6 attempt 立即可成功, 总
   elapsed ~188s 而非 336s。

4. **NVU_DISABLE_MS_FALLBACK=1**, glm5_2_nv 全败不会向 ms_gw fallback (cc4101 层 fallback
   到 dsv4p_nv40066 才是设计正路, 但 cc4101 看到的是 nv_gw 立即 502 而 buffer_exhausted
   caller-side 还没到 cc4101 fallback 触发条件 — 实测 fallback_occurred=false).

### 为何只改 wait 不改 attempt 数

- 加 attempt (5→7) 需要 +180s buffer 总预算, 已接近 cc4101 的 470s 上限, 风险大
- 改 buffer chain 内联 5 key 重试会改动核心调度, 风险大且违背 R-buf2key 设计意图
- 仅加 wait 是单 env 小步改, 只在 5key 全挂的 trailing edge 给 60s 余量, 不影响 99%
  正常流量路径

## 验证 (post-change, 09:10 CST 5min 窗口)

- env 已加载: `docker exec nv_gw env | grep NVU_WAIT_QUEUE_MAX_WAIT` → 180 ✓
- nv_gw /health ok, nv_num_keys=5 ✓
- cc4101, dsv4p_nv40066, logs_db 全 Up ✓
- 实时 cc4101-primary 5min 22/22 = 100% 200 ✓ (改后零回归)
- 日志显示正常 dispatch: req=cef362b1 attempt 1 k3 pexec fid1 11s 的 success_textool_call

## 判稳结论

- R795 链路分析暴露的 cc2 502 是 R735-R795 58 轮后的首次穿透, 根因清晰 (集中瞬断风暴
  + WaitQueue 120s 擦边超时 + NVU_DISABLE_MS_FALLBACK=1 全链断), 改 wait_queue 120→180
  给集中瞬断末尾的恢复多 60s 余量.
- 改动只在 5key 全挂尾部触发链路, 不影响正常 99% 流量 (attempt=1 success 3-18s 无 wait)
- 改后 5min 22/22 全 100%, 链路健康.
- 等 30min 后置轮 (R797) 抽样验证集中瞬断场景下是否仍有穿透. 实际集中瞬断风暴罕见
  (R735-R795 58 轮发生 1 次), 短期内难复现触发场景, 后置验证主要看未引入回归.

## 下一步

- R797: 后置验证 wait=180 是否引入回归 (正常窗口不应触发 wait, 应 0% 影响)
- 若 R-r-dsv4f0731_nv 并行线工作在 nv_gw 上注册 dsv4f_nv 的 DEFAULT_NV_MODEL 兜底
  未影响 glm5_2_nv tier 排序, 不主动切换
- 监测下个集中瞬断窗口: 若仍穿透 → 考虑加 attempt 6/7 + 调整 buffer total deadline
  让两层万分匹配
- 注意此改动是单点 wait 加长, 不解决"全 5key + 同 mode 同时挂"的根本设计, 根因还在
  NVCF 端点周期性 jitter。长期改进选项 (备用 mode 在 chain 内 inline 5key × 2 mode)
  暂不动 (风险大).

## 参数快照 (R796 实测)

- nv_gw: NVU_DISABLE_MS_FALLBACK=1, UPSTREAM_TIMEOUT=90, TIER_TIMEOUT_BUDGET_S=180,
  TIER_COOLDOWN_S=180, KEY_COOLDOWN_S=30
- nv_gw: NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4
- nv_gw: NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_BUFFER_MAX_RETRIES=5,
  NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90, NVU_BUFFER_TOTAL_DEADLINE_S=450
- nv_gw: **NVU_WAIT_QUEUE_ENABLED=1, NVU_WAIT_QUEUE_MAX_WAIT=180 (R796 改)**,
  NVU_PROBE_INTERVAL=15
- nv_gw: NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0 (全用 fid1=b1b22d03)
- nv_gw: NV_GLM52_KEY_MODE_BIND= (空, 用 mode_idx 指针, NV_GLM52_MODE_CHAIN=pexec_us_rr)
- nv_gw: NVU_KEYMGR_429_BASE=120, MAX=600; NVU_KEYMGR_CONN_BASE=30, MAX=60, FAIL_THRESHOLD=3, LONG=120
- nv_gw: StartedAt 2026-08-05 09:10 CST (= R796 up -d 后重建)
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=ms_gw:40007(env), STREAM_TOTAL=470, HEADER=400
- 链路: cc2→cc4101(4101)→nv_gw(40006, glm5_2_nv)→NVCF
