# R550 (HM1): 三agent链路可调空间评估 + NVCF动态surge发现 (非参数优化, 数据评估轮)

## 背景
用户要求评估 openclaw/opencode 两机互相优化是否值得做。本轮纯数据评估,不改代码。

## 数据结论: 三 agent 链路可调空间

### HM1 近6h DB (host_machine=opcsname, 两机各自独立DB不共享)

| agent | model | 6h req | SR | P95 | 可调空间 |
|---|---|---|---|---|---|
| hermes | kimi_nv | 1673 | **81.23%** | 95s | 参数天花板(详见下) |
| openclaw | dsv4p_nv | 2715 | 99.26% | 33s | **无** (已最优) |
| opencode | glm5_1_nv | 1 | 100% | - | **无数据** (流量极低) |

### kimi_nv 失败解剖 (6h, 314次失败)
- 100% `all_tiers_exhausted` (error_subcategory=all_tiers_failed_in_mapped_tier), P50=75s
- 5 个本地 key 各 100% SR (k0-k4 各 262-270 req 全 ok)
- 失败集中在 `nv_key_idx=NULL` (349 req, SR=10%) = peer fallback 路径 (打 HM2 对端, key_idx 未记)
- **本地5key全健康, 失败=peer fallback 也失败** (HM2 同 surge)

### peer fallback 实测: 6h 零成功
- 所有 model 的 `fallback_occurred=True` 计数 = 0 (从未触发成功)
- `fallback_actually_attempted=True` = 0
- 原因: R503 后 tier_order=[mapped_model] 单元素, 删了跨 tier ring fallback; peer fallback 触发条件=all_tiers_exhausted, 但对端 HM2 同样 surge → 互备失败
- 跨机互备在 NVCF 平台侧 surge (非主机故障) 时**完全无效**

## ★ NVCF 动态 surge 发现 (反转)

### 6h 历史数据 vs 实时探测对比
- 6h 历史: kimi_nv SR=81% (surge), dsv4p_nv SR=99.26% (健康)
- 实时探测 (R550 时刻):
  - kimi_nv: 5/5 成功 (3次thinking 8-9.5s rc500tok + 2次轻请求 1.8s) ✅
  - dsv4p_nv: 3/3 失败 (111s timeout 502) ❌
- **surge 已从 kimi 轮换到 dsv4p**

### 关键结论
NVCF function 元数据 status 都是 ACTIVE (监控脚本 09:25/09:35/09:45/09:55 全报 ACTIVE),
但实际推理可用性动态轮换。**静态路由 + 静态参数 无法应对动态 surge**。
这解释了 hermes loop R547/R549 为何全 NOP (参数调不动平台侧动态 surge)。

## 改进方向评估 (不做, 仅记录)

### 方向A: hm40006 加 function 健康度感知动态路由 ★推荐
- 机制: 单 agent 首选 function 连续失败时, 自动 fallback 到另一个健康 function (跨 function 同 model, 或跨 model)
- 当前问题: R503 删了跨 tier fallback (tier_order=[mapped_model]), 单 function surge → 全挂
- 收益: kimi surge 时 hermes 可临时走 dsv4p; dsv4p surge 时 opencode 可临时走 kimi
- 风险: 跨 model fallback 违反"各 agent 各后端语义" (hermes→kimi 的 thinking 产出 vs dsv4p 的差异)
- 实现复杂度: 中 (需加 function 健康度计数器 + fallback 触发逻辑 + 恢复回切)
- 违反"每轮少改"铁律: 是 (架构级改动, 非单参数)

### 方向B: 保持现状, 接受 NVCF 动态 surge 不可解
- 理由: surge 是 NVCF 平台侧, 不在我方控制范围
- hermes loop 已到参数天花板, R547/R549 全 NOP 是正确判断
- openclaw 99.26% 已最优, opencode 流量极低
- 代价: kimi 或 dsv4p 任一 surge 时, 对应 agent 挂到 surge 结束 (~小时级)

### 方向C: 给 openclaw/opencode 搭互相优化 loop
- 数据否决: openclaw 已99%+ (无空间), opencode 流量极低 (无样本)
- 不值得做

## 本轮结论
1. **hermes 互相优化 loop 继续跑是对的** (R549 刚过), 它已到参数天花板, 失败是 NVCF surge 不可解
2. **openclaw/opencode 互相优化不值得做** (数据证伪)
3. **真正的瓶颈是 NVCF 动态 surge**, 唯一可能解的是方向A (动态路由), 但是架构级改动, 需用户决策
4. 本轮不改任何代码/参数, 仅数据评估 + 记录方向

## 验证清单 (评估轮, 无改动需验证)
- [x] HM1 6h DB 三 agent SR/延迟/失败解剖 查询完成
- [x] kimi_nv 5 key 本地全 100% SR 确认 (失败=peer fallback 路径)
- [x] peer fallback 6h 零成功 确认
- [x] kimi_nv 实时探测 5/5 成功 (surge 已轮换走)
- [x] dsv4p_nv 实时探测 3/3 失败 (surge 已轮换来)
- [x] NVCF function 监控日志确认元数据全 ACTIVE (surge 非下架)

## 备份清单
无 (本轮无文件改动)

## ⏳ 轮到HM2优化HM1
