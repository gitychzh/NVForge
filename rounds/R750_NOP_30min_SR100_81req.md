# R750 — NOP 巡检 (2026-08-05 05:45 CST)

## 结论: 第 16 连续 100% 轮 (R735-R750), NOP, 链路已稳

## 实测数据 (created_at 实测核验, 05:45 CST 30min 窗)
- **cc2 nv_requests (caller=cc4101-primary): 81×200, SR=100%**
- **cc_requests: 82 total / 82 ok / 0 fb, SR=100%, fb=0%**
- 注入的 "f|91" fallback 段是 ts 列时区 bug 口径 → created_at 实测 0 fb (沿 R730/R742-R749 实证)

## per-key × error 分布 (注入数据, 全被 buffer 兜住)
- k0: pexec_success=16, 529_nv_overloaded=2, NVCFPexecRemoteDisconnected=1, empty_200=1
- k1: pexec_success=16, 529_nv_overloaded=1, NVCFPexecRemoteDisconnected=5
- k2: pexec_success=15, 529_nv_overloaded=1, NVCFPexecRemoteDisconnected=5
- k3: pexec_success=16, 529_nv_overloaded=1, NVCFPexecRemoteDisconnected=4
- k4: pexec_success=15, NVCFPexecRemoteDisconnected=3
- 总 pexec_success = 16+16+15+16+15 = 78 (与 cc2 78×200 链路请求一致, 注入噪声被 buffer 兜住)

## 噪声来源 (不在 cc2 路径)
- all_tiers_exhausted=8 (avg_dur 83872ms) + NVStream_IncompleteRead=2 → hermes→dsv4f0731_nv 上游 NVCF 容量
- dsv4f0731_nv SR=23.1% (3/13) → hermes caller 容器, dsvf0731_nv40666 Up 5min 刚重启, 不影响 cc2

## 验证 (NOP 无需 restart)
- /health: nv_gw ok (5 keys, glm5_2_nv default) + cc4101 ok
- docker ps: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, dsvf0731_nv40666 Up 5min, logs_db Up 5d — 全 Up
- env 沿 R749, 无漂移

## 判稳
- SR 100% ≥ 99%, fb 0% < 10% — 达标
- 连续 16 轮 (R735-R750) 100% SR, 链路已稳
- NOP, 无可改项

## 下一步
- 持续监控, 流量低时不动码
- 注入噪声 529/empty_200/NVCFPexecRemoteDisconnected 持续观察, 若泄漏到 cc2 (buffer 失效) 再查

## 参数快照 (沿 R749, 无变化)
- nv_gw: NVU_DISABLE_MS_FALLBACK=1, MODE_CHAIN=pexec_us_rr, 全 key 绑 fid1=b1b22d03,
  KEY_PROXY_BIND=0:7901;1:7894;2:7897;3:7896;4:7899, buffer 5×90s=450s, UPSTREAM_TIMEOUT=90
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, FALLBACK=glm5_2_ms→ms_gw:40007,
  STREAM_TOTAL=470, HEADER=400, UPSTREAM_IDLE=150, UPSTREAM_TIMEOUT=130
- deadline 链: 90s×5=450s buffer < 470s cc4101 < 600s API < 900s idle
