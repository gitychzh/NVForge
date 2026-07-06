# R794: DB 记录 function_id + per-attempt IP, mihomo filter 排除香港

## 摘要

用户要验证 NVIDIA 是否按 "每 800 条/5h/key/IP/functionID" 限速。当前 DB 缺 `function_id` 列。
R794 给 `nv_requests` + `nv_tier_attempts` 两表加 `function_id` 列, 并在 upstream.py 每个
key_cycle_attempt 记录该次 attempt 选中的 NVCF function_id; 同时 mihomo filter 预防性排除
香港节点 (NVIDIA 疑对 HK IP 特殊限制)。

## 改前数据 (铁律)

### DB schema 现状

- `nv_tier_attempts` 已有 `egress_ip, egress_route, nv_key_idx, ts` (HM2, R784 加);
  HM1 这两列**完全缺失** (R784 整组改动 HM1 漏做, diff 确认 HM1 db.py 落后 HM2)。
- 两表都**缺 `function_id`**。

### 源码现状

- `upstream.py` pexec 路径 `result.function_id` 已赋真实 NVCF ID (line 442/424), integrate 路径
  赋占位 `"integrate"` (line 127), 但 `key_cycle_attempts.append({...})` 13 个分支**都未带** function_id。
- HM1 upstream.py **完全没有 egress 代码** (grep egress=0), 且 config.py 缺 `egress_info_for_key` /
  `NVU_EGRESS_IPS`; HM1 有 FALLBACK_GRAPH 等独有逻辑, 不能整文件覆盖。
- `hermes-logs-schema.sql` 用 `CREATE TABLE IF NOT EXISTS`, 不会改已存在表; R784 当时只 ALTER
  没回写 SQL 文件 (遗留不一致)。

### mihomo 现状

- HM2 `nv-us-provider` 订阅实测无香港节点 (仅日/新/美/韩/迪拜/瑞士/澳/印度/台湾);
  filter `美国|圣何塞|阿什本|洛杉矶|日本东京|AWS日本` (无排除香港)。
- HM1 filter `美国|圣何塞|阿什本|洛杉矶` (无日本, 无香港)。
- R793 后 5 个 NV 代理端口 (7894-7899) 已无 key 在用, filter 纯预防未来订阅更新带入香港。

## 决策 (用户确认)

- DB schema + db.py 两机都我改 (共享源码必须一致, 用户授权跨 HM1)。
- HM1 只补 function_id (不动 egress, 列允许 NULL — HM1 直连 IP 只 1 个, NULL 不损信息)。
  HM2 补 function_id (egress HM2 已有)。
- mihomo filter 显式排除香港 (不停 NV 端口, 不动其它用途)。

## 改动

### 1. DB schema 加列 (两机, ALTER, 幂等)

```sql
ALTER TABLE nv_tier_attempts ADD COLUMN IF NOT EXISTS function_id TEXT;
ALTER TABLE nv_requests     ADD COLUMN IF NOT EXISTS function_id TEXT;
CREATE INDEX IF NOT EXISTS idx_nv_att_func_ts ON nv_tier_attempts (function_id, ts DESC) WHERE function_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_nv_req_func_ts ON nv_requests     (function_id, ts DESC) WHERE function_id IS NOT NULL;
-- HM1 额外补 R784 遗漏的 egress 列:
ALTER TABLE nv_tier_attempts ADD COLUMN IF NOT EXISTS egress_ip TEXT;
ALTER TABLE nv_tier_attempts ADD COLUMN IF NOT EXISTS egress_route TEXT;
ALTER TABLE nv_requests     ADD COLUMN IF NOT EXISTS egress_ip TEXT;
ALTER TABLE nv_requests     ADD COLUMN IF NOT EXISTS egress_route TEXT;
```
两机 `hermes-logs-schema.sql` 末尾追加同段 (120 行, 幂等, 修复 R784 遗留)。

### 2. db.py (两机, 统一 298 行)

`/opt/cc-infra/proxy/nv-gw/gateway/db.py`:
- `_build_request_row(m)`: 末尾加 `m.get("function_id")`
- `nv_requests` INSERT: 列清单 + ON CONFLICT UPDATE 加 `function_id, egress_ip, egress_route`
- `nv_tier_attempts` INSERT: 列清单 + attempt_rows 元组加 `a.get("function_id")`

HM1 db.py 从落后 (287 行无 egress) 同步到 HM2 水平 + 两机都加 function_id → 统一 298 行。
backup: `db.py.bak.R794` (两机)。

### 3. upstream.py (两机, 外科手术式 patch)

每机 13 个 `key_cycle_attempts.append({...})` 分支加 function_id 字段:
- pexec 路径 (`_try_tier_keys`, 8 处): `"function_id": function_id` (该 tier 选定的真实 NVCF ID)
- integrate 路径 (`_try_integrate_keys`, 5 处): `"function_id": "integrate"` (占位)

`execute_request` 两处 (成功 + 失败出口) 透传:
```python
if tier_result.function_id:
    metrics["function_id"] = tier_result.function_id
```

