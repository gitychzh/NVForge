# R783: HM2 nv_gw 每 key 独立 IP + dsv4p_nv 误选死 function 修复

## 摘要

R782 把 5 个 NV group 都切到同一个 `🇺🇸美国01` 节点, 导致 5 个 key 共享同一出口 IP
(134.195.101.193) — 违背 R580 "每 key 独立 IP 避免 same-IP rate limit" 的设计。本轮
给 5 个 group 各配不同美国节点 (01-06), 5 key 各走不同 IP。同时修复 dsv4p_nv 的
func_health 误判: 74f02205 (实际可用) 被标记 unhealthy → 切到 8915fd28 (实际挂死,
冷启动视为健康) → dsv4p_nv 全 timeout; 修复方法是去掉挂死的 8915fd28 候选。

## 改前数据 (铁律: 改前必有数据)

### 问题 1: 5 key 共享同一 IP
R782 把 5 个 NV group 全切 `🇺🇸美国01` → 5 端口出口 IP 全是 134.195.101.193:
```
7894 -> 134.195.101.193
7895 -> 134.195.101.193
7896 -> 134.195.101.193
7897 -> 134.195.101.193
7899 -> 134.195.101.193
```
用户指出: 一个 mihomo 实例可用多个 IP 代理, 不该所有 key 走同一 IP。

### 问题 2: dsv4p_nv 误选死 function
```
[NV-FUNC-HEALTH] model=dsv4p_nv primary=74f02205... unhealthy → switched to 8915fd28...
[12:25:48.3] [NV-KEY] tier=dsv4p_nv attempt 1/7: k1 → NVCF pexec 8915fd28... via socks 7894
(20s timeout, 8915fd28 实际挂死)
```
- K1 直测 74f02205 → HTTP 200 4.8s (实际可用!)
- K1 直测 8915fd28 → 20s timeout (实际挂死)
- func_health: 74f02205 历史失败累积 >5 样本, 成功率 <0.80 → unhealthy
- 8915fd28 冷启动 (样本 <5) → 视为健康 1.0 → 被选为首选
- 恶性循环: 8915fd28 每次失败 20s, 累积慢, 期间 dsv4p_nv 全 timeout

### K3 在 HM1 本机与别的 key 完全一致 (用户确认)
HM1 true-direct pexec 测试 (5 key 全 200):
| key | DS pexec | GLM pexec |
|---|---|---|
| K1 | 200 3.3s | 200 6.4s |
| K2 | 200 9.5s | 200 5.2s |
| K3 | 200 1.7s | 200 2.8s |
| K4 | 200 5.3s | 200 5.4s |
| K5 | 200 12.9s | 200 9.3s |
**K3 与别的 key 无任何区别, 甚至最快。HM2 上 K3 403 是 IP 维度特殊性 (HM2 可用出口
恰好落在 NVCF 对 K3 的封锁区间), 不是 key 问题。**

## 参数表

| 参数 | 改前 | 改后 | 文件 |
|---|---|---|---|
| ♻️US-NV-K1..K5 节点 | 全指向美国01 (同 IP) | 各指向美国01-06 (5 不同 IP) | mihomo API |
| dsv4p_nv function_ids | [74f02205, 8915fd28] | [74f02205] (去掉挂死备选) | config.py |
| TIER_TIMEOUT_BUDGET_S | 40 (R782) | 60 (glm5_2_nv thinking 需要更长) | docker-compose.yml |

## 改动详情

### 改动 1: 5 个 NV group 各配不同美国节点 (mihomo API + store-selected 持久化)
```bash
SECRET="set-your-secret"
declare -A MAP=(
  ["♻️US-NV-K1"]="🇺🇸美国01-0.1倍 | 电信联通移动推荐"   # 134.195.101.193
  ["♻️US-NV-K2"]="🇺🇸美国02-0.1倍 | 电信联通移动推荐"   # 134.195.101.194
  ["♻️US-NV-K3"]="🇺🇸美国03-0.1倍 | 电信联通移动推荐"   # 134.195.101.195
  ["♻️US-NV-K4"]="🇺🇸美国04-0.1倍 | 电信联通移动推荐"   # 134.195.101.197
  ["♻️US-NV-K5"]="🇺🇸美国06-0.1倍 | 电信联通移动推荐"   # 134.195.101.180 (05 挂了用 06)
)
```
- mihomo config.yaml 已有 `profile: store-selected: true` → selector 选择持久化到
  cache.db, 重启不丢 (已验证: restart mihomo 后 5 group 选择完全保留)
- 兜底脚本 `scripts/nv_proxy_selector.sh` 部署到 `/home/opc2_uname/bin/`, cache.db
  丢失时手动跑一次恢复

### 改动 2: dsv4p_nv 去掉挂死备选 function (config.py)
文件: `/opt/cc-infra/proxy/nv-gw/gateway/config.py` (bind-mount, restart 不 rebuild)

