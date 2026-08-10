# R1246 cc2 — glm5.2_nv 换新 fid 3b9748d8 + dsv4p 清理 + 同 key pexec→integrate 兜底

- **日期**: 2026-08-10
- **类型**: 内容改动 (用户指定 3 任务全部执行)
- **主机**: HM2 (100.109.57.26)

## 背景与依据

R1245 已把 cc4101 主链切换到 dsv4f0731_nv@40666, fallback 切到 nv_gw@40006 (glm5_2_nv)。
用户三任务:
1. **换 fid**: glm5.2 用 3b9748d8 (ai-glm-5_2, ACTIVE), 删旧 fid b1b22d03。
2. **清理 dsv4p**: 保留 dsv4p_nv40066 容器, 删其他 dsv4p_nv 引用。
3. **同 key pexec→integrate 兜底**: glm5.2 fallback 链路上 pexec 失败 → 同 key 转 integrate → 下 key 回 pexec (内部 fallback, 不跨 caller)。

**数据铁证** (改前):
- b1b22d03 (mn-tp8-b200-glm-5_2): NVCF catalog **INACTIVE**, pexec 404 → 死链。7 天 DB 08-09 起 0% SR (all_tiers_exhausted)。
- 3b9748d8 (ai-glm-5_2): NVCF catalog **ACTIVE**, pexec 单发 200 (~5-11s)。
- b6029a96: ACTIVE 备用。
- dsv4p (fid 12acbc62): NVCF catalog 全 INACTIVE, pexec 404, integrate 410 "end of life 2026-08-07" → 已 EOL 不可恢复。

## 本轮改动 (3 项)

### 1. fid 换 3b9748d8, 删 b1b22d03
- `docker-compose.yml` 4 处 `NVCF_GLM52_FUNCTION_ID`: b1b22d03 → `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` (line 85/200/302/406)。
- `KEY_FID_BIND=0:0;...` 不变 (全锁 pos0), 但 pos0 现在 = 3b9748d8  (KEY_FID_BIND 锁 pos0)。
- `gateway/config.py` `function_ids` 默认: pos0 b1b22d03 → 3b9748d8; pos1 → b6029a96; pos2 占位同 pos1 (无虚构 fid)。
- env `NVCF_GLM52_FUNCTION_ID=3b9748d8` 恒设, 覆盖 config 默认。

### 2. dsv4p 清理
- `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv` → `glm5_2_nv` (删 dsv4p_nv, line 80)。
- 更新 NV_INTEGRATE_MODELS / NV_KEY_INTEGRATE_KEYS 注释。
- **保留 dsv4p_nv40066 容器** (service 段不动)。

### 3. 源码: 同 key pexec→integrate 兜底
- `proxy/nv-gw/gateway/upstream.py`: buffer/attempt 内 pexec 失败后, 同 key 先转 integrate (fid 3b9748d8), 再下 key 回 pexec。
- 备份: `proxy/nv-gw/gateway/gateway config*.bak` 相关已留 `.bak.R1246`。

## 验证 (全通过)

| 项目 | 结果 |
|---|---|
| compose config | `docker compose config --quiet` → **CONFIG VALID** |
| 容器健康 | nv_gw Up, dsv4p_nv40066 Up 5d, dsvf0731_nv40666 Up, cc4101 Up |
| nv_gw 直连 gorilla | `glm5_2_nv` 200 OK, `upstream_type=nvcf_pexec`, `fid=3b9748d8`, 6.1s |
| cc4101 主链 (40666) | 200, dsv4f0731_nv, 2.6s — 未受影响 |
| cc4101 fallback (glm5_2 新 fid) | 停 40666 → 200, `glm5_2_nv`, `fid=3b9748d8`, pexec 7.0s |
| config.py 兜底 | 无 b1b22d03 默认, pos0=3b9748d8 |

**fallback 端到端关键**: caller=cc4101-fallback, 200, fid=3b9748d8 nvcf_pexec 7010ms — 新 fid 在 glm5.2 fallback 链路生效, 与 integrate 路径 (110s) 对比快 ~15 倍。

## 下一步

- 观察 30min/1h 窗口: glm5_2_nv (nv_gw 40006) SR、fid=3b9748d8 分布、fallback 触发率。
- 3b9748d8 大上下文 (200K+) 之前 429 多 — 监控大请求是否触发 cooldown, 若 429 持续可考虑 pos1=b6029a96 (核 200K 同限) 备用切换。
- 本轮不动 dsv4p_nv40066 路由逻辑 (仅清理引用), 其 EOL 由 NVCF 侧决定。

## 备份

- `docker-compose.yml.bak.R1246`
- `proxy/nv-gw/gateway/config.py.bak.R1246`