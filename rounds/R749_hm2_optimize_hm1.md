# R749: HM2 → HM1 — NVU_FORCE_STREAM_UPGRADE_TIMEOUT 50→64 (+14s)

## TL;DR
HM1 的 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=50` 严重落后于 `UPSTREAM_TIMEOUT=64`（R742已设64），漂移14s。
glm5_2 思考请求强制流式升级超时50s导致过早切断，force-stream upgrade 超时前无法完成→走 ATE。
修复：对齐到 UPSTREAM=64，让 thinking 请求有足够时间完成。

## 改前数据

### 6h 全景
| 指标 | 值 |
|------|-----|
| 总请求 | 338 |
| 成功 | 238 (70.4%) |
| 失败 | 100 (29.6%) — 全部 `all_tiers_exhausted` |

### 按模型
| 模型 | 请求 | 成功 | SR | avg_dur | fail |
|------|------|------|-----|---------|------|
| dsv4p_nv | 229 | 137 | 59.8% | 60.2s | 92 ATE |
| glm5_2_nv | 107 | 100 | 93.5% | 47.8s | 7 ATE |
| kimi_nv | 2 | 1 | 50.0% | 2.4s | 1 ATE |

### nv_tier_attempts (6h)
| tier | error_type | count | avg_ms | max_ms |
|------|-----------|-------|--------|--------|
| dsv4p_nv | NVCFPexecTimeout | 44 | 41,018 | 59,596 |
| glm5_2_nv | NVCFPexecTimeout | 62 | 47,597 | 57,797 |
| dsv4p_nv | empty_200 | 4 | - | - |
| glm5_2_nv | NVCFPexecgaierror | 1 | 8,015 | 8,015 |

### 关键发现
1. **glm5_2_nv health=0.0**（函数 `3b9748d8` 完全死亡），所有请求 fallback 到 dsv4p_nv
2. **NVCFPexecTimeout 均匀分布**：5个key 都 47-58s 超时（all-key uniform），确认是 function-level 问题，非单个key
3. **docker logs 关键证据**：
   ```
   [NV-THINKING-TIMEOUT] (glm5_2_nv) thinking request stream=False → extended timeout 50s
   ```
   force-stream upgrade 超时只有 50s，而 UPSTREAM=64s。glm5_2 思考请求在 50s 时被 force-stream 机制过早切断，无法到达 64s 的 UPSTREAM 边界。
4. **NVU_FORCE_STREAM_UPGRADE_TIMEOUT 漂移历史**：
   - R734: 44→50（对齐 UPSTREAM=50）
   - R733: UPSTREAM 48→50
   - R742: UPSTREAM 62→64
   - **R742 后 FORCE_STREAM 未同步更新**，仍保持 R734 的 50s
5. **BUDGET 安全**：114 >> 64，零风险

### HM1 DNS 状态
容器 DNS ExtServers=[223.5.5.5, 223.6.6.6]，解析 `api.nvcf.nvidia.com` 返回美国节点（52.87, 34.227, 54.84）。与 R748 修复后的 HM2 一致，无 DNS region 问题。（HM1 日本 IP，到美国节点正常）

## 改动清单

### 单一参数：`NVU_FORCE_STREAM_UPGRADE_TIMEOUT` 50 → 64 (+14s)

**文件**: `/opt/cc-infra/docker-compose.yml`（仅 HM1，line 514）

```yaml
      NVU_FORCE_STREAM_UPGRADE_TIMEOUT: "64"  # R749: 50→64 (+14s) drift correction
```

**备份**: `docker-compose.yml.bak.R749`

**原因**: 对齐 UPSTREAM_TIMEOUT=64，消除 14s 漂移，让 glm5_2 思考请求有足够时间完成而非被 force-stream 超时过早切断。

## 改后验证

```
$ curl -s http://localhost:40006/health
{"status": "ok", ...}
$ docker exec nv_gw env | grep NVU_FORCE_STREAM_UPGRADE_TIMEOUT
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=64
```

YAML 验证通过，容器重启成功（`Recreated` → `Started`）。

## 铁律遵守

- ✅ 改前必有数据：6h DB + docker logs + env 完整收集
- ✅ 改后必有验证：health check + env 确认 + YAML 验证
- ✅ 聚焦 nv_gw：仅改 HM1 nv_gw compose 参数
- ✅ 所有修改写入仓库：本 round + compose backup
- ✅ 单参数 per round + 铁律：只改 HM1 不改 HM2

## ⏳ 轮到HM1优化HM2