用 Python patch 脚本批量改 (闭合 `})` 行行首插入, 字段缩进 = 闭合缩进+4)。
两机各自 patch (函数边界位置不同, 脚本按 `def _try_integrate_keys` / `def _try_tier_keys`
正则定位区分 integrate vs pexec)。HM1 不加 egress (config.py 无 `egress_info_for_key`)。
backup: `upstream.py.bak.R794` (两机)。

### 4. mihomo filter 排除香港 (两机)

`~/.config/mihomo/config.yaml` 的 `nv-us-provider.filter`:

| 机 | 改前 | 改后 |
|---|---|---|
| HM1 | `美国\|圣何塞\|阿什本\|洛杉矶` | `^(?!.*香港\|.*HK\|.*Hong).*(美国\|圣何塞\|阿什本\|洛杉矶)` |
| HM2 | `美国\|圣何塞\|阿什本\|洛杉矶\|日本东京\|AWS日本` | `^(?!.*香港\|.*HK\|.*Hong).*(美国\|圣何塞\|阿什本\|洛杉矶\|日本东京\|AWS日本)` |

`mihomo -t` 两机均 `test is successful`。filter 是预防性 (当前订阅无 HK, 改后行为不变)。
backup: `config.yaml.bak.R794` (两机)。

## 验证 (铁律: 改后必有验证)

### DB 列 (两机)
```
\d nv_tier_attempts  → function_id, egress_ip, egress_route ✓
\d nv_requests       → 同上 ✓
```

### 端到端 (HM2, kimi_nv 200/1.69s)

`nv_requests` (重启后行):
| status | key | function_id | egress_ip | tier |
|---|---|---|---|---|
| 200 | k0 | f966661c-790d-... | 134.195.101.193 | kimi_nv |
| 200 | k1 | 3b9748d8-1d85-... | 218.93.250.242 | glm5_2_nv |
| 200 | k0 | 74f02205-c7ba-... | 134.195.101.193 | dsv4p_nv |
| 200 | k4 | 74f02205-c7ba-... | 134.195.101.180 | dsv4p_nv |

**function_id + egress_ip + key_idx 三维全落库** — 验证 "每 X 条/key/IP/functionID" 限速的
全部维度齐备。重启前行 function_id 为 NULL (旧代码), 重启后行有值。

### 端到端 (HM1)

`nv_requests`: status=200, key=1, function_id=74f02205-..., tier=dsv4p_nv ✓
`nv_tier_attempts`: key=0, function_id=74f02205-..., error=504_nv_gateway_timeout ✓
(HM1 egress_ip 列存在但 upstream.py 不写 → NULL, 符合 "HM1 只补 function_id" 决策。)

### mihomo config
`mihomo -t` 两机 `test is successful` (YAML 合法, 下次重启生效)。

## 限速验证查询 (用户目标)

现在可用以下 SQL 验证 "每 800 条/5h/key/IP/functionID" 假设:
```sql
-- 按 key + IP + function_id 窗口聚合, 看是否在 ~800 条/5h 处出现 429/504 拐点
SELECT function_id, egress_ip, nv_key_idx,
       date_trunc('hour', ts) AS hr,
       COUNT(*) AS n,
       COUNT(*) FILTER (WHERE error_type LIKE '%429%') AS n429,
       COUNT(*) FILTER (WHERE error_type LIKE '%504%') AS n504
FROM nv_tier_attempts
WHERE ts > now() - interval '24 hours' AND function_id IS NOT NULL
GROUP BY 1,2,3,4 ORDER BY n DESC;
```

## 铁律检查

- [x] 改前有数据 (schema 现状 + db.py diff + upstream.py egress 缺失 + mihomo 订阅实测)
- [x] 改后有验证 (DESC 表 + 端到端 function_id/egress_ip 落库 + mihomo -t)
- [x] 聚焦 nv_gw (DB/db.py/upstream.py 都是 40006 链路; mihomo 是 NV 代理层)
- [x] 写入仓库 (本 round 文件)
- [x] 两机一致 (db.py 统一 298 行; upstream.py 各自 patch; schema SQL 统一 120 行)

## 不改的项

- HM1 upstream.py 不补 egress (config.py 缺 egress_info_for_key, 跨 R784 整组改动风险高;
  egress_ip 列 NULL 不影响 function_id 限速验证 — HM1 直连单 IP)。
- mihomo NV 端口 7894-7899 listeners 不删 (R793 收尾范围, 本轮只加 filter)。
- TIER_TIMEOUT_BUDGET_S / FORCE_STREAM_UPGRADE_TIMEOUT 不动 (R793 已说明)。

## 跨机协作备注

- R794 改动跨 HM1 (memory 里归远程 CC), 因 db.py/schema 是共享源码必须两机一致, 用户明确授权。
- 远程 CC 若 pull 到本 round, 请知悉: HM1 db.py/upstream.py/schema 已被本机同步, 勿回退。
- git push 用 `ssh -p 443 git@ssh.github.com` 经 mihomo 7891 (GitHub 22 端口被 GFW reset)。
