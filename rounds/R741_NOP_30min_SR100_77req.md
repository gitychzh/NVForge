# R741 — cc2 nv_gw NOP 巡检 (2026-08-05 05:04 CST)

> 第 7 连续 100% 轮 (R735~R741)

## 数据 (30min 窗, 注入, ~05:03 CST)

### cc2 (cc4101-primary|glm5_2_nv)
- **77×200, SR=100%, fb=0% (0/99 fallback)** — 持续全面达标
- 平均时长 19071ms (cc4101-primary|200|77|19071|)
- 用户可见 SR=100%

### 30min 错误分类 (type|sub|count|avg_dur)
- all_tiers_exhausted|all_tiers_failed_in_mapped_tier|7|64233 — 全来自 hermes/dsv4f0731_nv
- NVStream_IncompleteRead||1|36792 — 1 个,cc2 链路不可见

### per-key tier_attempts 错误分布 (k0-k4, glm5_2_nv)
- k0: 9×529_nv_overloaded, 2×NVCFPexecRemoteDisconnected, 15×pexec_success
- k1: 8×529_nv_overloaded, 3×NVCFPexecRemoteDisconnected, 16×pexec_success
- k2: 8×529_nv_overloaded, 2×NVCFPexecRemoteDisconnected, 15×pexec_success
- k3: 9×529_nv_overloaded, 1×NVCFPexecRemoteDisconnected, 1×empty_200, 15×pexec_success
- k4: 8×529_nv_overloaded, 2×NVCFPexecRemoteDisconnected, 2×529_integrate_overloaded, 16×pexec_success
- **pexec_success 合计 77 (= cc2 77×200 一致)**: 529 noise 被 buffer 兜住,对 cc2 不可见

### hermes/dsv4f0731_nv (非 cc2 链路)
- 14×200 + 8×502, SR=63.6% — NVCF 容量,与 cc2 无关
- hermes→dsv4f0731_nv 全 502 = all_tiers_exhausted

## 判稳
- **SR=100% (77/77) ≥ 99% 阈值, fb=0% < 10% 阈值, 无新错误类型** → NOP 巡检轮
- 529 storm + empty_200/integrate_overloaded 微噪声持续,buffer 兜住 → cc2 不可见
- 第 7 连续 100% 轮 (R735~R741)

## 验证 (NOP 无需 restart)
- nv_gw /health: ok (5 keys, glm5_2_nv default)
- cc4101 /health: ok (primary=glm5_2_nv)
- docker ps: nv_gw Up 2h, cc4101 Up 3h, dsv4p_nv40066 Up 8h — 全 Up 无异常
- 新增容器 dsvf0731_nv40666 (Up ~1h) — 不在 cc2 链路,无影响

## 改动
无 (NOP)

## 下一步
- 持续监控 cc2 SR + fb (目标 SR 99%+ / fb <10%)
- 529/empty_200/integrate_overloaded 微噪声若未来泄漏到 cc2 (buffer 失效) 再查
- 流量低时不动码,仅 NOP 记数据

## 参数快照 (沿 R740, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, MODE_CHAIN=pexec_us_rr, 全 key 绑 fid1=b1b22d03
  - buffer 5×90s=450s, UPSTREAM_TIMEOUT=90, TIER_COOLDOWN_S=180
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007
  - STREAM_TOTAL=470, HEADER=400
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
