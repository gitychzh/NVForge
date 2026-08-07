# R1119 cc2 NOP — cc4101-primary 106/106=100% SR 零错误, 全量 dsv4f0731_nv 148/148=100% SR, 零 fallback

> 轮: R1119  |  容器: nv_gw Up 25h, cc4101 Up 20h  |  时间: 2026-08-07 23:45 CST
> 决策: **NOP 不改码** (SR=100% ≥ 99%, 无新错误)

## 判稳依据 (轮前链路分析注入, 2026-08-07 23:44 CST)

- **cc4101-primary (cc2 专属, 经 nv_gw:40006)**: **106/106 = 100.0% SR, 0 bad, 零错误**
  (较上轮 R1118 的 105 增 1, 全绿)。
- **dsv4f0731_nv 全量**: **148/148 = 100.0% SR** (上轮 151/152=99.3%, 本轮 0 bad 更干净)。
  本窗口**全量非-200 = 空**, 无 502, 无 zombie_empty_completion。
- **fallback**: f|148 = **0% 触发**, 全走 primary。
- **错误分类 (nv_requests)**: `(无错误)` — 零错误。
- **nv_tier_attempts per-key**: 全 `pexec_success` 为主 (fid 281478d0):
  k0=22, k1=19, k2=20, k3=21, k4=24。
  仅 fid **52e1ddb6** 泄漏线的 k1 1× RD + k1 1× empty_200 + k4 1× empty_200 — 一次性 single-request
  distributed transient, tier 层自愈, 未上浮为 surface 错误, 无 multi-key 连续复发。
- **buffer/wait/keymanager 日志**: 无 (无超时、无 key 惩罚、无 WAIT) — 全 attempt-1 direct flush。

## 结论

cc2 主链连续多轮 100% SR + zero fallback (R1096-R1119 区间)。本窗口比上轮更干净
(全量 100%, 无任何非-200)。per-key 少量 empty_200/RD 归属 fid 52e1ddb6 (越界容器 40666 hermes 泄漏线,
宿主分离, 记忆模式), 非 cc2 配置问题。无参数可调, 不改码。

## 下一步

- 延续 NOP。零错误零 fallback, 无参数可调。
- 仅当 RD/error 在 **multi-request 多 key 连续复发** 才查链路/mihomo 线路; 单请求 tier 层自愈不处置。
- 若出现 caller=cc4101-primary 的 502/错误才进 cc2 指标处置。