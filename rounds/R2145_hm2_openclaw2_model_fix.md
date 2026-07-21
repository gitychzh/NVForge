# R2145: HM2 — openclaw2 model 名修复 (cc-glm5-2 → glm5_2_nv), 解 dsv4p 502 空转

## 摘要

用户报"cc2 彻底挂了卡在 dsv4p_nv 502"。现场诊断发现 **cc2 没挂**, 真正每轮 502 空转的是 **openclaw2**: 直连 nv_gw(40006) 但 claude settings `model: cc-glm5-2` 不在 nv_gw MODEL_MAP → 路由到 `nv_default_model=dsv4p_nv` → dsv4p_nv 在 NVCF 端挂了 9h+ (5 key 全 cooldown) → 每轮 1ms 秒回 502。

修复: 改 openclaw2 settings `model: cc-glm5-2` → `glm5_2_nv` (备份 .bak.R2083)。HM2 only, 未碰 nv_gw 代码, 未碰 agent 行为。

## 改前数据 (改前必有数据)

### openclaw2 runlog — 连续 8+ 轮 dsv4p 502 空转
```
[09:27] API Error: 502 All NV API tiers failed for dsv4p_nv after 1.8s
[09:34] API Error: 502 All NV API tiers failed for dsv4p_nv after 1.9s
[09:41] API Error: 502 All NV API tiers failed for dsv4p_nv after 1.6s
[09:47] API Error: 502 All NV API tiers failed for dsv4p_nv after 5.7s
[09:55] API Error: 502 All NV API tiers failed for dsv4p_nv after 1.8s
[10:02] API Error: 502 All NV API tiers failed for dsv4p_nv after 2.0s
[10:08] API Error: 502 All NV API tiers failed for dsv4p_nv after 0.0s [cooldown]
[10:14] API Error: 502 All NV API tiers failed for dsv4p_nv after 1.7s
```
每轮 rc=0 (claude 报错即退), 0 产出。

### dsv4p_nv NVCF 端真挂了 9h+
- 最后一成功: 2026-07-21 00:49 UTC
- 02:00 窗口全 502 (67 次)
- error_detail: `all_cooldown:true, num_attempts:0, skipped:true, elapsed_ms:1` (tier 全 cooldown, 请求 1ms 秒回)
- socks5 7900-7904 全 OPEN (非代理问题, 是 NVCF function 74f02205 端坏)

### cc2 对照 (健康, 没挂)
- 走 cc4101→glm5_2_nv (cc4101 把 cc-glm5-2 改写成 glm5_2_nv, R1711)
- jsonl(10:16): model=glm5_2_nv(8次)+glm5_2_ms(2次fallback), PRIMARY-FAIL→FALLBACK-OK 正常
- 自优化 R2136 正常进行

### glm5_2_nv (cc2/openclaw2 真实模型) 健康
- 1h: 76 成功 / 1 失败

## 根因

| 系统 | ANTHROPIC_BASE_URL | settings model | 实际路由 |
|---|---|---|---|
| cc2 | 4101 (cc4101) | cc-glm5-2 | cc4101 改写→glm5_2_nv ✅ |
| openclaw2 | 40006 (nv_gw 直连) | cc-glm5-2 | nv_gw MODEL_MAP 不识别→default dsv4p_nv ❌ |

R1648 终态架构让 nv_gw 自带 anthrop↔openai 转换, openclaw2 直连 nv_gw 是设计内。但漏了"model 名不被 nv_gw 识别会路由到 default"这个边界。cc4101 在中间做了改写所以 cc2 不受影响; openclaw2 直连就暴露了。

## 改动

文件: `/home/opc2_uname/cc_ps/openclaw2_repair_self/.claude/settings.json`
备份: `settings.json.bak.R2083`

```diff
-  "model": "cc-glm5-2"
+  "model": "glm5_2_nv"
```

用户拍板选项"修 openclaw2 model 名"(非 nv_gw MODEL_MAP), 理由: 最小改动, 不碰 nv_gw 代码/不 build/restart, cc4101 已在做改写不重复。

## 改后验证 (改后必有验证)

### 10:22:56 轮 (读到新 settings 的第一轮, 10:31:04 结束 rc=0)
- **runlog 出现实际工作内容**: "main 已在 R2143，但我的本地提交 0939ee1 未 push..." (openclaw2 在做 git pull/rebase 分析, 不再秒回 502)
- **jsonl model**: 20 次 `glm5_2_nv` (0 个 dsv4p 路由)
- **nv_gw 5min glm5_2_nv**: 5/5 全 200

### openclaw2 不再发 dsv4p 请求
改前: openclaw2 每轮发 dsv4p_nv → 502
改后: openclaw2 全走 glm5_2_nv → 200

(dsv4p_nv 仍有 502 是 hermes 主 agent 在发, model.default=dsv4p_nv, 非 openclaw2 域)

## 归因结论

openclaw2 已救活, 从"每轮 dsv4p 502 秒回空转"变成"正常 glm5_2_nv 自优化"。

**dsv4p_nv 本身 NVCF 端挂了 9h+ 不可控** (非 nv_gw 旋钮能修), 但这不影响 cc2/openclaw2 (走 glm5_2_nv)。只影响 hermes 主 agent (走 dsv4p_nv), 等 NVCF 自愈。

## 教训

用户/runlog 看到"cc2 报 dsv4p 502"不一定是 cc2 —— 可能 openclaw2/hermes2 统称, 或是 cc2 读 nv_gw 日志看到的 dsv4p 错误 (cc2 jsonl 有 6 次 dsv4p 是它分析日志读到的, 非自己请求)。必查 jsonl 的 model 字段确认实际请求模型。

HM2 only, 未碰 nv_gw 代码, 未碰 ms-gw, 未碰 HM1。
