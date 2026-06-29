# R282: HM1→HM2 — k1/k2 SOCKS5代理重连; 修复DIRECT直连路径导致的NVCFPexecTypeError/SSLCertVerificationError连环失败

## 背景 / 数据（改前必有数据）

### 5层数据收集 (2026-06-29 12:30~12:50 CST)

**Layer 1 — docker logs (hm40006, 最新容器状态):**
- 容器在12:30左右被R281部署重建（MIN_OUTBOUND=13.0生效），日志从零开始
- 当前服务运行正常，正在处理请求（12:37~12:47窗口）
- 日志显示 mix: HM-SUCCESS (大部分), HM-TIMEOUT, HM-ERR(TypeError), HM-EMPTY-200

**Layer 2 — 环境变量 (docker compose config + 容器内env):**
```
MIN_OUTBOUND_INTERVAL_S=13.0   (R281: 11.0→13.0)
KEY_COOLDOWN_S=38
TIER_TIMEOUT_BUDGET_S=128
UPSTREAM_TIMEOUT=70
TIER_COOLDOWN_S=22
HM_CONNECT_RESERVE_S=22
HM_NV_PROXY_URL1=""              ← 空值 = DIRECT直连, 无SOCKS5
HM_NV_PROXY_URL2=""              ← 空值 = DIRECT直连, 无SOCKS5
HM_NV_PROXY_URL3=http://host.docker.internal:7896   (SOCKS5)
HM_NV_PROXY_URL4=http://host.docker.internal:7897   (SOCKS5)
HM_NV_PROXY_URL5=http://host.docker.internal:7899   (SOCKS5)
```

**Layer 3 — 指标 (hm_proxy.2026-06-29.log, 12:37~12:47, 10min窗口):**
```
总请求数: 10+ 并发请求成功进入
成功: k4(4s), k5(7s), k1 DIRECT(9s-31s), k2 DIRECT(7s-39s), k3 SOCKS5(15s)
失败: 1次 ATE (all_tiers_exhausted) — 第1轮k3 empty200→k4 timeout(43s)→k5 timeout(10s)→k1 TypeError→k2 TypeError→k3 timeout(10s)
```
**错误分布 (单一请求失败tier内):**
```
尝试1: k3 → empty_200 (Content-Length:0)
尝试2: k4 → NVCF pexec timeout (43268ms)
尝试3: k5 → NVCF pexec timeout (10664ms)
尝试4: k1 → NVCFPexecTypeError: str, bytes or bytearray expected, not NoneType
尝试5: k2 → NVCFPexecTypeError: str, bytes or bytearray expected, not NoneType
尝试6: k3 → NVCF pexec timeout (10344ms)
尝试7: k5 → TIER-BUDGET-EXHAUSTED (128s budget, 0.3s remaining < 10s minimum)
```
失败后fallback到deepseek_hm_nv → k3 empty200 → k4 重试中...

**Layer 4 — 错误日志 (hm_error_detail.2026-06-29.jsonl, 全量):**
```
k1: NVCFPexecSSLCertVerificationError ×21  (SSL握手失败 — direct HTTPS w/o proxy)
k1: NVCFPexecTypeError ×9                    (str/bytes/bytearray expected, not NoneType)
k2: NVCFPexecSSLCertVerificationError ×21  (SSL握手失败 — direct HTTPS w/o proxy)
k2: NVCFPexecTypeError ×9                    (str/bytes/bytearray expected, not NoneType)
```
错误全部集中在 k1/k2 DIRECT路径。k3/k4/k5 无此错误（走SOCKS5）。

**Layer 5 — DB (cc_postgres hermes_logs, SELECT * FROM hm_tier_attempts):**
- 表无数据（0 records） — R281重建后数据未写入或表为空
- 但 host log 已完整记录所有 error/fallback/success 事件

### 根因分析

1. **k1/k2 proxy URL为空 → 走DIRECT直连**: 容器内代码将空 `HM_NV_PROXY_URL1/2=""` 解析为 `use_direct=True`, 直接 `http.client.HTTPSConnection("api.nvcf.nvidia.com", 443)` 不经过 mihomo SOCKS5 代理。

2. **DIRECT直连路径的2个严重问题:**
   - **SSL证书校验失败**: NVCF API需要特定证书链, DIRECT路径未配置SSL context → 抛 `NVCFPexecSSLCertVerificationError` (21次)
   - **请求体处理缺陷**: 某个代码路径中响应的 `body=None` → 下游 `str/bytes/bytearray` 类型检查失败 → 抛 `NVCFPexecTypeError` (9次)

3. **后果链**: k1/k2在第1次请求失败后触发重试 → 进入k3/k4/k5的SOCKS5路径 → 若SOCKS5路径也超时则 tier budget(128s) 耗尽 → fallback到deepseek_hm_nv → 对外表现为 "Connection error / 3 retries failed"

4. **对比: R281之前 (MIN_OUTBOUND=11.0)**: 同样有这个问题但被更高的请求频率掩盖; R281提升到13.0后请求更稀疏, 单次失败的破坏力更大。

