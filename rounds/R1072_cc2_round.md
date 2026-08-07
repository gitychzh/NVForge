# R1072 cc2 round (NOP 巡检)

日期: 2026-08-07 20:1x CST
容器: nv_gw Up 16h, cc4101 Up 16h (cc4101 primary=dsv4f0731_nv → main nv_gw:40006)

## 判定: NOP (主链 106/106 = 100% SR 0 bad, 无新错误, 无参数可调)

## 数据 (注入轮前分析 19:57 CST + 独立 DB 复核 + 容器 /health)
- 30min 总览 (独立复核): cc4101-primary|dsv4f0731_nv|200|106; hermes|dsv4f0731_nv|200|64 + 502|2
- cc4101-primary (cc2 请求): **106/106 = 100% SR, 0 bad** ✅
- dsv4f0731_nv 整体 SR=98.7% (170/172) — 2 个 502 zombie_empty_completion 全属 hermes 越界宿主非主链
- 30min cc_requests: fallback 0 次 / 0.0% (f|172 全走主链)
- 错误分类: zombie_empty_completion×2 (复核归属: 全 hermes 越界宿主, 非 cc2 范围)
- per-key: 0/1/2/3/4 全 pexec_success (23/17/25/20/21) — 无错误噪声
- buffer 日志: 无 buffer/wait/keymanager 日志
- 容器 (复核): nv_gw Up 16h, cc4101 Up 16h, /health 40006/4101 全 200

## 改动: 无

## 下一步
- 保持 NOP 观察。主链连续多轮 0 bad 已达"完全健康基线"。
- 仅当 SSLEOFError>10次/10min 且同窗多请求 502 才排查 egress; 当前低频常态。
- 单 key 连续多轮 100% 失败才考虑换 fid; 当前 per-key 全 pexec_success, 无此需。