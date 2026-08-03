# R700b: openclaw 自优化提示词+脚本更新 — 聚焦 dsv4p_nv40066 pexec 链路

**日期**: 2026-08-03
**主机**: HM2 (opc2_uname)
**改动类型**: openclaw workspace 文件 + 定时脚本

## 背景

R700 将 opclaw4103 链路从 nv_gw:40006/dsv4p_nv 改为 primary=dsv4p_nv40066/dsv4p_nv + fallback=nv_gw:40006/glm5_2_nv.
openclaw 的自优化定时任务 (glm52_optimize.py) 和提示词文件仍引用旧链路 (nv_gw/glm5_2_nv), 需要同步更新.

## 链路确认 (DB 数据)

dsv4p_nv40066 路由方式:
- **100% nvcf_pexec** (NV_INTEGRATE_MODELS 为空, 不走 integrate)
- **Function ID**: 12acbc62 (DeepSeek V4 Pro)
- **5 US IPv4**: mihomo 7900~7904 → 134.195.101.180/188/203.10.96.139/194/120
- **SR**: 96.7% (58/60, 2 个 502 非 openclaw 管辖)
- **avg duration**: 9.5s, max 46.4s

## 改动文件

### 1. ~/.openclaw/workspace/openclaw2_improve_self/openclaw.md (自优化提示词)
- 链路拓扑更新: opclaw4103 → dsv4p_nv40066 (primary) + nv_gw:40006 (fallback)
- 数据源命令改用 `host_machine='opc2sname-dsv4p40066'`
- 优化方向: dsv4p pexec SR, fallback 触发率, 大input慢流, 429配额
- 铁律更新: 聚焦 dsv4p_nv40066 + opclaw4103, 不碰 nv_gw 源码
- 备份: openclaw.md.bak.R700

### 2. ~/.openclaw/workspace/MODEL_CONFIG.md (模型配置参考)
- 拓扑更新: 单 provider opclaw4103 (primary dsv4p_nv + fallback glm5_2_nv)
- dsv4p_nv40066: 100% nvcf_pexec, fid=12acbc62, 5 US IP, 5 key free 轮转
- nv_gw: per-key 混合链路 (fallback 目标)
- NVCF Function ID 映射表更新
- 备份: MODEL_CONFIG.md.bak.R700

### 3. ~/scripts/glm52_optimize.py (定时优化脚本, cron */30 * * * *)
- 数据源: `host_machine='opc2sname-dsv4p40066'` (非 `mapped_model='glm5_2_nv'`)
- 分析维度: per-key SR, timing (ttfb/duration), error_type, caller 分布
- 调整逻辑: per-key proxy IP 轮换 (非 fid/mode swap, 因为 dsv4p 全走 pexec 单 fid)
- 目标容器: `docker compose up -d dsv4p_nv40066` (非 `nv_gw`)
- 备份: glm52_optimize.py.bak.R700

## 验证

### 脚本测试运行
```
[2026-08-03T10:35:23Z] NO CHANGES NEEDED
  k0: SR=100.0% (10/10), avg=7529ms, stable
  k1: SR=92.3% (12/13), avg=11740ms, stable
  k2: insufficient data (4 requests), skip
  k3: SR=100.0% (20/20), avg=10594ms, stable
  k4: SR=100.0% (12/12), avg=7662ms, stable
```

JSON 输出包含:
- target: dsv4p_nv40066
- dsv4p_nv_sr: total=60, ok=58, sr_pct=96.7
- per_key: 5 keys, 全 nvcf_pexec, fid=12acbc62
- callers: hermes 48 req, openclaw 11 req
- current_proxy_urls/egress_ips: 7900~7904 / .180/.188/139/.194/.120

### E2E 链路验证
```
opclaw4103 → dsv4p_nv40066 → nvcf_pexec → NVCF 200 (1.08s)
host_machine=opc2sname-dsv4p40066, caller=openclaw, upstream_type=nvcf_pexec
```
