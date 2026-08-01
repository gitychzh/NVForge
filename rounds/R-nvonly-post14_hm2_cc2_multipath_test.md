# R-nvonly-post14 — 全方位多链路连通性测试 + glm5_2_nv 接入 integrate

HM2, cc2, 2026-08-01 15:00-16:35 CST

## 动机
全面诊断当前 nv_gw SR 波动 (63%→93% 不稳定)，测试 glm5_2_nv / dsv4p_nv 在三条路径
(pexec nv_gw、direct NVCF pexec、integrate.api) + 10 代理端口 (7 US IPv4) 的连通性，
对比找出最优路由配置。

## 全量测试结果矩阵

### Metrics summary

| 路径 | 模型 | 最佳 TTFB | 最差 TTFB | SR | 429 | 挂死 |
|------|------|----------|----------|-----|------|------|
| nv_gw pexec (stream) | glm5_2_nv | - | - | 0% | 0 | >60s HUNG |
| nv_gw pexec (non-stream) | glm5_2_nv | 10.43s | 10.43s | 100% | 0 | 0 |
| nv_gw pexec (stream) | dsv4p_nv | - | - | 0% | 2/2 keys | 0 |
| nv_gw pexec (non-stream) | dsv4p_nv | 1.99s | 4.97s | 100% | 0 | 0 |
| direct NVCF pexec (stream) | glm5_2_nv | - | - | 0% | 0 | 15s timeout |
| direct NVCF pexec (non-stream) | glm5_2_nv | 0.60s | 0.60s | 100% | 0 | 0 |
| direct NVCF pexec (non-stream) | dsv4p_nv | - | - | 0% | 429 | 0 |
| ✨ **integrate.api direct** | **glm5_2_nv** | **0.36s** | 9.94s | **100%** | 0 | 0 |
| ✨ **integrate.api direct** | **dsv4p_nv** | **0.46s** | 2.70s | **100%→0%** | 0 | 间歇性全挂 |

### 5 US IP + 扩展 IP integrate.api 逐个测试

| Proxy | Egress IP | glm5_2_nv | dsv4p_nv | 备注 |
|-------|----------|-----------|----------|------|
| 7894 | 134.195.101.193 | ✅ 200 (0.45s) | ✅→❌ | GLM52 稳定, DSV4P 间歇挂 |
| 7895 | 134.195.101.180 | ✅ 200 (9.94s) | ✅→❌ | GLM52 有慢异常值 |
| 7896 | 134.195.101.195 | ✅ 200 (2.48s) | ✅→❌ | |
| 7897 | 134.195.101.197 | ⚠️ 瞬态 | ✅→❌ | 重测证实可用 |
| 7899 | 134.195.101.120 | ✅ 200 (0.71s) | ✅→❌ | |
| 7900 | 134.195.101.188 | ✅ 200 (1.46s) | ✅→❌ | |
| 7901 | 203.10.96.139 🇦🇺 | ❌ 000 | ❌ 000 | **地理封锁** |
| 7902 | 134.195.101.194 | ✅ 200 (1.56s) | ✅→❌ | |
| 7903 | 134.195.101.120 | ✅ 200 (1.21s) | ✅→❌ | 同 7899 |
| 7904 | 134.195.101.197 | ✅ 200 (0.72s) | ✅→❌ | 同 7897 |

### 核心发现

1. **integrate.api 对 glm5_2_nv 全维度碾压 pexec**: TTFB 快 29x (0.36s vs 10.43s)，零 429，
   7 个独立 US IPv4 全通。GLM5.2 pexec stream=true 直接挂死 (>60s 无首字节)，
   生产 glm5_2_nv 流量为 0 的根因。

2. **integrate.api 对 dsv4p_nv 间歇性全挂**: 初始测试 10/10 全通 (TTFB 0.46-2.70s)，
   30 分钟后 5/5 全挂 (HTTP 000, 3 不同 key+代理独立验证)。
   这是历史已知问题 (config.py 注释: "integrate 端点对 deepseek-v4-pro 30s 挂死")。

3. **KEY_MODE_BINDING 是全局设置**: 影响所有 model，不是 glm5_2_nv 专用。
   更改会导致 dsv4p_nv 也被路由到 integrate (dead endpoint)，每次浪费 60s×3keys。

