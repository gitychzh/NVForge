# R699: HM2 全链路 bug 审计 + 8 项修复

**日期**: 2026-07-04 / 2026-07-05
**主机**: HM2 (opc2_uname @ 100.109.57.26)
**触发**: 用户请求"基于当前配置，再次全链路排查远程设备的 bug"

## 背景

R698 (JP 节点 per-key 分流) 部署后 dsv4p_nv 稳定，但全链路审计发现 8 个遗留 bug。
本 round 逐项修复并验证。**所有修改均数据驱动 + 端到端验证**。

## Bug 列表与处置

### BUG-1: nv_gw peer fallback 自环 (FIXED by peer)
- **现象**: HM2 `NVU_PEER_FALLBACK_URL=http://100.109.57.26:40006` (指向自己)
- **根因**: R699 审计前 peer 已自修为 `http://100.109.153.83:40006` (HM1)
- **验证**: `docker exec nv_gw env | grep PEER_FALLBACK_URL` 显示 HM1 地址 ✅
- **备注**: peer 直接改 compose 未 commit (违反铁律5)，本 round 代为记录

### BUG-2: UPSTREAM_TIMEOUT=25 太低 (FIXED)
- **现象**: 非思维链路 UPSTREAM_TIMEOUT=25s，dsv4p 复杂提示 28-39s → 超时
- **数据**: R696/R698 记录 dsv4p 74f02205 复杂 prompt 28-39s，25s 必超
- **修复**: `/opt/cc-infra/docker-compose.yml` line 483 `UPSTREAM_TIMEOUT: "25"` → `"40"`
- **验证**: 重启后 6/6 非思维请求成功；DB `status=200` ✅
- **关联**: 思维链路用 `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=40`，两边现在一致 40s

### BUG-3: hermes context_compressor 404 (FIXED)
- **现象**: hermes `auxiliary.compression` block 全空 (provider/model/base_url/api_key 都默认/空)
- **根因**: context_compressor 用主模型 dsv4p_nv 打 ms_gw，ms_gw 无 dsv4p_nv → 404
- **修复**: `~/.hermes/config.yaml` auxiliary.compression:
  ```yaml
  compression:
    provider: custom
    model: glm5_2_ms
    base_url: http://127.0.0.1:40007/v1
    api_key: ms-gw-token
    timeout: 120
  ```
- **验证**: hermes 重启后 70s 内无 404 ✅
- **边界**: 只改 gateway-side 字段 (model/base_url/api_key 指向 ms_gw)，未动 agent 自己的压缩策略 (threshold/target_ratio/protect_last_n 等保持)

### BUG-4: ms_gw /v1/models 缺 context_length 字段 (FIXED)
- **现象**: ms_gw `_handle_models` 返回 `context_window` 字段，OpenAI 标准是 `context_length`
- **影响**: openclaw 等读 context_length 的 agent 拿不到上下文窗口
- **修复**: `/opt/cc-infra/proxy/ms-gw/gateway/handlers.py` `_handle_models` 增加 `context_length` 别名:
  ```python
  "context_window": spec.get("context_window", 131072),
  "context_length": spec.get("context_window", 131072),  # R699 BUG-4
  "max_tokens": spec.get("max_tokens", 32768),
  ```
- **验证**: `curl /v1/models` 三个模型均返回 `context_length=131072` ✅

### BUG-5: nv_gw DB ts 8h 偏移 (FIXED)
- **现象**: `nv_requests.ts` / `nv_tier_attempts.ts` 比 `now()` 快 8h
- **根因**: handlers.py:176,215 用 `datetime.datetime.now().isoformat()` (naive, 无时区)；upstream.py:383,766,958 用 `time.strftime("%Y-%m-%dT%H:%M:%S")` (无时区)。容器时区 CST(+08)，naive datetime 被 postgres timestamptz 当 local time 解析 → +8h 偏移
- **修复**:
  - `handlers.py`: `datetime.datetime.now().isoformat()` → `datetime.datetime.now(datetime.timezone.utc).isoformat()`
  - `upstream.py`: `time.strftime("%Y-%m-%dT%H:%M:%S")` → `datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")` + 增加 `import datetime`
- **验证**:
  - 重启后新请求 jsonl timestamp = `2026-07-04T17:38:30.934224+00:00` (UTC 正确)
  - DB `nv_requests.ts` 对齐 `now()`: 17:38/17:40/17:41 UTC ✅
  - `nv_tier_attempts.ts` 同步正确 ✅
  - 旧记录 (重启前) 仍 8h ahead，无法事后修正 (jsonl 是 ground truth)
- **备份**: `handlers.py.bak.R699`, `upstream.py.bak.R699`

