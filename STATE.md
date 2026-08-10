# STATE.md — cc2 自优化 nv_gw 链路 (HM2)

> 当前轮: **R1247 (内容改动 — 用户 7 任务全执行: 40666/nv_gw 各单 fid+integrate 内部兜底, 清理多余 fid, pexec vs integrate 实测对比, hermes+openclaw 两 agent 链路配置 + 端到端验证; 保持 OpenAI 协议)**
> 主链 fid: **281478d0-f307** (dsv4f0731_nv), 现经 **dsvf0731_nv40666 容器** (40666)
> **链路 (R1247)**: cc → cc4101 (4101) → primary `dsvf0731_nv40666:40666/v1/messages` (dsv4f0731_nv, fid 281478d0, 单 fid + integrate 内部兜底) ✅ 200 (~2.6s)
> fallback → `nv_gw:40006/v1/messages` (glm5_2_nv, **fid 3b9748d8**, mode chain pexec→integrate 兜底) ✅ 200 (~7s)
> **agent 链路 (R1247 新增)**: hermes→hm4104(4104)+openclaw→opclaw4103(4103) → primary 40666(dsv4f0731) + fallback nv_gw(glm5.2), 均端到端 200 验证
> 原 primary (nv_gw:40006 dsv4f0731) → 降为 fallback; 原 fallback (ms_gw:40007) → 移除。
> **glm5_2_nv new fid**: 3b9748d8 (ai-glm-5_2, ACTIVE) 替代死链 b1b22d03 (mn-tp8-b200 INACTIVE 404)。
> **改前数据锚点**: 40666 dsv4f0731 0.7-3.1s / 40006 glm5.2 新 fid ~7s (R1246 实测); dsv4p_nv 已 EOL (NVCF 410 Gone 2026-08-07, 容器保留)。

## 本轮 (R1247) 改动 + 依据 + 验证

### 改动 (7 项, 全执行; 用户决策: 保持 OpenAI + 复用 dynamic 机制)
1. **40666 单 fid + integrate 内部兜底**: compose 删 4 行多余 `NVCF_*_FUNCTION_ID` (52e1ddb6/12acbc62/glm52/kimi),
   保留 `NVU_FID_DISCOVERY` (fid 281478d0 自动发现); `upstream.py:2577` gate `tier_model=="dsv4f_nv"` →
   `in ("dsv4f_nv","dsv4f0731_nv")` (dsv4f0731 复用 dsv4f-dynamic pexec→integrate 兜底, 1 行源码改动)。
2. **nv_gw glm5.2 单 fid + integrate 内部兜底**: `NV_GLM52_MODE_CHAIN` `pexec_us_rr` → `pexec_us_rr,integrate_us_rr`
   (pexec 优先, 故障递进 integrate); R1246 已单 fid 3b9748d8。
3. **清理多余 fid (仅这两容器)**: 40666 删 4 行 (见 1); nv_gw R1246 已删 b1b22d03。
4. **pexec vs integrate 实测对比 (直连 NVCF, 5×2 矩阵)**:
   - dsv4f0731: pexec avg ~2.0s, integrate avg ~3.3s → pexec 快 (integrate 须用 -0731 名, 普通名 410 EOL)。
   - glm5.2: pexec avg ~7.1s, integrate avg ~6.8s → 相近 (integrate TTFB 略优)。
5. **hm4104 (hermes)**: compose FALLBACK_URL `ms_gw:40007`→`nv_gw:40006`, FALLBACK_MODEL `dsv4f0731_ms`→`glm5_2_nv`,
   `MS_GW_API_KEY` `ms-gw-token`→`nv-gw-token` (forwarder FALLBACK 路径认证对齐 nv_gw); `config.yaml`
   default & default_model → `dsv4f0731_nv`。
6. **opclaw4103 (openclaw)**: compose PRIMARY `dsv4p_nv40066`→`dsvf0731_nv40666:40666` (dsv4f0731_nv),
   FALLBACK `ms_gw`→`nv_gw(glm5_2_nv)`, `MS_GW_API_KEY`→`nv-gw-token`; `openclaw.json` primary→`nv_cus/dsv4f0731_nv`,
   fallback→`nv_cus/glm5_2_nv`, provider 加 `dsv4f0731_nv` 模型定义。
7. **协议**: 保持 OpenAI `/v1/chat/completions` (两 agent transport=openai_chat / api=openai-completions 不变, cc-adapter 不改)。
   重启 `openclaw-gateway` + `hermes-gateway` (systemd user) 加载新配置, agent model 确认 `dsv4f0731_nv`。

### 依据 (DB/catalog 实测)
- b1b22d03: NVCF catalog **INACTIVE**, pexec 404; 08-09 起 7 天 DB all_tiers_exhausted 0% SR → 死链删除。
- 3b9748d8 (ai-glm-5_2): NVCF catalog ACTIVE, pexec 单发 200 (~5-11s)。b6029a96 ACTIVE 备用。
- dsv4p (12acbc62): catalog 全 INACTIVE, pexec 404, integrate 410 EOL 08-07 → 不可恢复, 仅清理引用。

