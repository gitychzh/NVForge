# R649 — glm5_2_nv per-key 混合链路 + dsv4p_nv40066 独立容器 (2026-08-03 15:07 CST)

## 当前轮号基线
- R649 部署时刻: 2026-08-03 15:07 CST (07:07 UTC)
- 改动: glm5_2_nv per-key 混合链路 + dsv4p_nv40066 独立容器作 cc4101 fallback

## 本轮改了什么
- nv_gw 源码 (config.py + upstream.py): 新增 NV_GLM52_KEY_FID_BIND + NV_GLM52_KEY_MODE_BIND (独立 env, 非全局, 仅 glm5_2_nv 读). 修复 function_ids 列表回 3 真实 fid.
- nv_gw env: MODE_CHAIN=pexec_us_rr,integrate_us_rr; KEY_MODE_BIND=k1/3/5 pexec + k2/4 integrate; FID_BIND=k1/3/5→fid1/2/3; 关 ms/peer fallback (NVU_MS_FALLBACK_ENABLED=0, NVU_PEER_FALLBACK_ENABLED=0, NVU_DISABLE_MS_FALLBACK=1).
- 新增 dsv4p_nv40066 容器 (port 40066): pexec-only, 5 US IP (7900-7904), 无 fallback, free 5-key. 复用 cc-infra-nv_gw image + 同源码 bind-mount.
- cc4101: PRIMARY=glm5_2_nv (改自 dsv4p_nv), FALLBACK=dsv4p_nv40066:40066 (改自 ms_gw). depends_on 去 ms_gw 加 dsv4p_nv40066.

## 依据
- 08-03 多链路测试: integrate+5US IP SR 96% (最稳), pexec fid1 72%/fid2 88%/fid3 52% (全不稳).
- 容器内无 proxy 0%, 本地 IP 直连 56.7% (单 IP throttling).
- R639-R648 NOP 确认 dsv4p_nv 24h SR 71%, all_tiers_exhausted 96% (NVCF 配额耗尽, 非 nv_gw 可改).

## 验证 (07:13-07:25 UTC)
- 3 容器 health ok: dsv4p_nv40066:40066, nv_gw:40006, cc4101:4101 (primary=glm5_2_nv)
- per-key 路由铁证 (nv_tier_attempts DB):
  k1→b1b22d03(pexec), k2→integrate, k3→3b9748d8(pexec), k4→integrate, k5→b6029a96(pexec) ✓
- dsv4p_nv40066 独立响应 3/3 200 (1-3s) ✓
- cc4101 端 8 次 glm5_2_nv: 7/8 200 (87.5% 初步)
- 5min 全 caller SR: 11×200 + 1×429 = 91.7%

## 下一步
- 等 30min 稳定窗口确认 glm5_2_nv (cc4101-primary) SR ≥ 90%, dsv4p fallback 触发率 < 10%.
- 观察 integrate path (k2/4) 生产稳定性.
- 观察 fid2/fid3 (k3/k5) 生产表现 (测试时 fid3 52% 最差, 若持续低则切 integrate).
- 回切阈值沿用 R621: SR<55% 或 exhausted>=8 持续才回切.

## 参数快照
- cc4101: PRIMARY=glm5_2_nv@nv_gw:40006, FALLBACK=dsv4p_nv@dsv4p_nv40066:40066, HEADER=400, DEADLINE=470
- nv_gw: MODE_CHAIN=pexec_us_rr,integrate_us_rr, KEY_MODE_BIND=k1/3/5 pexec+k2/4 integrate, FID_BIND=k1/3/5→fid1/2/3, MS/PEER fallback 全关
- dsv4p_nv40066: pexec-only, 5 US IP (7900-7904), 无 fallback, free 5-key, port 40066
- mihomo (宿主 pid 1056): 7894-7904 共 10 端口

## 回滚
- compose: cp docker-compose.yml.bak.R-glm52split.20260803_150723 docker-compose.yml
- 源码: cp config.py.bak.R-glm52split.20260803_150723 config.py; cp upstream.py.bak.R-glm52split.20260803_150723 upstream.py
- 重启: docker compose up -d nv_gw cc4101 && docker rm -f dsv4p_nv40066