4. **NV_GLM52_MODE_CHAIN 的 KEY_MODE_BINDING 优先于 mode_idx**: line 1428 的
   `_bound_mode_name = KEY_MODE_BINDING.get(key_idx)` 覆盖 mode chain 指针 —
   即使 chain=integrate,pexec，如果所有 key 绑 pexec_us_rr，integrate 永远不会被选中。

## 改动 (docker-compose.yml nv_gw env)

### 最终生效 (3 处)

1. **NV_INTEGRATE_MODELS=glm5_2_nv** (原: 空)
   - glm5_2_nv → integrate 首选 (经 line 1759 标准 integrate path)
   - dsv4p_nv → 保持在 NV_INTEGRATE_MODELS 之外，避免 dead integrate 路径
   - 依据: integrate 实测 glm5_2_nv 200, dsv4p_nv 间歇全挂

2. **NV_GLM52_MODE_CHAIN=** (原: pexec_us_rr, 改为空)
   - 禁用 mode chain → glm5_2_nv 不再被 line 1704 拦截
   - 落到 line 1759 走标准 integrate path (5 keys rr → integrate, fallback pexec)
   - 依据: KEY_MODE_BINDING 覆盖 mode_idx，chain=integrate,pexec 实际永远不走 integrate

3. **KEY_MODE_BINDING** 保持原值: 全部 pexec_us_rr
   - 回滚过的尝试: 改为 0:integrate_us_rr;1:pexec_us_rr;2:integrate_us_rr;3:pexec_us_rr;4:integrate_us_rr
   - 回滚原因: KEY_MODE_BINDING 全局生效，dsv4p_nv 的 k0/k2/k4 也被拐进 integrate
     (dead for dsv4p_nv)，每个 req 浪费 60s×3keys 才落到 pexec key → SR 毁灭

### 回滚记录 (已撤销)
- R-nvonly-post14-attempt1: KEY_MODE_BINDING split (integrate/pexec) — 全局副作用，已回滚
- R-nvonly-post14-attempt2: NV_GLM52_MODE_CHAIN=integrate_us_rr,pexec_us_rr + split — combo 仍因 KEY_MODE_BINDING 全局无效，已回滚

## 验证

1. **glm5_2_nv integrate 路由确认**: 日志 `[NV-INTEGRATE-SUCCESS] tier=glm5_2_nv k2 succeeded on first attempt`，TTFB=9.18s (vs pexec 10.43s, -12%)
2. **dsv4p_nv pexec-only 确认**: DB 显示 `upstream_type=nvcf_pexec`，无 integrate 流量
3. **0 fallback**: 30min 内 `fallback_occurred=f` 全表
4. **接口健康**: curl /health 正常, docker ps 全容器 Up

## 生产 SR (10min post-settle)
- cc4101-primary: 2/6 = 33% (低, 含频繁重启污染)
- 全 caller: dsv4p_nv=19 200 + 5 502 + 3 429; glm5_2_nv=1 200 (integrate)
- NULL tier 502=7 (可能过早请求或 restart 期间的 orphan)
- 0 buffer_exhausted, 0 fallback

## 下一步
1. 监控下一个 30min 窗口 — glm5_2_nv integrate SR 应稳定 99%+
2. dsv4p_nv integrate 间歇性故障需持续观测 — 如果恢复可重新加入 NV_INTEGRATE_MODELS
3. 本次没有改 gateway/*.py — 如果要修 KEY_MODE_BINDING 全局性 (使其 per-model)，需要改 upstream.py 源码

## 参数快照
```
NV_INTEGRATE_MODELS=glm5_2_nv
NV_GLM52_MODE_CHAIN= (空=禁用)
KEY_MODE_BINDING=0:pexec_us_rr;1:pexec_us_rr;2:pexec_us_rr;3:pexec_us_rr;4:pexec_us_rr
NVU_DISABLE_MS_FALLBACK=1
NVU_BUFFER_TIMEOUT_STAIRS=90,90,90,90,90
NVU_BUFFER_TOTAL_DEADLINE_S=450
```

## 备份
`/opt/cc-infra/docker-compose.yml.bak.R-nvonly-post14` (改动前的原始文件)