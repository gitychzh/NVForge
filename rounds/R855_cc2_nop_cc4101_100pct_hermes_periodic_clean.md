# R855 cc2 NOP 巡检轮 — 近窗 cc4101-primary SR=100%，hermes 周期客户端 5×all_tiers_exhausted，不改码

## 结论
cc2 自身路径 (cc4101-primary) 近窗 **114×200, SR=100%, 零错误**。链路/KeyManager 健康，buffer 全走
dsv4f0731_nv attempt=1/5 一次成功。30min 残留 5×all_tiers_exhausted **全为 caller=hermes 外部 cron 客户端**，
非 cc2 使命，修复链自适应吸收正常。与 R853/R854 完全同型。**不改码 (NOP 巡检轮)。**

## 本轮数据 (2026-08-07 ~04:35 CST, DB UTC 对齐)

**30min caller × model × status (nv_requests):**
```
cc4101-primary | dsv4f0731_nv | 200 | 114   ← cc2 自己的请求, 全 200
hermes         | dsv4f0731_nv | 200 |    1
hermes         | dsv4f0731_nv | 502 |    5
```

**30min 错误分类 (仅非 200):**
```
all_tiers_exhausted | all_tiers_failed_in_mapped_tier | 5 | avg178273ms
```
全部 caller=hermes (外部动态客户端)，每次 ~178s ≈ 5×90s=450s buffer deadline 全额耗尽 → 严格 ~5-6min
周期 cron 请求特征 (与 R853/R854 判定一致)。cc4101-primary 路径 **零错误**。

**nv_gw buffer 日志 (近 20min):**
- 每条 `attempt=1/5` 一次成功 (dsv4f0731_nv), elapsed 1-13s, verdict=success_text / success_tool_call
- 零 buffer_exhausted, 零 WAIT, 零 fallback → 一次成交率 100%

**容器健康:**
- `nv_gw 40006 /health` → ok (passthrough, 5 keys, nvcf_pexec_models 含 dsv4p/dsv4f/dsv4f0731/glm5_2_nv/kimi_nv)
- `cc4101 4101 /health` → ok (primary=dsv4f0731_nv)

## 关键判断
- cc2 primary 仍 pinned dsv4f0731_nv (glm5_2_nv 风暴冷却未归)，一次成交 100%。
- hermes 周期 all_tiers_exhausted 属外部定时客户端在 buffer 峰值耗尽时的特征，非链路退化，不影响 cc2 NV 成功指标。
- 修复链 (R827+R828+R829+R833+R813 多 tier round-robin + fail-fast + 动态 primary) 充分。

## 改动
无。

## 验证
curl /health 双端 ok + nv_gw buffer 日志一次成交 + 近窗 cc4101-primary 114×200 零错误。

## 下一步
- 长期观测，glm5_2_nv 冷却退去后观察 cc4101 primary 是否自动回归主链路。
- 持续跟踪 hermes 周期错误曲线 (是否稳定 ≤5/30min)。
- 不改码。