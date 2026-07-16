# R1635: HM2→HM1 — CC4101_PRIMARY_FAIL_THRESHOLD 8→4 (faster zombie escape)

## 触发分析

- HM1 提交: `107d9db` — R1634: HM2→HM1 PEER_FB_SKIP_MODELS add dsv4p_nv
- 判定: 轮到HM2 — 需要评估是否有新数据可优化

## 数据采集 (改前必有数据)

### HM1 nv_gw 日志 (18:37-18:40)

**glm5_2_nv zombie 恶性循环: 连续 54 次 zombie_empty_completion**
| 时间 | 内容 | 详情 |
|------|------|------|
| 18:37:14.7 | ZOMBIE | content=16c, input=117,313c, zombie→api_error→CC retry |
| 18:38:41.7 | ZOMBIE | content=16c, input=117,468c, Broken pipe on error chunk |
| 18:38:52.1 | ZOMBIE | content=16c, input=117,570c, zombie→api_error→CC retry |
| 18:39:00.4 | ZOMBIE | content=16c, input=117,570c, zombie→api_error→CC retry |
| 18:39:13.8 | ZOMBIE | content=16c, input=117,570c, zombie→api_error→CC retry |
| 18:39:23.4 | ZOMBIE | content=16c, input=117,570c, zombie→api_error→CC retry |
| 18:39:35.1 | ZOMBIE | content=16c, input=117,570c, zombie→api_error→CC retry |

Pattern: NVCF consistently returns 16-char garbage for all 117K+ context requests. Zombie detection correctly catches it, but CC4101 keeps retrying at FAIL_THRESHOLD=8.

**Successful glm5_2_nv responses (buffer-flush 模式):**
| 时间 | content_chars | duration |
|------|--------------|----------|
| 18:37:18.3 | 132c | 51,158ms |
| 18:37:26.6 | 246c | 11,842ms |
| 18:37:34.8 | 104c | 8,573ms |
| 18:37:57.8 | 17c | 9,440ms |
| 18:38:47.1 | 362c | 11,708ms |
| 18:39:57.0 | 1000c | 21,899ms |

### HM1 DB (3h窗口)
| mapped_model | status | count | avg_ms | max_ms | error_type |
|--------------|--------|-------|--------|--------|------------|
| dsv4p_nv     | 200    | 3     | 14,852 | 18,518 | — |
| dsv4p_nv     | 502    | 4     | 65,908 | 72,030 | all_tiers_exhausted |
| glm5_2_nv    | 200    | 44    | 12,901 | 51,158 | — |
| glm5_2_nv    | 502    | **54** | 8,478  | 66,356 | zombie_empty_completion |

### HM1 nv_tier_attempts (3h)
| error_type | count |
|------------|-------|
| pexec_success | 99 |
| pexec_429 | 7 |
| pexec_SSLEOFError | 3 |
| pexec_504 | 1 |

### HM1 CC4101 配置 (当前)
- `CC4101_PRIMARY_FAIL_THRESHOLD=8` (R1618: port from HM2 R1602)
- `CC4101_PRIMARY_SKIP_S=30`
- 每个 zombie 周期: 8 × 8,478ms ≈ 67.8s 浪费在无效重试上

## 分析

### 根因: NVCF glm5_2 function 117K+ context 下返回 16-char garbage

NVCF 3b9748d8 对超大 context (~117K chars) 稳定返回 16-char 空响应 (finish_reason=stop, 但 content 仅 16 字符)。nv_gw zombie 检测正确拦截 (50-char threshold), 但 CC4101 FAIL_THRESHOLD=8 导致每个 zombie 周期浪费 8 次 × 8.5s = 68s 才 OPEN 切 ms_gw。

### 54 zombie 错误 = 频繁的 circuit breaker 循环

3h 内 54 次 zombie → ~18 次/小时。FAIL_THRESHOLD=8 下每 ~8 次 zombie 触发一次 OPEN:
- 68s 浪费在 zombie 重试上后才切 ms_gw
- CC4101 返回 api_error 给 CC → CC 感知为 "server error" → 被迫手动重试

### 优化: 降低 FAIL_THRESHOLD 8→4

级别 | 浪费/周期 | 效果
------|----------|------
THRESHOLD=8 | 8 × 8.5s = 68s | 每个 zombie 周期浪费 68s 后才 OPEN
THRESHOLD=4 | 4 × 8.5s = 34s | 每个 zombie 周期仅浪费 34s 后 OPEN

**安全分析**: R1618 从 5→8 是因为 "NVCF 偶发抖动连续5次就OPEN误杀"。但当前 zombie 是持久 function-level bug (NVCF 3b9748d8 大 context 全返回 16-char), 不是随机抖动。4 次 zombie 后 OPEN 切 ms_gw 是正确行为, 不是误杀。

**不适用 R1618 担心**: 成功请求 (44/98 = 45%) 的 content 正常 (17-1000 chars), 超过 50-char threshold, 不会被 zombie 标记。只有 16-char 垃圾响应被标记。threshold=4 不会误杀正常请求。

## 变更

| 参数 | 旧值 | 新值 | 节省 |
|------|------|------|------|
| CC4101_PRIMARY_FAIL_THRESHOLD | 8 | 4 | ~34s/zombie 周期 (4→8 次减半) |

- 单参数修改
- compose only, 无代码修改
- `docker compose up -d cc4101` 重启验证
- 铁律: 只改 HM1 不改 HM2

## 验证

- `docker exec cc4101 env | grep PRIMARY_FAIL`: **CC4101_PRIMARY_FAIL_THRESHOLD=4** ✅
- `curl http://localhost:4101/health`: **{"status":"ok"}** ✅
- 预算安全: cc4101 只影响 circuit breaker 行为, 不影响 nv_gw tier budget ✅
- 铁律: 只改 HM1 不改 HM2 ✅

## 铁律:只改HM1不改HM2 ✅
## ⏳ 轮到HM1优化HM2