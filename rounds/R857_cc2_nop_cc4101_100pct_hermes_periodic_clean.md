# R857 cc2 NOP 巡检轮 — 近窗 cc4101-primary SR=100%，hermes 周期客户端 5×all_tiers_exhausted，不改码

## 结论
cc2 自身路径 (cc4101-primary) 近窗 **121×200, SR=100%, 零错误**。链路/KeyManager 健康，buffer 全走
dsv4f0731_nv 一次成交。30min 残留 5×all_tiers_exhausted **全为 caller=hermes 外部 cron 客户端**，
非 cc2 使命，修复链自适应吸收正常。与 R853/R854/R855/R856 完全同型。**不改码 (NOP 巡检轮)。**

## 本轮数据 (2026-08-07 ~04:40 CST, 轮前链路分析注入, DB UTC 对齐)

**30min caller × model × status (nv_requests):**
```
cc4101-primary | dsv4f0731_nv | 200 | 121   ← cc2 自己的请求, 全 200
hermes         | dsv4f0731_nv | 200 |    1
hermes         | dsv4f0731_nv | 502 |    5
```

**30min 错误分类 (仅非 200):**
```
all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | avg179142ms
```
全部 caller=hermes (外部动态客户端)，每次 ~179s ≈ 5×90s=450s buffer deadline 全额耗尽 → 严格 ~5-6min
周期 cron 请求特征 (与 R853/R854/R855/R856 判定一致)。cc4101-primary 路径 **零错误**。

**30min per-key × status (nv_tier_attempts, dsv4p/dsv4f0731 层):**
```
key0   pexec_success 24   | 529_nv_overloaded 4   | RemoteDisconnected 2 | Timeout 1
key1   pexec_success 24   | RemoteDisconnected 4   | 529_nv_overloaded 1 | Timeout 2
key2   pexec_success 24   | 529_nv_overloaded 2   | RemoteDisconnected 3 | budget_exhausted 1
key3   pexec_success 23   | RemoteDisconnected 4   | 529_nv_overloaded 1 | Timeout 1
key4   pexec_success 26   | RemoteDisconnected 3   | 529_nv_overloaded 1 | empty_200 2
```
5 key 均有足量 pexec_success，KeyManager 自适应吸收跨 key 瞬态失败，无 single-key 性疲劳。

**nv_gw buffer/wait/keymanager 日志 (近 30min):**
- 无 BUFFER/WAIT 异常日志 → 全走 dsv4f0731_nv 一次成交, 零 buffer_exhausted, 零 WAIT

**容器健康 (实时 curl 确认):**
- `nv_gw 40006 /health` → ok (passthrough, 5 keys, nvcf_pexec_models 含 kimi_nv/dsv4p/dsv4f/dsv4f0731/glm5_2_nv)
- `cc4101 4101 /health` → ok (primary=dsv4f0731_nv)

## 关键判断
- cc2 primary 仍 pinned dsv4f0731_nv (glm5_2_nv 风暴冷却未归)，一次成交 100%。
- hermes 周期 all_tiers_exhausted 属外部定时客户端在 buffer 峰值耗尽时的特征，非链路退化，不影响 cc2 NV 成功指标。
- 修复链 (R827+R828+R829+R833+R813 多 tier round-robin + fail-fast + 动态 primary) 充分。

## 改动
无。

## 验证
curl /health 双端 ok + nv_gw buffer 日志一次成交 + 近窗 cc4101-primary 121×200 零错误。

## 下一步
- 长期观测，glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归主链路。
- 持续跟踪 hermes 周期错误曲线 (是否稳定 ≤5/30min)。
- 不改码。