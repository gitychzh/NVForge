# R1797 — HM2 nv_gw ABSOLUTE_CAP=150 激活执行 + 验证（承接 R1796 计划）

> 铁律：只改 HM2，不改 HM1。本轮性质 = **执行轮**（承接 R1796 已写计划但未执行的状态漂移修复）。
> 模式：nv 直连 cc4101→nv_gw(40006)，R1774 三层修复 burn-in 观测期。

## 背景：承接 R1796

R1796（`rounds/R1796_nv_gw_abs_cap_activate.md`，本地文件，**未 commit**）写了一个完整激活计划：
HM2 的 `/opt/cc-infra/docker-compose.yml` line 73 已写 `NVU_STREAM_ABSOLUTE_CAP_S=150`（R1790 注释
"120→150，给慢流完成机会，降 fallback"），但 nv_gw 容器从 10:46 创建时**从未加载这个 env**
（`docker exec nv_gw env | grep NVU_STREAM_ABSOLUTE_CAP` = 空），config.py:515 回退默认 120s，
导致 120-150s 区间的慢流被 120s 帽子杀成 502。R1796 计划动作 = `docker compose up -d nv_gw`
（env 改动必须 up -d 重创建容器加载，restart 不重读 compose env）。

R1796 round 文件写了完整计划但**上一 session 末执行就停了**（无"验证结果"段，容器 StartedAt
仍 10:46，RestartCount=0）。本轮 R1797 = 把 R1796 计划执行掉 + 验证 + commit。

## 一、改前数据（2026-07-18 21:24 CST = 13:24 UTC，30min/2h 窗）

### 1. 总览窗
| 窗 | total | ok(200) | fail(502) | SR |
|----|-------|---------|-----------|-----|
| 30min | 47 | 40 | 7 | 85.1% |
| 2h | 196 | 173 | 23 | 88.3% |

（status 列是 integer 200/502，非 'success' 字符串 — CLAUDE.md 数据源模板过时，本轮已修正查询）

### 2. 失败分类（30min 7 条 / 2h 23 条）
| error_type | 30min | 2h |
|-----------|-------|-----|
| **stream_absolute_cap** | **2** | **9** (39%, 主犯) |
| all_tiers_exhausted | 2 | 7 |
| zombie_empty_completion | 2 | 3 |
| stream_first_byte_timeout | 1 | 4 |

**stream_absolute_cap 是主犯**（与 R1796 21:10 拉的数据一致：30min 4 条 / 2h 11 条，44%）。

### 3. stream_absolute_cap 失败请求时长（2h 9 条）
| request_id | duration_ms | content_chars (docker logs) |
|---|---|---|
| e8cb59ec | 120210 | 1892 |
| f86e79d5 | 120244 | 802 |
| 6038818a | 123457 | 1020 |
| 684b4ea7 | 120078 | 290 |
| 16d8409b | 120037 | 345 |
| db5f4248 | 120018 | (同批) |
| 73266c71 | 120036 | (同批) |
| 49106dc2 | 120025 | (同批) |
| 41e695e2 | 120019 | (同批) |

**全部 120-124s 被杀，全部有 content_chars (290-1892)** = 正在吐内容的慢流被 120s 帽子提前杀，
不是纯 hang。docker logs 同期 `[NV-ANTH-ABS-CAP] ... cap 120s exceeded ... gap_limit=120.0s`
证实容器实际跑 120s（R1790 的 150 从未加载）。

### 4. 容器状态漂移证据（改前）
- `docker exec nv_gw env | grep NVU_STREAM_ABSOLUTE_CAP` = **空**（env 完全缺失）
- 容器 `StartedAt=2026-07-18T10:46:06Z`，`RestartCount=0`（从未 recreate）
- compose line 73 `NVU_STREAM_ABSOLUTE_CAP_S=150` 写明但未加载
- config.py:515 `float(os.environ.get(..., "120"))` env 缺失回退默认 120
- docker logs gap_limit=120.0s（活证据）

## 二、根因（承接 R1796，本轮复核确认）

HM2 的 nv_gw 容器从未加载 R1790 在 compose 里写的 150，一直跑 config.py 默认 120s。
今天 2h 9 次 stream_absolute_cap 全是这个漂移的直接代价 — 这些请求本该在 120-150s 区间
跑完到 200（都有 content_chars 290-1892），被 120s 杀成 502。**这是状态漂移修复，
不是新调参** — 把容器对齐到 compose 已写明的 150 = 激活已落地决策。