改前:
```python
"function_ids": [os.environ.get("NVCF_DEEPSEEK_FUNCTION_ID",
                                "74f02205-c7ba-438f-b81a-2537955bd7ec"),
                 "8915fd28-fe8f-47d6-a35d-d745d78b35d5"],
```
改后:
```python
"function_ids": [os.environ.get("NVCF_DEEPSEEK_FUNCTION_ID",
                                "74f02205-c7ba-438f-b81a-2537955bd7ec")],
```
理由: 8915fd28 (sglang 备选) 长期 surge 挂死, func_health 冷启动误判为健康选它,
导致 dsv4p_nv 全 20s timeout。去掉后 nv_gw 只用 74f02205 (实际 ACTIVE 可用)。
若 74f02205 未来真的 surge, func_health 全挂会返 all_tiers_exhausted, 41xx 切 ms_gw
兜底 (比误选挂死 function 强)。

### 改动 3: TIER_TIMEOUT_BUDGET_S 40→60
R782 从 110 降到 40 太激进, glm5_2_nv thinking 请求 (inject chat_template_kwargs
enable_thinking) 首字节 8-30s, 40s budget 只够 1 次 thinking attempt, 偶发 timeout。
60s 能覆盖 1-2 次 thinking attempt, 又不会像 110 那样浪费 (非 thinking 请求 1-5s)。

## 改后验证 (铁律: 改后必有验证)

### 1. 5 key 各走不同 IP
```
7894 (K1) -> 134.195.101.193
7895 (K2) -> 134.195.101.194
7896 (K3) -> 134.195.101.195
7897 (K4) -> 134.195.101.197
7899 (K5) -> 134.195.101.180
```

### 2. 三模型端到端 (各 2 次, 全 200)
| 模型 | try1 | try2 |
|---|---|---|
| glm5_2_nv | 200 8.6s | 200 4.1s |
| dsv4p_nv | 200 11.2s | 200 3.2s |
| kimi_nv | 200 1.5s | 200 1.4s |

### 3. 41xx 适配器端到端
| 适配器 | 模型 | 结果 |
|---|---|---|
| opclaw4103 | glm5_2_nv | 200 (thinking 长输出) |
| hm4104 | dsv4p_nv | 200 4.7s |
| oc4105 | kimi_nv | 200 1.2s |

### 4. nv_gw 日志: 不再误选 8915fd28
```
[12:35:32.2] [NV-CYCLE] tier=glm5_2_nv k3 → 403, cycling to next key
[12:35:35.5] [NV-SUCCESS] tier=glm5_2_nv k4 succeeded after 1 cycle attempts
[12:35:46.7] [NV-SUCCESS] tier=dsv4p_nv k4 succeeded on first attempt  ← 用 74f02205, 不再误选 8915fd28
[12:36:57.6] [NV-SUCCESS] tier=dsv4p_nv k1 succeeded on first attempt
```
- K3 403 快速 cycle 到 K4 → 成功 (cooldown 机制正常)
- K1/K4/K5 各走不同 socks 端口 → 不同 IP
- dsv4p_nv 全部 `succeeded on first attempt` (不再 func_health 误判)

## K3 结论 (用户确认: 不调整 K3)
- HM1 本机 5 key 全 200, K3 甚至最快 → K3 与别的 key 无本质区别
- HM2 任何可用美国节点 K3 都 403 (134.195.101.x 段对 K3 不友好) — IP 维度特殊性
- K3 403 快速失败 (0.55-1s), KEY_AUTHFAIL_COOLDOWN_S=60 跳过, 不拖累其他 4 key
- 维持 R780 60s cooldown, 不改 K3 配置

## 预期效果
- 5 key 各走不同 IP, 避免 same-IP rate limit (R580 设计恢复)
- dsv4p_nv 不再误选挂死 function, 首次尝试即成功
- glm5_2_nv thinking 请求有足够 budget (60s)
- K3 维持 403 快速失败 + cooldown, 不影响整体

## 未做 / Follow-up
- **func_health 冷启动误判**: 8915fd28 冷启动视为健康被误选的根因是 MIN_SAMPLES=5
  + 冷启动返回 1.0。可考虑冷启动返回 0.5 或对备选 function 更保守。本轮用去掉死候选
  绕过, 根因修复下轮。
- **mihomo @reboot 脚本**: store-selected 已持久化 (验证通过), 但加个 @reboot 跑
  nv_proxy_selector.sh --check 兜底 (可选)
- **HM1 同步**: 用户明确暂不动

## 回滚
```bash
# config.py
cp /opt/cc-infra/proxy/nv-gw/gateway/config.py.bak.R782 /opt/cc-infra/proxy/nv-gw/gateway/config.py
docker restart nv_gw
# compose
cd /opt/cc-infra && sed -i 's|TIER_TIMEOUT_BUDGET_S=60|TIER_TIMEOUT_BUDGET_S=40|' docker-compose.yml
docker compose up -d nv_gw
# mihomo: 脚本 nv_proxy_selector.sh 可切回, 或手动切
```

## 不改的东西 (铁律: 聚焦)
- HM1 任何配置 (用户: 暂不动)
- K3 key 配置 (用户: 不调整, 与别的 key 无区别)
- ms_gw (兜底后端, 不动)
- 41xx 适配器 (timeout 维持, nv_gw 快速失败后自然快速切 fallback)
