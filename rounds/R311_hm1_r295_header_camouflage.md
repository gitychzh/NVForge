# R311: HM1 移植 R295 HTTP 头伪装 (authorized self-change)

**Role**: HM1 (opc_uname) — 功能移植 (非交替优化轮; 用户授权本轮仅设置HM1)
**Timestamp**: 2026-06-29 22:50 CST
**Change**: 把 HM2 R295 的 NVCF 指纹风控绕过头伪装功能移植到 HM1, **全 key 生效**
**Category**: 风控对抗/功能补齐
**前轮**: R310 (HM1 gateway 模块化)

> 本轮不属交替优化序列, 是用户授权的 HM1 自身功能补齐
> ([[iron-rule-interpretation]] 授权破例自改边界). 不碰 HM2 任何东西.
> 铁律破例依据: 用户明确 "在本机hm1也添加相应的功能代码".

## 1. 目标
HM2 侧 hm40006 对 key1/key5 注入 6 个伪装 HTTP 头 (User-Agent 浏览器、
Origin/Referer 伪造 build.nvidia.com 来源、X-Requested-With、Accept-Language、Accept),
注释 `# R295: HTTP header camouflage for NVCF fingerprint bypass`, 目的绕 NVCF 指纹风控.
HM1 无此代码. 用户要求把该功能移植到 HM1.

## 2. 改前数据(改前必有数据)
- 取 HM2 真实源码 `/opt/cc-infra/proxy/hm-proxy/gateway/upstream.py:266-279` (SSH 实读, 非凭记忆):
  ```python
  # R295: HTTP header camouflage for NVCF fingerprint bypass
  hdr_extra = {}
  if key_idx in (0, 4):   # HM2: k1/k5 (=HM2 上走 mihomo 的 key)
      hdr_extra = {User-Agent, Accept-Language, Accept, X-Requested-With, Origin, Referer}
  headers_out = {标准4头, **hdr_extra}
  ```
- HM1 改前 `upstream.py:172-177` headers_out 仅 4 标准头 (Content-Type/Authorization/Content-Length/Connection:close). 全量扫 User-Agent/Origin/camouflage/伪装 0 命中.
- **关键差异**: HM2 `if key_idx in (0,4)` 选 k1/k5 是因为 HM2 上 k1/k5 恰好走 mihomo. HM1 路由不同 (k1/k3/k5 走 mihomo, k2/k4 直连). 字面照搬 k1/k5 会让 HM1 的 k3(也走代理)不伪装, 行为不一致.

## 3. 决策(问用户)
用户选 **全部 key 都伪装** (k1-k5 全注入, 最大化伪装). 故 HM1 实现为**无条件**注入
(去掉 `if key_idx in (0,4)` 守卫), 比 HM2 更激进, 但符合用户明确意图.

## 4. 改动(单一逻辑变更, 铁律每轮少改)
`/opt/cc-infra/proxy/hm-proxy/gateway/upstream.py` headers_out 构造处 (原 L172-177):
```python
# R295-port (HM1 self-change, authorized): HTTP header camouflage for NVCF
# fingerprint bypass. Ported from HM2 R295. HM2 applies to key_idx in (0,4)
# (k1/k5 = mihomo-proxied on HM2). On HM1 user elected ALL keys (k1-k5) →
# unconditional, no key_idx guard. Mirrors HM2's exact 6 headers.
hdr_extra = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://build.nvidia.com",
    "Referer": "https://build.nvidia.com/explore/discover",
}
headers_out = {4标准头, **hdr_extra}
```
6 个头键值与 HM2 逐字一致 (Origin/Referer URL、UA 串、Accept 值全同).
**仅此一处改动**, 其余路由/超时/冷却/DB 全不动.

## 5. 改后验证(改后必有验证)
1. **语法**: `ast.parse` OK ✅
2. **AST 验证**: 容器内确认 headers_out 字典含 6 伪装头键
   `['User-Agent','Accept-Language','Accept','X-Requested-With','Origin','Referer']` ✅
3. **rebuild + up**: gateway 源码未挂载 → `docker compose build hm40006 && up -d hm40006`.
   首次 build 失败 (`ghcr.io EOF` 间歇 reset, 铁律6网络问题), 直连恢复后重试 build 成功 ✅
4. **health**: `{"status":"ok", hm_num_keys:5, ...}` ✅
5. **伪装头真发出(关键)**: 临时加 `_log("HM-HDR-VERIFY", ...)` 打印 `headers_out.keys()`,
   rebuild, 发请求, 日志确认 k1+k2 均发出 10 头 (4标准+6伪装) ✅.
   验证后**删除**该临时日志, 最终 rebuild 回到干净状态 (grep HM-HDR-VERIFY=0, R295-port=1) ✅
6. **功能不破**: 最终请求 `POST /v1/chat/completions deepseek_hm_nv` → HTTP 200, 16.8s, 有效 content ✅

### 验证手法说明
出站请求经 TLS (hm40006→mihomo SOCKS5→NVCF, 或直连 NVCF), tcpdump 抓不到明文 HTTP 头.
故用"临时日志打印 headers_out.keys() + 容器内 grep 源码 + AST 字典键检查"三重确认伪装头
真的进入 conn.request 的 headers 参数, 而非仅源码存在.

## 6. 回滚
备份 `upstream.py.bak.R295hm1_20260629_224706`. 任何失败 → 还原 + rebuild.

## 7. 交付
- HM1 upstream.py 增加 R295 头伪装 (全 key, 6 头, 与 HM2 逐字一致)
- 端到端验证报告 (本文件 §5)
- 仓库: `deploy_artifacts/hm1_gateway_R311_camouflage/upstream.py`

## 8. 参数表(本轮未动)
| 参数 | 值 | 说明 |
|---|---|---|
| 路由 | k1/k3/k5=mihomo(7894/7896/7899), k2/k4=DIRECT | 不变 (R310 已恢复) |
| TIER_TIMEOUT_BUDGET_S | 182 | 不变 |
| UPSTREAM_TIMEOUT | 64 | 不变 |
| 头伪装 | k1-k5 全注入 6 伪装头 | **本轮新增** |

## ⏳ 轮到HM2优化HM1  ← 脚本检测此标记(交替优化序列恢复)