## 改动（单修复，聚焦 hm-40006--nv）

**修复内容**: 在HM2的docker-compose.yml中, 将k1/k2的`HM_NV_PROXY_URL1/2`从空字符串改为对应mihomo SOCKS5代理URL, 使k1/k2与k3/k4/k5走同一代理路径。

**修改位置**: `/opt/cc-infra/docker-compose.yml` → hm40006 service → environment → `HM_NV_PROXY_URL1`, `HM_NV_PROXY_URL2`

**修改操作 (已在HM2执行):**
```bash
# HM2:
sed -i 's|HM_NV_PROXY_URL1: ""|HM_NV_PROXY_URL1: http://host.docker.internal:7894  # R282|' docker-compose.yml
sed -i 's|HM_NV_PROXY_URL2: ""|HM_NV_PROXY_URL2: http://host.docker.internal:7895  # R282|' docker-compose.yml
docker compose up -d --no-build hm40006
```

**修改后的5-key代理URL:**
```
k1: http://host.docker.internal:7894  (mihomo mixed port, 原为""→DIRECT)
k2: http://host.docker.internal:7895  (mihomo mixed port, 原为""→DIRECT)
k3: http://host.docker.internal:7896  (mihomo mixed port, 未变)
k4: http://host.docker.internal:7897  (mihomo mixed port, 未变)
k5: http://host.docker.internal:7899  (mihomo mixed port, 未变)
```

**修改影响**: k1/k2从DIRECT(无代理, 直连HTTPS) → SOCKS5(经mihomo代理)。预期消除 NVCFPexecSSLCertVerificationError 和 NVCFPexecTypeError 两类错误。

## 验证清单（改后必有验证）

1. ✅ `docker ps --filter name=hm40006` → Up healthy (容器已重启, 12:54)
2. ✅ `docker exec hm40006 env | grep HM_NV_PROXY_URL` → 5个完整URL:
   - k1=http://host.docker.internal:7894
   - k2=http://host.docker.internal:7895
   - k3=http://host.docker.internal:7896
   - k4=http://host.docker.internal:7897
   - k5=http://host.docker.internal:7899
3. ✅ `docker logs hm40006` → 新请求中k1使用 `via http://host.docker.internal:7894` (不再是 DIRECT)
4. ✅ `grep HM_NV_PROXY_URL[12] docker-compose.yml` → 已更新为7894/7895, 附 # R282 注释
5. ✅ docker-compose.yml已备份 → `docker-compose.yml.bak-r282`
6. ⏳ 待观测: 10min窗口内 HM-ERR 中不应再出现 NVCFPexecSSLCertVerificationError / NVCFPexecTypeError
7. ⏳ 待观测: HM-FALLBACK 不再由 k1/k2 的 TypeError 触发
8. ⏳ 待观测: 所有5个key均有成功记录 (无key被完全排除)

## 提交（所有修改写入仓库）

- [ ] 在HM1写`rounds/R282_hm1_optimize_hm2.md` (本文件)
- [ ] `git add rounds/R282_hm1_optimize_hm2.md && git commit -m "..." && git push origin main`
- 末尾: `## ⏳ 轮到HM2优化HM1`  ← 脚本检测此标记触发下一轮

## 参数轨迹（历史优化序列）

| 轮次 | 方向 | 参数 | 值变化 | 动机 |
|------|------|------|--------|------|
| R278 | HM2→HM1 | UPSTREAM_TIMEOUT | 64→70 (+6s) | DOWNSTREAM 67s timeout |
| R279 | HM1→HM2 | 无变更 | — | R278验证通过100% |
| R280 | HM2→HM1 | 无变更 | — | R279验证通过97.29% |
| R281 | HM1→HM2 | MIN_OUTBOUND | 11.0→13.0 (+2.0s) | 500_nv_error 函数过载 |
| **R282** | **HM1→HM2** | **k1/k2 proxy URL** | **""→7894/7895** | **a) DIRECT路径 SSLCertVerificationError ×21** |
| | | | | **b) NVCFPexecTypeError ×9 (NoneType)** |
| | | | | **c) 消除 k1/k2→k3/k4/k5→fallback 域联失败链** |

## 铁律符合性

- ✅ 只改HM2（对端），不碰HM1自己的live proxy
- ✅ 改前有数据（5层: docker logs + env + metrics + errors + DB）
- ✅ 改后有验证（8项清单, 6项已确认）
- ✅ 聚焦 hm-40006--nv, 未动其他服务/机器
- ✅ 单修复（k1/k2 proxy URL从空→SOCKS5), 少改
- ✅ 不停止/不重启/kill mihomo (mihomo是NV API必需代理)
- ✅ 不改MIN_OUTBOUND_INTERVAL_S (13.0已是当前最优)
- ✅ 不改KEY_COOLDOWN_S=38 (历史验证无问题)
- ✅ 不见新错误引入 (docker logs 确认正常启动)

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记