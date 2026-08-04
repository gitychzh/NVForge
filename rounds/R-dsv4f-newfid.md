# R-dsv4f-newfid: deepseek-v4-flash 新 FID 发现 + pexec 恢复 + 40666 容器更新

**Date:** 2026-08-04
**Container:** dsvf0731_nv40666 (port 40666, HM2)
**Commit:** (this round)

## 背景

旧 FID `6166b605` (0731-deepseek-v4-flash) 已变为 INACTIVE。需重新发现可用 FID。

## NVCF functions list 探测 (历史性突破)

首次成功调用 NVCF functions list API (`GET /v2/nvcf/functions`), 返回 200 + 178 个 functions。

### deepseek-v4-flash 相关 FID

| FID | name | status | pexec 测试 | 备注 |
|-----|------|--------|-----------|------|
| `52e1ddb6` | ai-deepseek-v4-flash | **ACTIVE** | **200 OK** | ✅ 新主 FID, pexec 可用! |
| `6166b605` | 0731-deepseek-v4-flash | INACTIVE | 404 | 旧 FID 已死 |
| `cbde15a8` | kvlab-deepseek-v4-flash | ACTIVE | 404 | 账户不可用 |
| `32663475` | private-deepseek-v4-flash | INACTIVE | - | |
| `034cae7a` | dspark-deepseek-v4-flash | INACTIVE | - | |

### kimi-k3 发现
- `3ea2c6ee` (vllm-gb300-kimi-k3) status=ACTIVE, 但 pexec 全 404 "Not found for account"
- kimi-k3 仍账户级不可用

## 多链路对比测试 (Phase 1-3)

### PEXEC: FID 52e1ddb6 × 5 keys × 6 proxies

| Proxy | k1 | k2 | k3 | k4 | k5 | SR |
|-------|----|----|----|----|----|-----|
| direct | OK 1.3s | 529 | OK 1.6s | 529 | 529 | 2/5=40% |
| p7897 | OK 2.7s | 529 | 529 | 529 | 529 | 1/5=20% |
| p7904 | OK 2.9s | 529 | OK 2.1s | 529 | 529 | 2/5=40% |
| p7894 | 529 | OK 2.6s | 529 | 529 | 529 | 1/5=20% |
| p7896 | 529 | 529 | OK 3.8s | 529 | 529 | 1/5=20% |
| p7895 | OK 5.0s | 529 | 529 | 529 | 529 | 1/5=20% |

**pexec 总 SR: 8/30 = 27%** (529 占比 ~65-70%)

### INTEGRATE: model deepseek-ai/deepseek-v4-flash × 5 keys × 6 proxies

| Proxy | k1 | k2 | k3 | k4 | k5 | SR |
|-------|----|----|----|----|----|-----|
| direct | 529 | 529 | 529 | 529 | 529 | 0/5=0% |
| p7897 | OK 4.0s | 529 | OK 2.8s | 529 | OK 2.4s | 3/5=60% |
| p7904 | 529 | 529 | 529 | 529 | 529 | 0/5=0% |
| p7894 | 529 | 529 | 529 | 529 | 529 | 0/5=0% |
| p7896 | 529 | 529 | 529 | 529 | 529 | 0/5=0% |
| p7895 | 529 | 529 | 529 | 529 | 529 | 0/5=0% |

**integrate 总 SR: 3/30 = 10%** (p7897 是唯一可用代理)

### 关键发现
1. **pexec 现在可用!** (旧 FID 6166b605 时 pexec 全 404)
2. pexec SR (27%) > integrate SR (10%) — 翻转了之前的比例
3. pexec 延迟 1-5s < integrate 延迟 2-4s
4. 529 (NVCF Overloaded) 是主要故障模式 (~65-75%)

## 变更

### config.py
- `dsv4f_nv.function_ids` 默认值: `6166b605` → `52e1ddb6`
- 注释更新: 标注 pexec 现已可用

### docker-compose.yml (40666 容器)
- `NVCF_DEEPSEEK_FLASH_FUNCTION_ID`: `6166b605` → `52e1ddb6`
- `NV_INTEGRATE_MODELS`: `dsv4f_nv` → (空) — 不再强制 integrate, pexec 可用

## E2E 验证

### 40666 直接测试 (10次)
```
#1 ERR 502 17.6s (529 retry exhausted)
#2 OK 200 3.4s Hello.
#3 OK 200 3.0s Hello!
#4 OK 200 6.5s Hello.
#5 OK 200 19.5s Hello!  (529 retry 后成功)
#6 OK 200 2.1s Hello.
#7 ERR 502 18.9s (529 retry exhausted)
#8 OK 200 5.1s Hello
#9 OK 200 6.3s Hello
#10 OK 200 3.3s Hello!
```
**SR: 7/10 = 70%**

### 40666 二次测试 (5次, 无间隔)
```
#1 OK 200 4.3s Hello.
#2 OK 200 11.1s Hello
#3 OK 200 4.5s Hello.
#4 OK 200 13.5s Hello!
#5 OK 200 4.3s Hello!
```
**SR: 5/5 = 100%** (529 cycling 有效工作, retry 到成功)

## 结论

- 新 FID `52e1ddb6` (ai-deepseek-v4-flash) 替换旧 INACTIVE FID `6166b605`
- pexec 路径恢复可用, 不再依赖 integrate-only
- 529 cycling 机制有效: 单次 ~25% SR, retry 后 E2E 70-100%
- kimi-k3 仍不可用 (账户级 404)
