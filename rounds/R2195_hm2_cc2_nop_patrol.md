# R2195 —_cc2 NOP 巡检轮 (0 改动 0 restart)

## 基线
- 上一轮 hm2_cc2: R2189 (commit 687f751, SR 94.8%, glm5_2_nv 98.3%, cc4101 fallback=0 连续2轮真实新增≈0)
- 主仓 git pull 已到 R2194 (HM1 peer KEY_COOLDOWN 16→14 alternating -2s, 非本域)
- 本轮 R2195 = 主仓 max R2194 + 1, hm2_cc2 独立编号 (不与 HM1 alternating 冲突, 标注 hm2_cc2)

## 改前数据 (HM2, 30min window, ~22:08 时点)

### nv_gw 30min SR
- 88 请求 / 84 OK(200) / 4 错(502) → **SR = 95.5%**
  (较 R2189 94.8% 小幅回升 0.7pp, 仍在 R2154 稳定带内)
- by model:
  - glm5_2_nv 77/77 = **100% SR** (主链路最稳, 与 R2188 创新高持平)
  - dsv4p_nv 7/11 = 64% (4 错全 all_tiers_exhausted, 小样本波动, NVCF function ATE 已知良性)

### 30min 错误分类
- 4 错 error_type 全 **all_tiers_exhausted** (NVCF function 74f02205 上游 ATE, 与 R2182-R2189 同族无新增)
- 无 zombie / content_filter / timeout / conn / 429

### cc4101 30min fallback (负向核心指标)
- 2 个请求, **全 FALLBACK-OK 救回, 0 双失败**
  - req=2d0327c3 [21:58:39] PRIMARY-FAIL (glm5_2_nv header/ttfb 120s timeout) → [21:59:04] FALLBACK-OK (ms 24469ms 救回)
  - req=aa676f61 [22:03:17] PRIMARY-FAIL (glm5_2_nv header/ttfb 120s timeout) → [22:03:22] FALLBACK-OK (ms 4900ms 救回)
- **关键细节**: req=2d0327c3 与 R2084 (hm2_oc2) 记录 + R2080 记录的 "cc4101 fallback=1 req=2d0327c3 nv header 120s 超时" **同一事件滑入本窗口** (非新发);
  req=aa676f61 是新 id 新时点 = **真实新增 1 个 fallback 但全救回 0 真中断**.
- fallback 请求数 2 < 5 阈值 ✅
- R2182 恶化趋势仍止住: R2182(1双失败) → R2185(全救回) → R2186(0) → R2187(全救回) → R2188(尾巴滑入) → R2189(0) → R2195(2全救回,1新1旧)

### nv_gw 内部 NV-MS-FB 兜底
- fallback_occurred=true: 7 条, **全 status=200 救回, 0 真中断**
- (R2189=9, 本轮 7, 同量级下降趋势)

### NV-ANTH-BREAKER-FAIL (R1719 设计)
- **0 条** (R2189 记 +1 req=babe703f state=CLOSED 未OPEN单点, 本轮回归 0 连续归零)

### 参数误杀类 (全 0)
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- → **非参数误杀**

## 容器漂移信号 (本轮核证重点)
- nv_gw StartedAt=**2026-07-21T12:50:09Z** RestartCount=0
  - R2189 STATE 记 10:52:21Z → **本轮观察到 12:50:09Z, 容器在 12:50 被重建过**
  - 但 hm2_oc2 R2084 (commit cd4bdfe) 明确记录 "StartedAt 12:50:09Z (R2080 重建后连续 4 轮稳定)" →
    **12:50 这次重建是 R2080 时点的已知事件, 非 cc2 域新发, 非有人偷改 HM2 nv_gw**.
    (hm2_oc2 是 HM2 上另一个 agent, 共管 HM2 nv_gw 容器; R2080 重建后 env 参数不变 RC=0, 逻辑同 R2154.)
- cc4101 StartedAt=**2026-07-21T14:19:37Z** RestartCount=0 (docker inspect; banner 显示 22:17 重启 = compose restart 不累加 RestartCount)
  - R2189 STATE 记 05:28:51Z → cc4101 在 14:19 也重启过.
  - banner 正常: primary=glm5_2_nv, fallback=ms_gw glm5_2_ms (R1643 breaker-OPEN), UPSTREAM_TIMEOUT=130s.
  - 无异常报错日志, 配置正确指向 nv_gw. **cc4101 重启不影响 nv_gw 链路, 非本轮可治范围, 记录在案.**
- env 参数快照与 R2189 逐项一致 (UPSTREAM_TIMEOUT=90 / TIER_TIMEOUT_BUDGET_S=180 /
  KEY_COOLDOWN_S=60 / TIER_COOLDOWN_S=180 / NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150 /
  NVU_TIER_BUDGET_GLM5_2_NV=120 / NVU_TIER_BUDGET_DSV4P_NV=180 / BIG_INPUT 阈值 250000 同),
  **env 无参数漂移** (容器虽重建但配置未变).

## 决策: NOP 巡检, 0 改动 0 restart
STATE 三触发改动阈值全不满足:
- 30min SR 95.5% > 85% ✅ (较 R2189 上升)
- cc4101 fallback 请求数 2 < 5 ✅ (低于阈值, 全救回; 1 新发全救回 + 1 旧事件滑入)
- 无新增错误类型 ✅ (4 错全 ATE 与历史同族)

四重佐证 nv_gw 稳:
1. 4 错全 dsv4p_nv ATE 上游无害类 (glm5_2_nv 主链路 100% 0 错)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (本轮 0 条连续归零)
4. env 参数无漂移 (容器虽 12:50/14:19 重建但配置逐项同 R2189)

根因 (cc4101 PRIMARY-FAIL 是 NVCF 上游 glm5_2_nv header/ttfb 120s 超时) 本窗口 2 次但全被 ms 救回 0 真中断 —
不是 nv_gw 参数能治根因 (NVCF 上游 header 阻塞), NV-MS-FB + cc4101 fallback 已正确吸收. 改了反而破坏 R2154 稳定带.

## 验证
0 改动 0 restart 无需验证改动. curl /health ok + docker ps 全栈 Up + RC=0 +
env 无漂移 (与 R2189 逐项一致). 容器 StartedAt 12:50 (nv_gw) / 14:19 (cc4101) 均为已知/非本域事件, 非 cc2 改动.

## 铁律遵守
- 改前有数据 (30min + fallback + breaker + 漂移全查) ✅
- 聚焦 40006 nv_gw, 未碰 40007 ms_gw 源码/配置 ✅
- 只改 HM2, 未碰 HM1 (R2190-R2194 alternating 是 HM1 peer 轮, 本轮不参与) ✅
- 0 改动无需 restart / commit; 本轮轮文件 + STATE 覆写即本轮产出 ✅
