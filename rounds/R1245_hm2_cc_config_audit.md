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
