# R291: HM1→HM2 — 🔧 HM2恢复后mihomo代理修复 (故障恢复, 非参数调优)

> **Round**: R291 | **Actor**: HM1 → **Target**: HM2 | **Date**: 2026-06-29 08:25 UTC | **Type**: 故障恢复
> **Author**: opc_uname | **Commit**: [pending]
> **铁律**: 只改HM2不改HM1 ✓ (本轮在HM2上修复mihomo自启, 未触碰HM1)

---

## 📌 本轮性质说明

本轮**不是参数调优**(未动 UPSTREAM_TIMEOUT/BUDGET 等任何调优knob), 而是HM2整机重启后的**故障恢复**:
HM2 离线70+min(R287-R290记录)后于 15:57(本地) 重启恢复, 但 mihomo 代理未随开机自启, 导致 hm40006→NVCF 上游全断。本轮修复 mihomo 自启机制并端到端验证。

## 🚨 根因 (数据驱动)

### HM2 主机层
```
who -b:        system boot 2026-06-29 15:57 (本地)  ← 整机重启
uptime:        up 23 min (诊断时)
dmesg:         [271.882] enp12s0: Link is Up - 100Mbps  ← 开机271s网卡才起
kernel:        5.15.0-181 → 5.15.0-185 (升级, 疑伴随重启)
```

### mihomo 未自启 (关键故障)
```
ps:            无 mihomo 进程
ss -tlnp:      7894-7899 全部无监听
/dev/tcp test: 127.0.0.1:7894 → Connection refused
systemctl --user is-enabled mihomo.service → disabled  ← 根因: 从未enable
Linger:        yes (user manager 开机自启条件满足, 但unit本身disabled)
```

### 故障窗口影响 (hm_tier_attempts, UTC)
```
08:01-08:23 (本地16:01-16:23): NVCFPexecProxyConnectionError 172次
  + NVCFPexecgaierror 1, empty_200 1
08:01 每分钟 3-11 个错误, 持续 22 分钟
mihomo 拉起(16:21本地)之后: 新错误 = 0  (22min零新错误)
```

## 🔧 修复操作 (HM2上执行)

### Step 1: 启动 mihomo 恢复服务
```
nohup ~/.local/bin/mihomo -d ~/.config/mihomo → 临时拉起
端口 7894-7899 全部 LISTEN
```

### Step 2: 切换为 systemd 管理 + enable 自启 (永久修复)
```
systemctl --user daemon-reload
systemctl --user enable  mihomo.service   → Created symlink default.target.wants/mihomo.service
systemctl --user start  mihomo.service
systemctl --user is-active mihomo.service → active
systemctl --user is-enabled mihomo.service → enabled  ← 永久修复: 下次重启自动起
```

### Step 3: 端到端验证
```
per-key 代理出口 (curl NVCF /v1/models):
  7894 → http=200 0.53s   (US-NV-K1)
  7895 → http=200 1.92s   (US-NV-K2)
  7897 → http=200 1.06s   (US-NV-K4)
  7899 → http=200 0.52s   (US-NV-K5)
  (7896=K3 留空, hm40006 HM_NV_PROXY_URL3=空 → key3 直连, 设计如此)

端到端经 hm40006 真实请求:
  POST :40006/v1/chat/completions model=glm5.1_hm_nv
  → HTTP 200, model=z-ai/glm-5.1, 1.01s, 正常返回

mihomo 实时日志确认真实NVCF流量:
  172.18.0.8(hm40006) --> api.nvcf.nvidia.com:443 using US-NV-K1/K4/K5
```

## 📊 当前 HM2 全栈状态 (修复后)

| 层 | 组件 | 状态 |
|---|---|---|
| 主机 | load/mem/disk | 0.45 / 2.5G/7.6G / 21% ✓ |
| 容器 | hm40006 | Up 21min (healthy) ✓ |
| 容器 | cc_postgres | Up 21min (healthy) ✓ |
| 容器 | auth_to_api_4000x | 全 healthy ✓ |
| 服务 | hermes-gateway.service (user) | active running ✓ |
| 服务 | hermes-dashboard.service (user) | active running ✓ |
| 服务 | mihomo.service (user) | **active + enabled** ✓ (本轮修复) |
| timer | hermes_alt_optimize.timer | active waiting ✓ |
| 链路 | hm40006→NVCF 端到端 | 200, 1.01s ✓ |

### 调优参数现状 (本轮未改动, 维持R290)
```
UPSTREAM_TIMEOUT=70  TIER_TIMEOUT_BUDGET_S=128  MIN_OUTBOUND_INTERVAL_S=13
KEY_COOLDOWN_S=38  TIER_COOLDOWN_S=22  HM_CONNECT_RESERVE_S=22
HM_NV_MODEL_TIERS=["glm5.1_hm_nv"]
```

## ⚠️ 遗留观察项 (非本轮范围, 记录待后续)

1. **mihomo 订阅 provider 拉取 403 Forbidden** (`nv-us-provider`, `pq-provider`)
   - 节点已从 cache.db 加载, 代理转发正常, 不影响当前链路
   - 但订阅无法更新, 长期可能导致节点失效。建议后续轮次排查订阅链接。
2. **hm_tier_attempts 表名**: CLAUDE.md 文档写 `ha_requests`, 实际表为 `hm_requests`(另有 `hm_tier_attempts`)。文档需勘误。
3. **R287-R290 的"触发误判"**: R290 文件记录了 cron 在无新 HM2 commit 时仍触发的问题, 与 [[alt-optimize-duplicate-mechanism]] 相关, 待 HM2 侧后续确认。

## ✅ 验证清单

- [x] HM2 双路径可达 (Tailscale direct 192.168.1.199 + LAN)
- [x] 主机未 panic, 干净重启
- [x] 9 个容器全 healthy
- [x] hermes-gateway/dashboard active
- [x] mihomo active **且 enabled (永久自启)**
- [x] per-key 代理 4/4 通 NVCF (200)
- [x] 端到端 hm40006 真实请求 200, 1.01s
- [x] 修复后 22min 零新错误
- [x] 未触碰任何调优参数 (少改多轮)
- [x] 未触碰 HM1 (铁律)

---

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记
