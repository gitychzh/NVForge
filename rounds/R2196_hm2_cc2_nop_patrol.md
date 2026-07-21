# R2196 — hm2 NOP 巡检轮 (0 改动 0 restart)

## 基线
- 上一轮 hm2_cc2: R2195 (commit 318eb86, SR 95.5%, glm5_2_nv 100% 77/77 持平R2188创新高, cc4101 fallback=2全救回 1新1旧)
- 主仓 git pull 已到 R2195 (主仓最新=本轮 hm2_cc2 前序, 无 HM1 新轮)
- 本轮 R2196 = 主仓 max R2195 + 1, hm2_cc2 独立编号 (不与 HM1 alternating 冲突, 标注 hm2_cc2)
- STATE.md 停在 R2188 (上一个 session 接棒前的旧交接), 但主仓已远推到 R2195 → 以 git log 为准, 本轮续 R2196

## 改前数据 (HM2, 30min window, ~22:30 时点)

### nv_gw 30min SR
- 75 请求 / 71 OK(200) / 4 错(502) → **SR = 94.7%**
  (较 R2195 95.5% 小幅回落 0.8pp, 仍在 R2154 稳定带内波动)
- by model:
  - glm5_2_nv 64/64 = **100% SR** (主链路最稳, 连续 R2188/R2195/R2196 三轮 100%)
  - dsv4p_nv 7/11 = 64% (4 错全 all_tiers_exhausted, 小样本波动, NVCF function ATE 已知良性)

### 30min 错误分类
- 4 错 error_type 全 **all_tiers_exhausted** (NVCF function 上游 ATE, 与 R2182-R2195 同族无新增)
- 无 zombie / content_filter / timeout / conn / 429

### cc4101 30min fallback (负向核心指标)
- 1 个请求, **全 FALLBACK-OK 救回, 0 双失败**
  - req=f4c1505d [22:28:48] PRIMARY-FAIL (glm5_2_nv header/ttfb 120s timeout after 120107ms) → [22:28:56] FALLBACK-OK (ms 7664ms 救回)
- **关键细节**: req=f4c1505d 是新 id 新时点 (22:28:48, 非 R2195 记录的 2d0327c3/aa676f61) = **真实新增 1 个 fallback 但全救回 0 真中断**
- fallback 请求数 1 < 5 阈值 ✅
- R2182 恶化趋势仍止住: R2182(1双失败) → R2185(全救回) → R2186(0) → R2187(全救回) → R2188(尾巴滑入) → R2189(0) → R2195(2全救回1新1旧) → R2196(1全救回真新发)

### nv_gw 内部 NV-MS-FB 兜底
- fallback_occurred=true: 11 条, **全 status=200 救回, 0 真中断**
- (R2195=7, 本轮 11, 同量级波动回升)

### NV-ANTH-BREAKER-FAIL (R1719 设计)
- **0 条** (R2195=0, 连续归零)

### 参数误杀类 (全 0)
- 75s_timeout / STREAM-STALL-FAIL / BIG-INPUT / UPSTREAM-ERROR-SEEN / CC4101-UPSTREAM-ERROR = 0
- → **非参数误杀**

### 容器状态 (漂移信号核)
- nv_gw /health ok (nv_num_keys=5, 3 models [kimi_nv,dsv4p_nv,glm5_2_nv], passthrough role, default=glm5_2_nv)
- nv_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z
  (**与 R2195 快照逐项一致 → R2080 重建后连续 N 轮未被重建**, 漂移信号止住)
- cc4101 RestartCount=0 StartedAt=2026-07-21T14:21:44Z
  (R2195 记 14:19 重启 banner 正常配置正确 primary=glm5_2_nv, 本轮 14:21 同窗口, RC=0 非新重建)
- env 关键参数与 R2195 逐项一致 (UPSTREAM_TIMEOUT=90/TIER_TIMEOUT_BUDGET_S=180/
  KEY_COOLDOWN_S=60/TIER_COOLDOWN_S=180/NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150/
  NVU_TIER_BUDGET_GLM5_2_NV=120/NVU_TIER_BUDGET_DSV4P_NV=180/BIG_INPUT 阈值同), **无参数漂移**

## 决策: NOP 巡检不改代码

STATE 三触发改动阈值全不满足:
- SR 94.7% > 85% ✅
- cc4101 fallback 请求数 1 < 5 ✅ (低于阈值, 全救回; 1 新发但 0 真中断)
- 无新增错误类型 ✅ (4 错全 dsv4p_nv ATE 与历史同族)

四重佐证 nv_gw 稳:
1. 4 错全上游无害类 (dsv4p_nv NVCF function ATE 已知良性, glm5_2_nv 主链路 100%)
2. 无参数误杀 (全 0)
3. breaker 不真 OPEN (本轮 0 条连续归零)
4. 参数无漂移 (容器未重建, env 与 R2195 逐项一致)

