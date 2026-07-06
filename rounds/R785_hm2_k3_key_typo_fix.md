# R785: HM2 K3 key 1字符录入错误修复 (根因发现)

## 摘要

**根因**: HM2 的 NVU_KEY3 在 docker-compose.yml 第54行有一个 1 字符录入错误:
位置 65 的 `v` 被写成了 `b` (`...5BcdMXv_HZry` → `...5BcdMXb_HZry`)。

这导致 HM2 的 K3 在 NVCF 上所有 invoke 都返回 403 "Authorization failed"。
**之前 R705/R780/R783 把 K3 的 403 归因于 "IP 维度特殊性" 是完全错误的** —
K3 从来不是坏 key, 也不是 IP 风控, 纯粹是 compose 文件录错了 1 个字符。

## 改前数据 (铁律: 改前必有数据)

### 1. 两机 K3 key 比对 (用户发现)
```
HM1 K3: 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  (正确)
HM2 K3: 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  (错!)
                                                                 ↑ 位置65: v→b
```
- K1/K2/K4/K5 两机 hash 完全相同 (同一把 key)
- 只有 K3 差 1 个字符

### 2. HM2 K3 行为 (修复前)
- list models: 200 (key 格式有效, NVCF 匿名 list)
- integrate chat kimi: 403 "Authorization failed"
- pexec kimi/glm5.2/dsv4p: 全 403 "Authorization failed"
- 在电信直连、美国 IP、日本 CMI 三种 IP 上都 403 → **跟 IP 无关**

### 3. 对比 K1 (同一 IP 同一时间)
- K1 电信直连 integrate kimi: 200 (1.4s)
- K1 美国 IP integrate kimi: 200 (1.2s)
- K1 在 HM1 全直连: 100% 成功

**结论**: 403 是 K3 key 字符错误导致的认证失败, 不是 IP 风控, 不是 key 过期, 不是账户无授权。

## 错误来源

`/opt/cc-infra/.env` 和 `.env.template` 里 K3 都是正确值 (`...MXv_HZry`),
但 `docker-compose.yml` 第54行直接硬编码了错误值 (`...MXb_HZry`)。
compose 的硬编码值覆盖了 .env, 所以 .env 的正确值没生效。
推测是某个 round 手动编辑 compose 时打错了 1 个字符 (v 和 b 在键盘上相邻)。

## 改动

### docker-compose.yml (HM2) 第54行
```yaml
# 修复前
- NVU_KEY3=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
# 修复后
- NVU_KEY3=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
```
sed 精确替换, backup: docker-compose.yml.bak.R785_k3fix

## 验证 (铁律: 改后必有验证)

### 1. K3 修复后直接测试 (两种 IP)
```
K3 via 美国7896 integrate kimi: HTTP 200 (2.6s)  ← 修复前是 403
K3 via 直连电信 integrate kimi: HTTP 200 (3.1s)  ← 修复前是 403
```

### 2. nv_gw 端到端 (kimi_nv 多次请求触发 rr 轮换)
```
nv_key_idx | egress_route | egress_ip      | status | duration_ms
-----------+--------------+----------------+--------+-------------
     2     | mihomo-7896  | 134.195.101.195| 200    | 963    ← K3 修复!
     1     | direct       | 218.93.250.242 | 200    | 991
     0     | mihomo-7894  | 134.195.101.193| 200    | 807
     4     | mihomo-7899  | 134.195.101.180| 200    | 1105
     3     | mihomo-7897  | 103.62.49.162  | 200    | 4593
```
全 5 key 200 成功, K3 (key_idx=2) 现在正常工作。

## 重新审视之前的错误结论

以下结论基于 "K3 是坏 key / IP 风控" 的错误前提, 现在全部推翻:

1. **R705 "HM2 mihomo 5 出口打 NVCF 全 timeout, 直连秒回"** — 错。K3 的 403 是 key 字符
   错误, 不是 IP 被 block。其他 4 key 在各种 IP 都通。
2. **R705 "CMI 103.62.49.x 全 block"** — 错。R784 已证明 CMI 103.62.49.162 能访问 NVCF
   (K4 走 CMI 9/9 成功)。
3. **R780/R783 "K3 在 HM2 美国 IP 全 403 是 IP 维度特殊性"** — 错。是 key 字符错误。
4. **R783 "K3 403 快速失败 + cooldown 不影响整体, 维持现状"** — 错。K3 应该修, 不是维持。
5. **"5 key 风控跟 IP 有关, 需要 mihomo 多 IP"** — 错。K1/K2/K4/K5 在电信直连和美国 IP
   都 200, IP 不是风控因素。HM1 全直连 100% 成功就是证据。

## 正确的结论

1. **5 个 NV key 的风控跟 IP 无关** — 电信直连、美国 IP、日本 CMI 对正常 key 都可用。
2. **mihomo 美国代理不是必需的** — HM1 全直连证明电信直连可行。HM2 保留 mihomo 是
   R784 A/B 观察配置 (用户要求), 不是因为 IP 风控。
3. **K3 跟其他 4 key 无本质区别** — 修复字符错误后, K3 在两种 IP 都 200, 跟 K1 一样。
4. **key 字符必须逐字符核对** — 1 个字符错误就能让 key 看起来像 "坏了", 而实际只是
   录入错误。改前必有数据 → 数据要包含 "两机 key 逐字符比对" 这一步。

## 教训 (写给未来)

- 当一个 key "list 200 但 invoke 403" 时, **首先怀疑 key 字符错误**, 不是 IP 或账户授权。
- 核对 key 不能只看 hash 或长度, 要**逐字符 diff** (hash 不同就一定有字符差异)。
- compose 里硬编码 secret 容易出错, 应该用 .env 引用 (本轮后建议改用 .env)。
- "IP 风控" 是个容易自圆其说的解释, 但必须有 "同一 IP 不同 key 行为不同" 的反例才能证明
  是 IP 问题。本轮 K1 (200) vs K3 (403) 同一 IP 就是反例 → 推翻 IP 风控论。

## Follow-up
- **HM2 compose 改用 .env 引用 key** (避免硬编码字符错误, .env 已是正确值)
- **核查其他 round 是否也基于 K3 坏掉的前提** (R705/R780/R783 的部分结论需修正)
- **HM1 同步**: 用户明确暂不动

## 回滚
```bash
cd /opt/cc-infra && cp docker-compose.yml.bak.R785_k3fix docker-compose.yml
docker compose up -d nv_gw
# (但不会回滚 — 这是 bug 修复, 不是参数调优)
```