## 三、本轮改动（单点，最小动作）

- **不改 compose 文件**（已 =150，R1790 已写）。备份 `cp docker-compose.yml docker-compose.yml.bak.R1797`（已建）
- **动作**：`cd /opt/cc-infra && docker compose up -d nv_gw`（env 改动必须 up -d 重创建容器；
  restart 不重读 compose env — 这是 R1796 计划的关键点）
- bind-mount 源码不动，不碰 proxy/ms-gw/，不碰 HM1
- ms_gw(40007) 在 nv_gw recreate 窗口（~10-15s）由 cc4101 forwarder 兜住新请求，cc2 无感

## 四、验证（改后即时）

### 1. env 加载 ✓
```
$ docker exec nv_gw env | grep NVU_STREAM_ABSOLUTE_CAP_S
NVU_STREAM_ABSOLUTE_CAP_S=150          # 之前完全缺失，现 =150 已加载
TIER_TIMEOUT_BUDGET_S=180
NVU_MS_FALLBACK_FAIL_THRESHOLD=5
```

### 2. health ✓
```json
{"status":"ok","proxy_role":"passthrough","nv_num_keys":5,
 "nvcf_pexec_models":["kimi_nv","dsv4p_nv","glm5_2_nv"],"port":40006}
```

### 3. docker ps ✓
- nv_gw Up 13s（Recreated 21:29:15）
- ms_gw Up 33h（热备在，未动）
- cc4101 Up 6h，logs_db Up 44h

### 4. 容器重启后即时服务 ✓
- 21:29:29 第一个请求 mapped_model=glm5_2_nv
- 21:29:32 [NV-GLM52-SUCCESS] k1 succeeded（mode stabilized）
- 21:29:36 [NV-PEEK-OK] peek healthy first content after 6812ms

### 5. 待下窗口日志确认（改后观测）
- [ ] 新 abs_cap 触发（若有）应显示 `gap_limit=150.0s`（不再是 120.0s）
- [ ] 120-150s 区间慢流能跑完到 200，stream_absolute_cap 计数显著下降
- [ ] SR 从 85.1% 回升向 88-93%+
- [ ] fallback 仍 ~0（不恶化）

## 五、监督者盲点提示处理（17:30 HM1 监督者追加，关于 SSE flushed_content_chars 阈值）

- 提示假设：R1774 修复 A 的 `flushed_content_chars>0 走 graceful end` 阈值太低，应提到 ≥50c/≥100c，
  或 graceful end 前先 flush content_block_stop 闭合 block。SSE `Could not parse` 复发 12 次/2.5h。
- **本轮不处理**：本轮主犯是 stream_absolute_cap（2h 9 条 = 39% 失败），zombie_empty_completion
  仅 3/2h=13%。铁律一轮一改，先治主犯。**作为 hypothesis 保留到 STATE 下轮清单，不静默丢弃。**
- 下轮若 zombie/parse 复发占比上升，再 dump 一条复发时刻 wire chunk（从
  `/opt/cc-infra/logs/nv_gw/hm_error_detail.*.jsonl` grep request_id）验证阈值假设，一并治。

## 六、铁律符合性
- ✅ 改前有数据（30min+2h+tier+duration+容器 env+docker logs 全拉）
- ✅ 聚焦 40006（只动 nv_gw）
- ✅ 不碰 40007（ms_gw 源码/配置零改动，热备保留）
- ✅ 不碰 HM1
- ✅ 写入仓库（本 round 文件 + STATE 覆写）
- ✅ 改 env 用 up -d 不是 restart（compose env 必须重创建容器才加载）
- ✅ 单点改动（激活一个已有 env，不叠加新调参）

## 七、下一轮（R1798）建议
1. 拉改后 30-90min 窗：确认 stream_absolute_cap 计数下降、gap_limit=150 生效、SR 回升
2. 若 stream_absolute_cap 仍占失败主犯 + content_chars 仍高 → 150 也不够，
   考虑提到 170（仍 < tier_budget 180，留 10s buffer）；但先验证 150 是否已够
3. 若 zombie_empty_completion/SSE parse 复发占比上升 → 处理 17:30 监督者盲点
   （dump wire chunk 验证 flushed_content_chars 阈值假设）
4. fallback 率持续盯（负向核心指标），目标保持 ~0
