# R1245: HM2 CC 配置系统性体检 + 两项零风险修复

## 改前数据 (2026-07-13 21:00, HM2 远程体检)

### cc4101 链路 7 天 metrics (1430 请求)

| token 桶 | 请求数 | zombie/502 | 率 |
|---|---|---|---|
| <80k | 1009 | 232 | 23.0% |
| 80-105k | 200 | 32 | 16.0% |
| 105-155k | 221 | 22 | 10.0% |
| >155k | 0 | 0 | - |

**结论: zombie 与 token 规模弱相关, <80k 反而最高 23%** — 推翻"88k 死亡窗口是主因"假设.
R1244 已记 "16 zombie_empty (NVCF content-filter, not config-fixable)" 佐证.

### zombie 来源细分 (7d 288 个失败)

- **primary timeout (nv_gw glm5_2_nv 挂): 235 (81.6%)** ← 主因
- fallback zombie (ms_gw 后端空僵尸): 52 (18.1%)
- 其他: 1

### primary 不可用根因 (直测 2026-07-13 21:10)

```
curl nv_gw:40006 glm5_2_nv (小请求 stream):
  req1: 60s 无响应 http=000
  req2: ttfb=59.9s http=200 (60s 级卡死)
  req3: 60s 无响应 http=000
curl ms_gw:40007 glm5_2_ms (同请求):
  ttfb=2.5s http=200  (正常)
```

→ NVCF glm5_2_nv 后端服务端故障 (R825/R1242 已记 "function 3b9748d8 DEGRADED"),
  非配置层可修. cc4101 熔断器已正确 OPEN + skip primary (今天 12/33 skip),
  fallback (ms_gw glm5_2_ms) 撑着, 7d 772/1098 成功 (70.3%).

## 改动

### 1. cc4101 config.py 注释/default 对齐 R805

`/opt/cc-infra/proxy/cc4101/gateway/config.py`:

- 注释 "Fallback: ms_gw (dsv4p_ms)" → "Fallback: ms_gw (glm5_2_ms)"
- R704 注释补 R805 真相 (改回 glm5_2_ms 原因: NV DEGRADED 期 dsv4p_ms 同链路也降级)
- `FALLBACK_UPSTREAM_MODEL` default `dsv4p_ms` → `glm5_2_ms` (防 env 丢失落过时值)
- 备份: config.py.bak.R1245-pre-fb-comment-fix
- 影响: 零. live 容器 env 已配 glm5_2_ms, default 只是兜底; 无需重启.
- 验证: `docker exec cc4101 python3 -c "from gateway import config; print(config.FALLBACK_UPSTREAM_MODEL)"` → glm5_2_ms ✓; 容器 Up 32min 未重启.

### 2. 清理 3 份过时 settings.json.bak

`~/.claude/settings.json.bak{,.1781785846,.pre_cc4101}` 全部指向已废弃 legacy litellm
链��� (40001/40000 + sk-litellm-local + glm5.1), 误回退会把 CC 打回死链路.

- 删除 3 份
- 用当前 live (4101/cc4101-token/cc-glm5-2) 生成新 `settings.json.bak`

## 未做的 (留档, 待用户确认)

- **CLAUDE.md 重写**: 仓库根 CLAUDE.md + NVForge/CLAUDE.md 仍描述 legacy 40001/glm5.1,
  未跟上 R827 CC→cc4101 迁移. R682 决策"legacy 不退役"仍对, 但 CC 链路段需补 cc4101.
  涉及多文件措辞, 留独立任务.
- **autoCompactWindow 下调**: 原假设避开 88k 窗口, 但数据显示 <80k zombie 反而 23% 最高,
  下调无效. 不改.
- **memory 同步**: 远程 NVForge memory 仅 2 条, 本地 22 条. 待 rsync.
- **session-env 清理**: 152 目录 (最老 6/14), 待加系统 cron 清理 >30d.

## 铁律核对

- 改前数据: ✓ 7d metrics + 直测
- 改后验证: ✓ config import + live 容器状态
- 聚焦 nv_gw: 本轮改 cc4101 config 注释 + settings bak, 非 nv_gw 参数; 属配置卫生,
  不动 model selection/tier/thinking. (cc4101 是 CC 自身链路, 非优化目标 nv_gw)
- 写入仓库: ✓ 本文件

---

## 补充: 后续三项全部完成 (2026-07-13 22:00, commit a6f5920)

### 3. session-env 清理 + 系统 cron

- 清 >7d 空 session-env 目录: 152 → 13 (全是空壳, 0 文件, 无活跃 session 引用)
- 装系统 crontab (非 CronCreate, 见 [[cron-session-only-unreliable]]): 每周一 3:30 清 >30d 空目录
  `30 3 * * 1 find ~/.claude/session-env -maxdepth 1 -type d -empty -mtime +30 -exec rmdir {} +`
- telemetry 最老 22d 未到 30d 阈值, 保守不删; cron 未来覆盖

### 4. memory 双向同步

- 远程 NVForge memory 原 2 条 (cc-chain-layout-hm2, openclaw-hm2-topology), 修正 stale:
  - cc-chain-layout-hm2: PRIMARY_HEADER_TIMEOUT=8(R825) → 25(R828) 实测
  - openclaw-hm2-topology: contextWindow 48000 → 120000 (R1243 已修)
- 拉远程 2 条到本地, 推本地 22 条到远程, MEMORY.md 索引补 2 行
- 双向同步后: 两机各 25 个 memory .md + MEMORY.md, 内容一致

### 5. CLAUDE.md 重写 (commit a6f5920)

R682 "legacy 不退役"决策已被 R827 实际推翻 (legacy 容器物理退役, 端口 closed).
改前三处 stale: 容器表 / CC config 段 / 铁律3. 详见 commit message.

- 容器表删 6 legacy 行, 加 5 cc-adapter 行 (cc4101/cx4102/opclaw4103/hm4104/oc4105)
- CC 链路段: 改为经 cc4101 走 nv_gw/ms_gw 同链 (非 separate glm5.1)
- 铁律3 + Agent config 末段同步
- 备份 CLAUDE.md.bak.pre-R1245; 两 clone (hermes_improve_self + NVForge) 已对齐 origin/main

## 本轮总结

R1245 系统性体检 → 4 项配置卫生修复全部完成, 2 commit (9629066 config+bak, a6f5920 CLAUDE.md).
核心发现: primary (nv_gw glm5_2_nv) NVCF 后端故障非配置可修, 熔断器+fallback 已是最优;
zombie 与 token 规模弱相关, 下调 autoCompactWindow 无效 (不做).
