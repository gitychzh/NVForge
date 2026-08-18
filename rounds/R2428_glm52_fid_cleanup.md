# R2428 — glm5_2_nv 死 fid 候选清理

**时间**: 2026-08-18
**容器**: nv_gw (40006)

## 背景

NVCF 全量扫描 (192 functions, 4 key 实测) 发现:
- 仅 1 个 ACTIVE glm-5_2 fid: `3b9748d8` (ai-glm-5_2)
- `bfcf495b` / `b1b22d03` / `b6029a96` / `5532e90c` / `73eccb72` 全部 INACTIVE, pexec 404
- **无 glm-5.3** — NVCF 上不存在
- KEY1 (nvapi-Oi2S0DK...) 已死, 403 Forbidden

## 改动

### config.py (proxy/nv-gw/gateway/config.py)
- glm5_2_nv `function_ids` 从 2 个候选 `[3b9748d8, bfcf495b]` 精简为 1 个 `[3b9748d8]`
- bfcf495b 已 404, 留在候选 → func_health 选中后浪费 attempt + 拖慢 8-15s
- fid_discovery 仍运行 (ENABLED=1), 发现新 ACTIVE fid 时自动替换 pos0 (in-memory)

### docker-compose.yml
- 删除 `NV_GLM52_FUNCTION_ID2/3/4/5` 死 fid env vars (注释保留)
- 这些 env 本来已不被 config.py 读取 (R1255 精简时遗留), 删除避免混淆

## 验证

1. `docker compose restart nv_gw` — 容器正常启动
2. `curl /health` — status=ok, models=[glm5_2_nv]
3. Python 验证: `function_ids = [3b9748d8]`, total=1 ✅
4. env 验证: 无死 fid env vars ✅

## 注意

- nv_breaker 当前 OPEN (all_keys_exhausted, 5key 全 429), 流量走 ms_gw
- 原因: 唯一 ACTIVE fid 3b9748d8 被 NVCF rate-limit, 非 fid 配置问题
- fid_discovery 30min 周期自动扫描, 发现新 ACTIVE fid 会替换 pos0