### 验证 (全通过)
| 项目 | 结果 |
|---|---|
| compose config | `docker compose config --quiet` → **CONFIG VALID** |
| 容器 | nv_gw / dsvf0731_nv40666 / hm4104 / opclaw4103 / cc4101 / dsv4p 全 Up healthy |
| 40666 dsv4f0731 | 200, **fid 281478d0** (discovery), 单 fid, NVU_FID_DISCOVERY 生效 |
| nv_gw glm5.2 | 200, **fid 3b9748d8**, mode chain `pexec_us_rr,integrate_us_rr` 生效 |
| 源码 dynamic gate | `upstream.py:2577` `dsv4f0731_nv` 接入 pexec→integrate 兜底 |
| openclaw 端到端 primary | 4103 → 40666 dsv4f0731, 200 3.6s, caller=openclaw fid=281478d0 |
| hermes 端到端 primary | 4104 → 40666 dsv4f0731, 200 14.7s, caller=hermes fid=281478d0 |
| openclaw fallback (停40666) | 4103 → nv_gw glm5_2, 200 5.3s |
| hermes fallback (停40666) | 4104 → nv_gw glm5_2, 200 8.3s |
| agent 重启 | openclaw + hermes gateway (systemd) active, agent model=`dsv4f0731_nv` |

**pexec vs integrate 实测 (直连 NVCF, 5×2 矩阵)**: dsv4f0731 pexec avg ~2.0s < integrate ~3.3s → pexec 快; glm5.2 pexec avg ~7.1s ≈ integrate ~6.8s → 相近。两模型双链路均健康, pexec 优先 + integrate 兜底合理。
**测试排除**: 任务4 glm5.2 10 连打探针触发 nv_gw 5key NVCF 限流/cooldown, 致 adapter fallback 初测 70s 超时; 属测试自致限流非配置问题, cooldown 恢复后 fallback 200 验证通过。

## 参数快照 (R1247: nv_gw + 40666 + cc4101 + 两 agent, 实测 env)

- **nv_gw (40006)**: `NV_GLM52_MODE_CHAIN=pexec_us_rr,integrate_us_rr` (R1247 新增 integrate 兜底),
  `NVCF_GLM52_FUNCTION_ID=3b9748d8`, `KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0` (全锁 pos0=3b9748d8),
  `NV_INTEGRATE_MODELS=glm5_2_nv`, `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv` (R1246 删 dsv4p_nv),
  TIER_TIMEOUT_BUDGET_S=180, NVU_BUFFER_MAX_RETRIES=5 (stairs 90×5=450s),
  NVU_DISABLE_MS_FALLBACK=0, NVU_FORCE_STREAM_UPGRADE=0, NVU_FORCE_STREAM_UPGRADE_TIMEOUT=150,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4。
- **dsvf0731_nv40666 (40666)**: `NVU_FID_DISCOVERY_ENABLED=1`, MODEL=dsv4f0731_nv, NAME_MATCH=deepseek-v4-flash,
  fid 281478d0 自动发现, **单 fid** (R1247 删 4 行多余 NVCF_FUNCTION_ID);
  `NVU_PEER_FB_SKIP_MODELS=glm5_2_nv,dsv4p_nv,dsv4f_nv,dsv4f0731_nv`,
  TIER_TIMEOUT_BUDGET_S=180, BUFFER_MAX_RETRIES=5, BUFFER_CALLERS=cc4101-fallback;
  `upstream.py:2577` gate 扩展 `dsv4f0731_nv` → pexec→integrate dynamic 兜底。
- **cc4101**: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, PRIMARY_UPSTREAM_URL=http://dsvf0731_nv40666:40666/v1/messages,
  FALLBACK_UPSTREAM_MODEL=glm5_2_nv, FALLBACK_UPSTREAM_URL=http://nv_gw:40006/v1/messages,
  CC4101_STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400, PRIMARY_FAIL_THRESHOLD=3,
  PRIMARY_SKIP_S=30, UPSTREAM_TIMEOUT=130, UPSTREAM_IDLE_TIMEOUT=150。
- **hm4104 (hermes)**: PRIMARY_URL=dsvf0731_nv40666:40666, PRIMARY_MODEL=dsv4f0731_nv,
  FALLBACK_URL=nv_gw:40006, FALLBACK_MODEL=glm5_2_nv, MS_GW_API_KEY=nv-gw-token (R1247 改)。
- **opclaw4103 (openclaw)**: PRIMARY_URL=dsvf0731_nv40666:40666, PRIMARY_MODEL=dsv4f0731_nv,
  FALLBACK_URL=nv_gw:40006, FALLBACK_MODEL=glm5_2_nv, MS_GW_API_KEY=nv-gw-token (R1247 改)。

## 上轮
R1246 (glm5.2 fid 换 3b9748d8 删死链 b1b22d03, dsv4p 清理, 同 key pexec→integrate 兜底; 全验证生效)
→ **R1247 (40666/nv_gw 各单 fid + integrate 内部兜底, 清理多余 fid, pexec vs integrate 实测, hermes+openclaw 两 agent 链路配置 + 端到端验证; 全通过)**。

## 下一步
1. **观察 30min/1h 窗口**: 两 agent (hermes/openclaw) 新链路 SR、fallback 触发率 (目标 <5%);
   dsv4f0731_nv@40666 主链 + glm5_2_nv@40006 fallback 成功率。
2. **fid 稳定性监控**: 40666 discovery fid 281478d0 与 nv_gw glm5.2 fid 3b9748d8 分布, 是否稳定 200。
3. **pekec 优先 + integrate 兜底**: 观察新 dynamic 兜底是否在真实流量中触发, 触发时是否仍保 SR 目标。
4. **3b9748d8 大上下文监控**: 该 fid 大请求 (200K+) 历史 429 多 — cooldown 频触发时 pos1=b6029a96 备用。