# R1070 cc2 round (NOP 巡检)

日期: 2026-08-07 20:5x CST
容器: nv_gw Up 16h, cc4101 Up 16h (cc4101 primary=dsv4f0731_nv → main nv_gw:40006)

## 判定: NOP (主链 111/111 = 100% SR 0 bad, 无新错误, 无参数可调)

## 数据 (注入轮前分析 19:48 CST + 容器 /health 复核)
- cc4101-primary (cc2 请求): **111/111 = 100% SR, 0 bad** ✅
- dsv4f0731_nv 整体 SR=98.2% (161/164) — 3 个 zombie_empty_completion 全属 hermes 越界宿主非主链
- 30min cc_requests: fallback 0 次 / 0.0% (f|164 全走主链)
- 错误分类: zombie_empty_completion×3 (全 hermes 越界宿主, 非 cc2 范围)
- per-key: 0/1/2/4 全 pexec_success (22/20/25/21), key3 pexec_success×23 + 单条 NVCFPexecRemoteDisconnected×1 (常态噪声)
- buffer 日志: 无 fail/WAIT/KEYMGR
- 容器: nv_gw Up 16h, cc4101 Up 16h, nv_gw_stable Up 5d, /health 40006/4101 全 200

## 改动: 无

## 下一步
- 保持 NOP 观察。主链连续多轮 0 bad 已达"完全健康基线"。
- 仅当 SSLEOFError>10次/10min 且同窗多请求 502 才排查 egress; 当前低频常态。
- 单 key 连续多轮 100% 失败才考虑换 fid; 当前主链 fid 281478d0 全 pexec_success。