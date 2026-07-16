# R1635: 两边 cc4101→nv_gw 模型链路源码同步 + 工程化归档 (HM1↔HM2)

> 破铁律授权: 用户明确指令"使两边的模型链路 cc4101→40006 同步, 使用最新的代码".

## 触发 / 目的

- R1627 之前一直存在一个未验证的假设 (memory 旧条): "HM1 nv_gw 源码只到 R1416, 与 HM2 (R1627) 已分叉".
- 用户要切 HM1 本机 CC 从 ms → nv, 但担心 HM1 nv_gw 缺 R1627 全量缓冲修复 → 需先确认两边代码链路是否真同步.
- 用户指令: "使两边的模型链路 cc4101→40006 同步, 使用最新的代码, 并逐一检查是否是两边相同, 同时顺便规范一下代码, 使之更符合工程化、长期维护的规则".

## 改前数据 (md5 全量比对)

### cc4101/gateway (11 .py) — 两边 md5 **完全一致**, 无需动

### nv_gw/gateway (14 .py) — 10 个一致, 4 个 HM1 比 HM2 新

| 文件 | HM1 (本机) | HM2 (远程, 改前) | HM1 改进 |
|---|---|---|---|
| `cooldown.py` | cap=`KEY_COOLDOWN_S*4` (可调) | cap=30 (硬编码) | R844 F12 退避封顶可调 |
| `db.py` | R845 worker self-heal + flush 异常兜底 + 新增 `caller`/`nvcf_reqid` 列 | 无 self-heal, 无新列 | R845 可观测性 + 防写静默挂死 + 新增列 |
| `func_health.py` | `HEALTH_THRESHOLD` env-overridable (`NVU_FALLBACK_HEALTH_THRESHOLD`) | 硬编码 0.80 | env 可调阈值 |
| `logger.py` | JSONL/enqueue 写失败 `print` 可见 | 静默 `pass` | R845 把静默 metrics gap 暴露 |

**关键发现**: `config.py` + `handlers.py` (R1627 全量缓冲所在) 两边 md5 **早已完全一致** → 推翻 memory 旧说 "HM1 只到 R1416", **HM1 nv_gw 早已含 R1627** (之前某次已同步过, memory 未及时更新).

### HM2 schema 前置缺口
HM2 `nv_requests` 表**没有** `caller` / `nvcf_reqid` 列 (HM1 db.py INSERT 写这两列). 若直接推 db.py → `UndefinedColumn` 全崩. 必须先 ALTER TABLE.

### 备份文件污染 (工程化)
gateway 源码**不在 git 仓库** (仓库只存 `deploy_artifacts/` 零星快照), 所以本地 `.bak.R*/.diagbak/.preR*` 是**唯一现场快照**, 不能删 — 归档进 `bak-archive/` 子目录 (HM2 cc4101 已有此先例).
- HM1 nv-gw: 10 个; HM1 cc4101: 1 个; HM2 nv-gw: 67 个; HM2 cc4101: 16 个.

### env 配置 (不在同步范围)
两边 `docker-compose.yml` 的 `KEY_COOLDOWN_S` / `TIER_TIMEOUT_BUDGET_S` / `EGRESS_IP` 等参数本就该按各主机数据分别调参 (HM1 直连日本 IP vs HM2 mihomo 5 美国 IP), 不属"代码链路不一致", 保持现状.

## 变更

1. **HM2 schema 加列** (必须先于 db.py 同步):
   ```sql
   ALTER TABLE nv_requests ADD COLUMN IF NOT EXISTS caller text DEFAULT 'unknown';
   ALTER TABLE nv_requests ADD COLUMN IF NOT EXISTS nvcf_reqid text;
   CREATE INDEX IF NOT EXISTS idx_nv_req_caller ON nv_requests (caller, ts DESC);
   ```
   幂等, 经 `docker exec logs_db psql` 执行.

2. **HM2 4 文件先 `.bak.R1632_pre` 备份, 再 scp HM1 版本覆盖** (cooldown.py, db.py, func_health.py, logger.py).

3. **两边 nv-gw/gateway + cc4101/gateway 所有备份文件 `mv` 进 `bak-archive/`** (非删除, 可逆). 子目录无 `__init__.py`, Python 不当 package 导入, compose 整目录挂载无副作用.

4. **规范化** `func_health.py`: `import os` 原在 docstring 前 (致模块 `__doc__` 被吞为普通字符串), 移到 docstring 之后 — 修复模块 docstring. HM1 改后同步 HM2.

5. 两边 `docker restart nv_gw` (bind 挂载只改 .py, restart 即加载新代码, 无需 rebuild).

## 验证清单

| 项 | 结果 |
|---|---|
| HM2 `ALTER TABLE` 加 caller/nvcf_reqid 列 + 索引 | ✅ ALTER TABLE ×2 + CREATE INDEX |
| 4 文件 scp HM1→HM2, md5 一致 | ✅ cooldown=db=func_health=logger 全一致 |
| HM2 `docker restart nv_gw` + `/health` 200 | ✅ `{"status":"ok",...}` |
| HM2 `/health` 启动日志无 import 错 / UndefinedColumn | ✅ 干净启动 |
| HM2 真实请求端到端落库 + caller 列写入 | ✅ req `f2c964bd` http=200 3.23s, `caller=other` 正常 |
| 两边 nv_gw 14 .py md5 全一致 | ✅ 终检 diff 空 |
| 两边 cc4101 11 .py md5 全一致 | ✅ 早已一致 |
| 两边 gateway/ 目录纯净化 (只活跃 .py + bak-archive + __pycache__) | ✅ 4 个目录全无杂质 |
| HM2 备份归档 (nv-gw 67 + cc4101 16) / HM1 (nv-gw 10 + cc4101 1) | ✅ |
| func_health.py docstring 修复 (`__doc__` True) + env 阈值正常读 | ✅ |

## 参数表

无 compose env 调整 (纯代码同步, 不碰两边各自调参的 env).

## 回退
- db.py: HM2 `cp gateway/bak-archive/db.py.bak.R1632_pre gateway/db.py && docker restart nv_gw` (ALTER 加列幂等, 无需回滚 schema).
- 其余: `git` 无源码, 但 `.bak.R1632_pre` + `bak-archive/` 均保留, 可手工恢复.

## 后续
- HM1 本机 CC 切 NV 的前置条件 (代码已一致) 已满足 — 但切之前仍需观察 HM1 nv_gw 实际成功率 (本机 nv_requests 仅 54 条, 样本不足). 切换待用户指令.
- memory 已更新: 推翻 "HM1 只到 R1416" (实为早已含 R1627).

## 铁律
- 改前数据 (md5 查) / 改后验证 (health+logs+请求落库) / 聚焦链路 (只动 nv_gw+cc4101 源码, 不碰 env/agents) / 写入仓库 (本轮文件 + 此 round). 破铁律 (改 HM2) 经用户明确授权.