glm5_2_nv 本轮 100% SR 连续第三轮 (R2188/R2195/R2196), 证明 R2154 动态 header timeout 后主链路持续最稳.
根因 (cc4101 PRIMARY-FAIL 是 NVCF 上游 glm5_2_nv header/ttfb 120s 超时) 本窗口 1 次 (req=f4c1505d) 但全被 ms 救回 0 真中断 —
不是 nv_gw 参数能治根因 (NVCF 上游偶发 header 阻塞), NV-MS-FB + cc4101 fallback 已正确吸收.

## 验证: 0 改动 0 restart 无需验证改动
- curl /health ok
- docker ps 全栈 Up (nv_gw/cc4101/ms_gw/logs_db)
- 容器 RC=0
- env 无漂移 (与 R2195 逐项一致)
- 容器 StartedAt: nv_gw=12:50:09Z (未重建, 同 R2195), cc4101=14:21:44Z (同 R2195 窗口, RC=0)

## 下一轮该做什么
1. 继续巡检. 盯 R2154 动态 header timeout 后 75s_timeout 持续归零 (本轮=0 ✅).
2. **cc4101 fallback 趋势**: R2182(1双失败) → R2185(全救回) → R2186(0) → R2187(全救回) → R2188(尾巴滑入) → R2189(0) → R2195(2全救回1新1旧) → R2196(1全救回真新发).
   连续多轮无双失败/全救回. STATE 建议 ~R2200+ 做下次 6h 复核 (R2182/R2178 都做过 6h 复核 98.2% 无慢退化).
   **下轮拉 fallback 数据时**: 若仍见 req f4c1505d + 22:28:48 时点 → 判为旧事件滑入非新发,
   别误读成"fallback 又发生". 真新发 fallback 会是新 req id + 新时点.
   **若下轮再出现 PRIMARY+FALLBACK 双失败没救回, 或 cc4101 fallback 请求数升到 ≥5/30min(且是新 req id), 需评估**
   (但动也治不了 NVCF 上游慢/软失败, 顶多让 nv_gw 更快放弃 glm5_2_nv 甩 ms — NV-MS-FB 已在跑).
3. 盯 NV-ANTH-BREAKER-FAIL state 计数 (本轮 0 条, 连续归零). 若单轮 +5 或逼近 OPEN 阈值再评估.
   **注意**: fallback_occurred=true ≠ cc4101 fallback. 前者是 nv_gw 内部 NV-MS-FB tier
   兜底正常吸收 (R1719 设计, 本轮 11 条全救回), 后者才是真正"数据空洞"负向指标 (本轮=1全救回真新发).
4. **触发改动的三阈值** (全满足才动, 否则冻结): 30min SR 跌破 85% **或** cc4101 fallback
   请求数 >5 条/30min **且** 出现新错误类型 (zombie 比例上升 / NV-ANTH-BREAKER-FAIL 真 OPEN).
5. 主仓 R21XX alternating -2s 是 HM1 peer 轮 (only HM1), HM2 不参与, 保持 HM2 稳态.
   铁律: 只改 HM2 不改 HM1.
6. 下一 session 接棒若 STATE 又被清: 用 `git log --oneline -8` + DB 重建, **绝不 Read /tmp**
   (上次 session 因反复 Read 不存在的 /tmp 文件陷入 tool-use 死循环被 SDK 看门狗中断).
7. **容器漂移信号止住** (nv_gw StartedAt=12:50:09Z 连续多轮未变). 若下轮再变 + 参数漂移,
   需查是谁改的 (HM1 peer 轮 only HM1 不应动 HM2 nv_gw, 若发现 HM2 env 被改需回滚).
   cc4101 StartedAt=14:21:44Z 是 R2195 已知的 banner 正常重启 (配置正确 primary=glm5_2_nv), 非nv_gw问题.
8. 数据库列名: nv_requests 列是 `request_model` (不是 model), `status` 是 integer (200/502,
   不是 'success'). 下轮拉数据别再用错列名 (R2186 踩过坑).

## nv_gw 参数快照 (HM2, 本轮确认无漂移)
```
MIN_OUTBOUND_INTERVAL_S=10
KEY_COOLDOWN_S=60
UPSTREAM_TIMEOUT=90
TIER_TIMEOUT_BUDGET_S=180
TIER_COOLDOWN_S=180
NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150
NVU_FORCE_STREAM_UPGRADE=0
NVU_TIER_BUDGET_GLM5_2_NV=120
NVU_TIER_BUDGET_DSV4P_NV=180
NVU_BIG_INPUT_FAIL_N=1
NVU_BIG_INPUT_THRESHOLD=250000
NVU_BIG_INPUT_COOLDOWN_S=180
NVU_BIG_INPUT_MODELS=glm5_2_nv
KEY_AUTHFAIL_COOLDOWN_S=60
NV_INTEGRATE_KEY_COOLDOWN_S=90
```
容器: nv_gw RestartCount=0 StartedAt=2026-07-21T12:50:09Z (同R2195, 连续多轮未被重建, RC=0, env无漂移) /
cc4101 RestartCount=0 StartedAt=2026-07-21T14:21:44Z (同R2195窗口, RC=0)
