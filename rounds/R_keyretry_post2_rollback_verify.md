# R-keyretry-post2 (hm2_cc2): R-keyretry 回滚收尾轮 — 部署→验证→回滚闭环

> 2026-07-27 10:28 CST. 收尾轮. R-keyretry (commit 24d435c) 部署后, post1 验证发现 0 救回 +
> 场景不匹配; **post1 之后有人把 env 回滚到 NVU_CALLER_RETRY=0 (compose mtime 10:05:55,
> nv_gw 10:06 重启), 但回滚动作没写轮文件没更新 STATE**. 本轮 = 补齐交接棒: 确认回滚已生效 +
> 回滚后验证 + 闭环归档. **0 改动 0 restart** (回滚是上一动作, 本轮只验证+记数据).

## 时间线还原 (交接棒盲点修正)

| 时间 (CST) | 动作 | 落仓状态 |
|-----------|------|---------|
| 09:28 | R-keyretry 部署 (commit 24d435c, env NVU_CALLER_RETRY=3) | ✅ commit+push |
| 09:35 | post1 验证 (5 重试请求 0 救回, 场景1+2 不匹配, NOP 不改码) | ❌ 文件写了但未 commit |
| 10:05-10:06 | **回滚** (env NVU_CALLER_RETRY=0, compose 注释 "净负作用 499爆发8×/h 真救回0", restart nv_gw) | ❌ 未写轮文件, 未更新 STATE |
| 10:28 | **post2 本轮**: 拉回滚后数据确认 + 补 commit + 更新 STATE | 本轮 |

→ STATE.md 停在 "R-keyretry 部署成功, 下轮该验证", 下个 session (本轮) 接棒时差点基于错误
认知操作. 本轮先 cat 已存在但未 commit 的 post1 文件还原真相, 再补 post2 闭环.

## 回滚确认 (本轮实测)

