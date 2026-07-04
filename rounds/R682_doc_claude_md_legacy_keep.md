# R682: CLAUDE.md 重写对齐 R680/R681 + legacy 链路退役决策(不退役)

## 改前数据

用户要求两件事一起做:(1) CLAUDE.md 同步新命名;(2) legacy 链路(40000-40005+41001)退役。

### legacy 链路流量核查 (2026-07-04 15:15, 6h 窗口)

HM1 `docker logs --since 6h` 各 legacy 容器 [REQ] 计数:

| 容器 | 端口 | 6h [REQ] 数 | 备注 |
|---|---|---|---|
| legacy_dispatch | 40000 | 0 (只 START 行) | dispatcher, 无直接 REQ |
| legacy_cc_1 | 40001 | **27** | **活跃流量** |
| legacy_codex | 40002 | 0 (只 START) | |
| legacy_passthrough | 40003 | 0 (只 START) | |
| legacy_cc_2 | 40005 | 0 (只 START) | |

legacy_cc_1 的 27 条 [REQ] 全部是:
```
model=claude-opus-4-8→glm5.1 stream=True ... agent=_cc  format=anthropic
```

`agent=_cc` = CC 自己(claude-code 进程)。核实 CC 进程环境:
```
ANTHROPIC_BASE_URL=http://127.0.0.1:40001
ANTHROPIC_API_KEY=sk-litellm-local
```
(`~/.claude/settings.json` 里同值)

### 链路还原

```
cc (claude-opus-4-8, anthropic 格式)
  → :40001 legacy_cc_1 (PROXY_ROLE=cc, anthropic→openai 转换)
  → :4000  legacy_ms_litellm (ms-gateway 代码, MS 2D 轮转)
  → ModelScope glm5.1 (ZHIPUAi/GLm-5.2 实际)
```

HM2 同链路,日志量更低但拓扑一致。

## 决策: legacy 链路不退役

legacy 40000-40005 + 4000 不是 dead code,是 **CC 自己的 glm5.1 anthropic 兼容链路**,
独立于三个 agent 的 nv_gw/ms_gw 链路。CLAUDE.md 旧文"聚焦 hm-40006--nv, 不动
40000/40001/40002/40003/40005, ms_uni41001/41002"的铁律正是此意——这些端口服务 CC 自身,
不是可退役的遗留物。

CLAUDE.md 里把 legacy 标成"manual fallback / no longer in hot path"是 R680 前的旧描述,
误导了本次退役评估。已在 R682 CLAUDE.md 重写中纠正。

## 改动

### 1. CLAUDE.md 全文重写 (/home/opc_uname/cc_ps/cc_repair_hm/CLAUDE.md)

主要变化:
- 命名全改 R680 新名: nv_gw/ms_gw/logs_db/legacy_*
- 链路图从 hm40006 改为 nv_gw; 链路拓扑标注直连(HM1)/mihomo(HM2)
- 容器表新增, 9 容器全列, 标注各自服务对象(agent vs CC 自己)
- 铁律: 删 R569 已废止的"只改对端""每轮少改", 保留数据/验证/聚焦/网络/写入仓库; 新增
  "legacy 链路服务 CC 自己, 不可拆"的说明
- 数据源: 表名改 nv_requests/ms_requests/nv_tier_attempts (旧 ha_requests/hm_tier_attempts 已随 R680 重命名); 容器 cc_postgres→logs_db
- 部署工作流: 简化为 CC 直接改两机 (R569 后无交替), bind-mount 改 .py 只 restart
- 新增 "Agent config" 节: 明确三 agent 是独立 APP, CC 只动 gateway-side 字段(provider key/token/baseURL), 不动模型选择/思考强度/工具调用
- 新增 hidden contracts 节: db.py 默认值/NO_PROXY/NVU_GATEWAY_API_KEY/X-MS-Proxy header
- 退役说明: legacy 40000-40005+4000 服务 CC 自己(ANTHROPIC_BASE_URL=:40001), 不是 dead code

### 2. legacy 链路: 不动

维持现状, 不退役。

## 验证

- CLAUDE.md backup 在 CLAUDE.md.bak.pre-r682
- 两机 9 容器全 healthy (R681 已验证, 本次未改容器)
- legacy_cc_1 流量正常 (27 req/6h, agent=_cc, 当前 CC 进程正在用)

## 下一步

无。R680/R681/R682 三连击完成: 命名消歧 + 彻底去 litellm + 文档对齐。
