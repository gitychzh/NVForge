# R752 NOP — 30min SR 100%/fb 0% (84 req), 18th consecutive 100% round

**时间**: 2026-08-05 06:00 CST
**上轮**: R751 (17th consecutive 100%)
**改动**: 不改码 (NOP 巡检)

## 依据 (created_at 实测核验)

### cc2 链路 (cc4101-primary × glm5_2_nv)
- nv_requests: 84×200 (SR=100%)
- cc_requests: 84 total / 84 ok / 0 fb (SR=100%, fb=0%) — created_at 实测
- 注入的 `f|106` fallback 发生率 → created_at 实测 0 fb (ts 列时区 bug 伪影, 沿 R730/R742-R751)

### per-key pexec_success 分布 (零差额)
- k0=18, k1=17, k2=17, k3=17, k4=15 = 总 84
- 与 cc2 84×200 完全一致 — 无任何错误穿透 cc2

### 注入噪声 (全来自 hermes→dsv4f0731_nv, 被 buffer 兜住)
- NVCFPexecRemoteDisconnected=19
- 529_nv_overloaded=5
- empty_200=1
- all_tiers_exhausted=8 (dsv4f0731_nv 上游 NVCF 容量)
- NVStream_IncompleteRead=1

## 验证
- `/health`: nv_gw ok (5 keys, glm5_2_nv default)
- `docker ps`: nv_gw Up 3h, cc4101 Up 4h, dsv4p_nv40066 Up 9h, nv_gw_stable Up 3d, logs_db Up 5d — 全 Up
- env 沿 R751, 无漂移

## 判稳结论
- **18 连续 100% (R735~R752), fb=0** — 全面达标
- 连续第 6 轮最干净: per-key 全 pexec_success, 零错误穿透 cc2
- NOP 巡检轮, 无可改项

## 下一步
- 持续 NOP 监控 SR + fb
- 注入噪声若泄漏到 cc2 再查根因
- 流量低不动码

## 参数快照 (沿 R751, 无变化)
- nv_gw: pexec_us_rr 单 mode, 全 key 绑 fid1=b1b22d03, buffer 5×90s=450s
- cc4101: PRIMARY=glm5_2_nv→nv_gw:40006, STREAM_TOTAL=470, HEADER=400
- deadline 链: 90s×5=450s < 470s < 600s < 900s
