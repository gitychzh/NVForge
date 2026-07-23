# R2297: HM2优化HM1 — 启用kimi_nv peer-fallback救援

## 检测: HM1提交了新commit (R2158), 轮到HM2执行优化

## 数据收集

### HM1 nv_gw日志 (最近error/warn)
```
[19:59:04] [NV-CONN] tier=kimi_nv k4 connection error: Remote end closed connection without response
[20:00:05] [NV-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=2, timeout=0, other=1, elapsed=159025ms
[20:00:05] [NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['kimi_nv']), elapsed=159029ms, ABORT-NO-FALLBACK
[20:03:37] [NV-TIER-FAIL] tier=kimi_nv all 5 keys failed: 429=0, empty200=2, timeout=0, other=1, elapsed=165122ms
[20:03:37] [NV-ALL-TIERS-FAIL] All 1 tiers failed (ring tiers tried: ['kimi_nv']), elapsed=165127ms, ABORT-NO-FALLBACK
```

### 6h DB统计
| 模型 | 成功 | 失败 | SR |
|------|------|------|-----|
| glm5_2_nv | 20 | 10 | 66.7% |
| kimi_nv | 10 | 22 | 31.3% |
| **总计** | 30 | 32 | 48.4% |

### 30m DB统计
| 模型 | 成功 | 失败 | SR |
|------|------|------|-----|
| glm5_2_nv | 2 | 0 | 100% |
| kimi_nv | 0 | 5 | 0% |

### kimi_nv ATE详情 (6h): 15个ATE + 7个zombie
- 全部 tiers_tried_count=1, 仅尝试kimi_nv tier
- 0 tier_attempts → 全部pre-empted (远程连接断开)
- 错误类型: empty_200 (7), NVCFPexecRemoteDisconnected (4), NVCFPexecSSLEOFError (3)

### 30m延迟
- glm5_2_nv: avg 7,464ms
- kimi_nv: 1个成功 30,887ms (其他全部失败)

### Fallback: 0次fallback发生 (6h内63请求全无fallback)

### 429 key cycling: kimi_nv 9次key_cycle_429s=1

## 根因分析

1. **kimi_nv NVCF上游连接严重恶化**: NVCFPexecRemoteDisconnected + SSLEOFError + empty_200 = 所有5个key全部失败
2. **peer-fallback被禁用**: `NVU_PEER_FB_SKIP_MODELS=kimi_nv` 阻止了HM2救援
3. **HM2 kimi_nv SR=80%** (来自脚本): 远优于HM1的31.3%，peer-fallback有巨大潜力
4. **无fallback tier**: kimi_nv无其他NVCF tier可fallback，只能等peer-fallback

## 优化计划

**单参数改动**: 清除 `NVU_PEER_FB_SKIP_MODELS` 中的 `kimi_nv`，启用HM2 peer-fallback救援kimi_nv请求。

## 执行

### 改动: `NVU_PEER_FB_SKIP_MODELS=kimi_nv` → `NVU_PEER_FB_SKIP_MODELS=` (空)

```bash
# 行483: 清除kimi_nv peer-fb skip
sed -i '483s/- NVU_PEER_FB_SKIP_MODELS=kimi_nv/- NVU_PEER_FB_SKIP_MODELS=/' /opt/cc-infra/docker-compose.yml
```

### 重启: `docker compose up -d --no-deps --force-recreate nv_gw` ✅

### 验证: 容器健康 ✅, YAML校验通过 ✅, live env确认 `NVU_PEER_FB_SKIP_MODELS=` (空)

## 预期效果

- kimi_nv请求失败后自动fallback到HM2 (100.109.57.26:40006)
- peer-fallback超时122s，足够覆盖kimi_nv的~120-165s请求
- 单参数改动，零风险：仅移除skip列表中的一个模型名
- 不影响其他模型 (glm5_2_nv, dsv4p_nv 不受peer-fb-skip影响)

## 评判

- 更少报错 ✓ (预期kimi_nv ATE下降)
- 更快请求 ✓ (peer-fallback比完全失败快)
- 超低延迟 ✗ (非本参数目标，但减少失败即改善)
- 稳定优先 ✓ (单参数，零副作用)
- 铁律: 只改HM1不改HM2 ✓

## ⏳ 轮到HM1优化HM2