### env + 源码一致性
- compose env: `NVU_CALLER_RETRY=0` ✓ (注释: "R-keyretry-post1 回滚: 部署后实测净负作用
  (499爆发 8×/h, duration 95-180s 撞SDK131s墙, 真救回0). env=0 回退 max_attempts=1")
- `NVU_CALLER_RETRY_INTERVALS=2,4,8` (停用, env=0 时不读)
- `NVU_CALLER_RETRY_KEY=4` (停用, 注释标 "(停用)")
- config.py L144: `NVU_CALLER_RETRY = int(os.environ.get("NVU_CALLER_RETRY", "0"))` 默认 0 ✓
- upstream.py L1343-1347: `_chain_max_attempts = _caller_retry if >0 else 1` → env=0 → 回退 1 ✓
- upstream.py L1360: `_is_caller_bound = (... and NVU_CALLER_RETRY > 0)` → env=0 → 不进 caller-bound
  分支, 走普通 chain (max_attempts=NVU_NUM_KEYS+2) ✓
- nv_gw 上次重启: 2026-07-27T02:06:18Z = CST 10:06:18 ✓ (compose mtime 10:05:55 +0:23s)
- 启动日志: `[NV-GLM52-CHAIN] CALLER_BIND caller=cc4101-primary -> fixed key=k2 (no cross-key
  rotation, max_attempts=1)` ✓ max_attempts=1 印证回滚生效 (R-keyretry 时是 3)

### 回滚铁证: RETRY-SLEEP 标签归零
- `docker logs nv_gw --since 20m | grep -c NV-GLM52-RETRY-SLEEP` = **0** ✓
  (R-keyretry 生效时每次重试间记此标签, 回滚后不再触发)

## 回滚后验证数据 (CST 10:06-10:26, 20min 干净窗口)

### cc2 (cc4101-primary) SR
- 38×200 / 1×499 (client_gone_during_flush, BUG-A 家族) → **SR 97.4%**
- 对比 R-keyretry 生效时段 (CST 09, 6h hourly): SR 78.9% (12 fail)
- 对比回滚后 (CST 10, 6h hourly): SR 91.7% (4 fail)
- → 回滚后 SR 回升, 499 从 8×/h 降回 BUG-A 基线 (~4×/h)

### cc4101 真 fallback (回滚后 20min)
- 1 次 (NVCF ttfb >60s 撞 PRIMARY_HEADER_TIMEOUT, ms_gw 救回)
- 场景2 (post1 定义): NVCF ttfb 超时被 cc4101 60s pre-empt, R-keyretry 重试本就不跑,
  回滚对此场景无影响, fallback 仍靠 ms_gw 兜

### nv_gw CHAIN 状态 (回滚后 20min, NVCF 上游故障期)
- CHAIN-FAIL: 23 / SUCCESS: 1 ← **NVCF glm5_2_nv 此刻大面积 ttfb 超时/key 耗尽**
- CHAIN-FAIL → all_keys_exhausted → nv_gw 内部 NV-MS-FB-ATTEMPT (fallback ms_gw) →
  cc2 侧记 200 (ms_gw 救回) → cc2 SR 97.4% 靠 ms_gw 兜底
- PRIMARY_HEADER_TIMEOUT: 1 次 (NVCF ttfb 超时)

## 关键结论

### 1. R-keyretry 实验闭环: 部署→验证→回滚, 决策正确
- 部署依据: STATE.md "用户直接指令" (非 cc2 自主轮)
- post1 验证: 5 重试请求 0 救回 (场景1 全面 key 耗尽 + 场景2 ttfb 超时 pre-empt)
- 回滚依据 (compose 注释): duration 95-180s 撞 cc2 SDK 131s 客户端首字节墙 → 499 爆发 8×/h
  → 净负作用 (0 救回 + 引发新 499), 回滚正确
- 回滚后验证 (本轮): SR 78.9%→97.4% 回升, RETRY-SLEEP=0 印证禁用, 499 回基线

### 2. R-keyretry 代码保留但 env 禁用 (安全状态)
- config.py / upstream.py 的 R-keyretry 代码仍在 (NVU_CALLER_RETRY 读 env, 默认 0)
- env=0 → 代码路径不触发, 等同 R-keyretry 之前的逻辑 (fixed key max_attempts=1)
- 回滚成本: env 单点 (改回 3 即恢复), 不需 cp .bak (源码未碰)
- 保留代码理由: 用户直接指令部署, 回滚决策已由数据驱动 (post1 0 救回 + 本轮 499 爆发铁证),
  未来若 NVCF 故障形态变化 (间歇 429 非 ttfb 超时) 可重启用

### 3. 当前 NVCF 上游故障非 nv_gw 可改码解决
- 回滚后 20min nv_gw CHAIN-FAIL=23/SUCCESS=1: NVCF glm5_2_nv 此刻大面积挂
- 故障形态: ttfb >60s (cc4101 pre-empt) + 5 key 全 exhausted (同 key 重试也救不回)
- 这正是 R-keyretry 无效的两种场景 (post1 已定义), 回滚不影响此故障
- cc2 不中断靠 ms_gw(40007) fallback 兜底 — 符合 CLAUDE.md "40007 是重启/故障窗口热备" 设计
- 当前不是再改 nv_gw 码的时机: 无新可优化点 (故障在上游 NVCF, 非 nv_gw 配置问题)

## 三阈值判稳 (回滚后 20min)
| 阈值 | 实测 | 判定 |
|------|------|------|
| cc2 (cc4101-primary) SR | 97.4% (38/39, 1×BUG-A 499) | ✓ 回升至基线 |
| cc4101 真 fallback | 1 (NVCF ttfb 超时, ms_gw 救回) | ⚠ NVCF 故障期, 非退化 |
| 无新错误类型 | client_gone_during_flush (BUG-A 已知) | ✓ |

→ SR 回升 + 无新错误 + R-keyretry 已禁用 (RETRY-SLEEP=0) → 回滚正确, 闭环归档.
当前 nv_gw 行为 = R-keyretry 之前 + R-buffer 持续生效. **冻结 NOP, 0 改动 0 restart.**

## 本轮改了什么
**0 改动 0 restart** (收尾验证轮). 只拉数据确认回滚生效 + 补 commit + 更新 STATE.
- 补 commit: `R_keyretry_post1_patrol_verify.md` (上轮写了未 commit)
- 新增: `R_keyretry_post2_rollback_verify.md` (本轮, 回滚闭环归档)
- 更新: `STATE.md` (让"上一轮发生了什么"反映 R-keyretry 闭环)

## 下轮建议
1. **R-keyretry 闭环已归档, 不再动** (env=0 禁用, 代码保留待 NVCF 形态变化重启用)
2. **盯 NVCF 上游恢复**: CHAIN-FAIL/SUCCESS 比 + cc4101 fallback 数. 若 NVCF 恢复 (CHAIN-FAIL
   骤降, fb→0), cc2 SR 应回 100% (post7 基线). 当前是 NVCF 故障期, SR 97.4% 靠 ms_gw 兜底
   属正常, 不改码.
3. **改用 nv_requests.created_at 查 cc2 时序 SR** (post7 修正: cc_requests.ts 非单调).
   6h hourly 分桶看趋势, 不做精确 30min 计数.
4. **盯 BUG-A 499 (client_gone_during_flush)**: SDK 131s 客户端墙, buffer 重试无效是设计局限,
   当前不治 (NVCF ttfb 长输出 + 大 input 段). 频次 ~4-8×/h 波动接受.
5. **不碰 40007** (ms_gw 重启热备, 当前 NVCF 故障期全靠它兜底 cc2 不中断).
6. 铁律: 改前数据, 改后验证, 聚焦 40006, 只改 HM2, 写入仓库, 尽量多走 glm5_2_nv 少 fallback.

## 回滚锚点 (R-keyretry, 保留待用)
- 重启用 (若未来 NVCF 形态匹配): compose env `NVU_CALLER_RETRY=3` + `docker compose up -d nv_gw`
- 代码回滚 (若要彻底删 R-keyretry 逻辑): `cp upstream.py.bak.R-keyretry upstream.py &&
  docker compose restart nv_gw` (但 config.py 仍读 env=0, 不 restart 也安全)

## 关联
- R-keyretry (commit 24d435c): 同 key 重试 3x 部署
- R-keyretry-post1 (本轮补 commit): 验证 0 救回 + 场景1/2 不匹配
- R-buffer-post7 (commit 9596fe1): 巡检 + 修正 cc_requests.ts 时序查询方法论
- CLAUDE.md BUG-A: cc4101 pre-empted nv_gw retry (场景2 根因), SDK 131s 客户端墙

HM2 only. Co-Authored-By: Claude <noreply@anthropic.com>