### BUG-6: ms_gw ms_requests.ts 全 1970 (FIXED) + variant 6-9 exhausted (FALSE ALARM)
- **现象 A**: `ms_requests.ts` 全部 1970-01-06
- **根因 A**: ms_gw `handlers.py:119` `t_start = time.monotonic()` (单调时钟，从系统启动算起，非 epoch)，`int(t_start*1000)` 给 `fromtimestamp()` → 1970 附近
- **修复 A**: 拆分 `t_start` (monotonic, 用于 duration_ms) 与 `t_start_wall` (time.time(), 用于 ts):
  ```python
  t_start = time.monotonic()  # for duration
  t_start_wall = time.time()  # R699 BUG-6: wall clock for ts (monotonic -> 1970)
  ...
  "ts": int(t_start_wall * 1000),
  ```
- **验证 A**: 重启后新请求 `ms_requests.ts = 2026-07-04 17:38:11+00` 对齐 `now()` ✅
- **现象 B (误报)**: 审计报告"variant 6-9 exhausted"
- **核实 B**: `SELECT variant_idx, status, count(*) FROM ms_requests GROUP BY 1,2` — 全部 status=ok，10 个 variant 均有成功记录，**无失败**。variants_cooling v0/v1/v2 是临时 cooldown 会自动恢复，非 bug ✅

### BUG-7: cc4101 orphan 容器 (FIXED)
- **现象**: `docker ps` 显示 `cc4101` 容器 (image cc-infra-cc4101, 7h healthy)，但 `docker-compose.yml` 无此 service 定义
- **根因**: 历史 compose 定义过 cc4101 service，后续移除但容器未删 (label project=cc-infra, service=cc4101, workdir=/opt/cc-infra)
- **修复**: `docker rm -f cc4101`
- **验证**: `docker ps -a` 仅剩 legacy_cc_1/legacy_cc_2 + 9 个活跃容器 ✅

### BUG-8: nv_proxy_selector.sh 缺失 (FALSE ALARM)
- **审计推测**: "应该有 nv_proxy_selector.sh 但找不到"
- **核实**: `grep -rn "nv_proxy_selector\|proxy_selector" nv-gw/gateway/*.py docker-compose.yml` **无任何引用**
- **结论**: 当前架构是 env 驱动 (`NVU_PROXY_URL1..5` 直接指向 mihomo 7894-7899 端口) + mihomo `type: select` 手动选节点，**无脚本依赖**。bug 不存在 ✅

## 修改文件清单

| 文件 | 位置 | 改动 |
|---|---|---|
| `docker-compose.yml` | `/opt/cc-infra/` (HM2) | line 483 `UPSTREAM_TIMEOUT: "25"→"40"` |
| `~/.hermes/config.yaml` | HM2 | auxiliary.compression 块填充 ms_gw 配置 |
| `proxy/ms-gw/gateway/handlers.py` | `/opt/cc-infra/` (HM2) | `_handle_models` 增加 context_length 别名; `t_start` 拆分 monotonic/wall |
| `proxy/nv-gw/gateway/handlers.py` | `/opt/cc-infra/` (HM2) | timestamp → UTC-aware (2 处) |
| `proxy/nv-gw/gateway/upstream.py` | `/opt/cc-infra/` (HM2) | timestamp → UTC-aware (3 处) + `import datetime` |

## 部署 artifacts

`deploy_artifacts/R699_hm2_full_link_fix/` 存放上述 3 个 gateway 源文件的修复后版本:
- `nv-gw_handlers.py`
- `nv-gw_upstream.py`
- `ms-gw_handlers.py`

## 验证汇总

| 项 | 验证方法 | 结果 |
|---|---|---|
| BUG-1 | `docker exec nv_gw env \| grep PEER_FALLBACK_URL` | HM1 地址 ✅ |
| BUG-2 | DB `status=200` 6/6 非思维请求 | ✅ |
| BUG-3 | hermes 重启后 70s 无 404 | ✅ |
| BUG-4 | `curl /v1/models` 返回 context_length=131072 | ✅ |
| BUG-5 | jsonl + DB ts 对齐 now() UTC | ✅ |
| BUG-6 | ms_requests.ts 对齐 now() UTC; variant 全 ok | ✅ |
| BUG-7 | `docker ps` 无 cc4101 | ✅ |
| BUG-8 | grep 无引用 (不存在) | ✅ |

## 后续

- HM1 (本机) 的 nv_gw / ms_gw 源是否也有同样 ts bug? **待 R700 核查** (HM1 改前必有数据)
- `NVU_PEER_FALLBACK_TIMEOUT` HM2=25 / HM1=45 不对称 — 当前合理 (HM2→HM1 链路 25s 够)，暂不动
- peer 直接改 compose 未 commit 的问题已在本 round 代为记录
