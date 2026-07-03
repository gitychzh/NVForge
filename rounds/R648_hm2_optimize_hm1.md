# R648: HM2 → HM1 — PEER_FALLBACK_TIMEOUT 12→10 (-2s)

**轮次**: R648  
**角色**: HM2 (opc2_uname) 优化 HM1 (opc_uname, 100.109.153.83)  
**日期**: 2026-07-03 19:35 UTC  
**上轮提交**: R647 (HM1→HM2, 73cac29) — PEER_FALLBACK_TIMEOUT 14→12

---

## 1. 数据采集 (HM1, SSH 100.109.153.83:222)

### 容器状态
- `nv_40006_uni`: Up, healthy (StartedAt: 2026-07-03T11:30:14Z, R647 deploy)
- 配置确认: `NVU_PEER_FALLBACK_TIMEOUT=12`, `NV_INTEGRATE_KEY_COOLDOWN_S=0`, `MIN_OUTBOUND_INTERVAL_S=0`, `UPSTREAM_TIMEOUT=34`

### 日志摘要
```
[19:33:23.1] [NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request stream=True → extended timeout 61s
[19:33:25.9] [NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request stream=True → extended timeout 61s
```
— 均为正常的 thinking timeout 扩展（NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61），非错误。无 ERROR/WARN。

### DB 1h 全景 (R647 regime)
```
total | ok  | fail | total_kc429 | avg_dur_ms | avg_ttfb
------+-----+------+-------------+------------+----------
  126 | 126 |    0 |           5 |    37585.5 |   8495.7
```
— **126/126 OK, 0 fail, total_kc429=5** (成功请求中的正常 key rotation)

### upstream 分布 1h
```
upstream_type | total | ok  | avg_ms
---------------+-------+-----+---------
 nvcf_pexec    |    63 |  63 |  6493.7
 nv_integrate  |    63 |  63 | 68677.4
```
— **双路径均 100% 成功，零错误**

### 最近 10 条请求
全部 `glm5_2_nv / nvcf_pexec / status=200 / key_cycle_429s=0`，延迟 2.4–6.4s，干净无问题。

---

## 2. 优化分析

### 当前参数状态
| 参数 | 当前值 | floor | 状态 |
|------|--------|-------|------|
| `NV_INTEGRATE_KEY_COOLDOWN_S` | 0 | 0 | **已触底** |
| `MIN_OUTBOUND_INTERVAL_S` | 0 | 0 | **已触底** |
| `UPSTREAM_TIMEOUT` | 34 | — | 余量充足，不急 |
| `NVU_PEER_FALLBACK_TIMEOUT` | 12 | — | **可继续压** |

### 决策: PEER_FALLBACK_TIMEOUT 12 → 10 (-2s)
- R647 regime (12s) 下: **126/126 OK, 0 fail, 双路径零错误** — 确认零错误 regime 稳定
- `peexec avg 6.5s` — 10s 仍覆盖 pexec 平均耗时 (6.5s × 1.5 = 9.75s < 10s)
- peer fallback 历史 100% timeout（成功路径不受 pexec 超时影响），压缩仅减少 failure-path 等待
- 继续 R645→R646→R647 chain 的 −2s 每轮节奏

---

## 3. 执行操作 (仅改 HM1，不改 HM2)

### Step 1: 备份
```bash
cp /opt/cc-infra/docker-compose.yml /opt/cc-infra/docker-compose.yml.bak.R648
```

### Step 2: 修改 compose (line 436, python3 - stdin)
```yaml
# Before:
      NVU_PEER_FALLBACK_TIMEOUT: "12"  # R646

# After:
      NVU_PEER_FALLBACK_TIMEOUT: "10"  # R648: HM2→HM1 — PEER_FALLBACK_TIMEOUT 12→10 (-2s)...
```

### Step 3: 重启
```bash
docker compose up -d nv_40006_uni
# → Container Recreated → Started
```

### Step 4: 验证
| 检查项 | 结果 |
|--------|------|
| docker ps | `Up About a minute (healthy)` ✅ |
| env | `NVU_PEER_FALLBACK_TIMEOUT=10` ✅ |
| docker logs | `(no error/warn found)` ✅ |
| StartedAt | `2026-07-03T11:55:16Z` ✅ |

---

## 4. 评判
- ✅ 零错误 regime: 126/126 OK, 0 fail (1h)
- ✅ 单参数每轮: PEER_FALLBACK_TIMEOUT 12→10 (-2s)
- ✅ 只改 HM1 docker-compose.yml, HM2 零修改
- ✅ 数据驱动: R647 regime 验证充分 (126 req / 0 fail)
- ✅ 稳定优先: 10s 仍覆盖 pexec avg 6.5s，安全余量 50%+

---

## ⏳ 轮到HM1优化HM2