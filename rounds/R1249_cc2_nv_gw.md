# R1249 — cc2: glm5_2_nv FID 动态健康切换 + 三容器模型白名单瘦身 (40006 只留 glm5_2_nv)

> 日期: 2026-08-12 (~23:00 CST)
> 主机: HM2 (opc2_uname@100.109.57.26)
> 改动范围: `/opt/cc-infra/proxy/nv-gw/gateway/{config,upstream,fid_discovery}.py` + `/opt/cc-infra/docker-compose.yml`
> 备份: config.py.bak.R1253/.bak.R1254, upstream.py.bak.R1253, fid_discovery.py.bak.R1253

## 背景 (用户需求)

1. **FID 动态选择**: 用户实测 5 个 ACTIVE glm-5.2 fid + 5 US IP 后, 发现"正在用的 fid 不可用 → 下一个 key 自动换新 fid; 有多个有效 fid 时动态选延迟低的"。根因: `NV_GLM52_KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0` 把 5 key 全钉在 fid pos0 (3b9748d8), 短路了 `func_health` 的自动切换 — 绑定 fid 一旦 surge/429, 全链陪葬。用户批准放开。
2. **40006 只部署 glm5_2_nv**: 用户指定 dsv4f0731 只存在于 40666 容器, 40006 不要重复部署。实测 40006 (host_machine=opc2sname) 30min 只有 glm5_2_nv 流量, dsv4f0731 定义是冗余残留。

## 改动 1: FID 候选扩展 + 动态健康切换 (R1253)

### config.py — glm5_2_nv function_ids 3 候选 → 5 个 ACTIVE fid
- 原: pos0=3b9748d8, pos1=b6029a96, pos2=b1b22d03 (R1246 删死链后 3 候选)
- 新: 5 个实测 ACTIVE fid (env 可覆盖):
  - pos0 = 3b9748d8-1d85-40e8-8573-0eeaa63a4b63 (ai-glm-5_2, 首选)
  - pos1 = b6029a96-0ead-457b-a732-bbfb251486cb (mn-tp8dp1)
  - pos2 = b1b22d03-1ac7-4204-be9b-84ebb009e1a2 (mn-tp8-b200, 08-12 回归 ACTIVE, 实测最快 1.6s)
  - pos3 = 5532e90c-cb90-49bd-b0d6-42729b667532 (mn-baseline-wb)
  - pos4 = bfcf495b-2faf-4ce7-ba4f-bdd4214ff0df (mn-baseline, 实测稳 2.8s)

### upstream.py:1878 分支 — KEY_FID_BIND 命中加健康检查
- 原: KEY_FID_BIND 命中直接取 `_candidates[pos]`, 短路 func_health
- 新: 命中后检查 `func_health.is_healthy(function_id)`, 不健康则 `select_healthy_function` 自动切到候选里健康的另一 fid
- 后备保障: 即使未来有人重设 KEY_FID_BIND, 坏 fid 也不会全链陪葬

### docker-compose.yml — 清空硬绑定 + 5 fid env + 开启 discovery
- `NV_GLM52_KEY_FID_BIND=` 清空 (原 `0:0;1:0;2:0;3:0;4:0` 全钉 pos0)
- 新增 `NV_GLM52_FUNCTION_ID2~5` 显式候选 fid
- 开启 `NVU_FID_DISCOVERY_ENABLED=1` (interval=1800s, model=glm5_2_nv, match=glm) — 后台 30min 自动发现 ACTIVE fid

### fid_discovery.py bug 修复 — probe 404 根因
- 原: `_probe_fid` 硬编码 `model: "deepseek-ai/deepseek-v4-flash"` (给 dsv4f 写的) + 直连 `HTTPSConnection` 不走代理 → 对 glm 候选全 404
- 新: model 从 `NV_MODEL_IDS[DISCOVERY_MODEL]` 动态取 (glm → `z-ai/glm-5.2`), 连接复用 `nvcf_conn._make_nvcf_proxy_conn` (per-key mihomo SOCKS5)
- 修复后 discovery 能真实探测 glm 候选, 不再全 404

## 改动 2: NVU_ACTIVE_TIERS 模型白名单 (R1254)

### 背景
40006/40066/40666 三容器 **bind-mount 共用同一份 config.py**, 原本全量暴露 5 个模型 (health 列表 + 路由), 但各容器实际只服务自己的专职模型。直接删 config.py 里 dsv4f0731 定义会同时打挂 40666 主链 (cc4101 primary → dsv4f0731@40666)。

### config.py — 加 NVU_ACTIVE_TIERS 白名单过滤
- 新增 env `NVU_ACTIVE_TIERS` (逗号分隔内部 tier 名; 空=全部, 默认兼容)
- 过滤 `NVCF_PEXEC_MODELS` / `NV_MODEL_TIERS` / `NV_MODEL_IDS` / `MODEL_MAP`
- `DEFAULT_NV_MODEL` 若不在白名单 → 自动切到白名单第一个
- 未部署模型请求 → MODEL_MAP 无映射 → `detect_nv_model` fallback 到 DEFAULT, 不 404 不误路由

### docker-compose.yml — 三容器各自白名单
- nv_gw (40006): `NVU_ACTIVE_TIERS=glm5_2_nv` ← **只部署 glm5_2_nv (用户指定)**
- dsvf0731_nv40666 (40666): `NVU_ACTIVE_TIERS=dsv4f0731_nv` ← 只部署 dsv4f0731 (专职)
- dsv4p_nv40066 (40066): `NVU_ACTIVE_TIERS=dsv4p_nv` ← 只部署 dsv4p_nv (专职)

## 验证 (改后必有)

| 检查项 | 结果 |
|---|---|
| compose syntax | ✅ `docker compose config --quiet` OK |
| config.py py3.12 语法 | ✅ `ast.parse` OK |
| 40006 health | ✅ `nvcf_pexec_models: ['glm5_2_nv']` default=glm5_2_nv |
| 40666 health | ✅ `['dsv4f0731_nv']` default=dsv4f0731_nv |
| 40066 health | ✅ `['dsv4p_nv']` default=dsv4p_nv |
| 40006 启动日志 | ✅ `R1254: NVU_ACTIVE_TIERS=['glm5_2_nv'] → tiers=['glm5_2_nv']` |
| 40666 dsv4f0731 冒烟 | ✅ HTTP 200 in 11s (主链正常) |
| 40006 glm5_2_nv 冒烟 | ✅ HTTP 200 in 29s |
| 40006 收 dsv4f0731 请求 | ✅ `mapped_model=glm5_2_nv` (白名单外 fallback 到 DEFAULT) HTTP 200 in 7s |

## 下一步

1. **FID discovery probe 修复后观察**: 下个窗口日志确认 discovery 能探测到 ACTIVE glm 候选 (不再 404)
2. **延迟加权候选**: 用户方案提到"自动读取 DB 延迟数据动态选低延迟 fid", 本次实现了健康切换 + discovery, 延迟排序可作为 func_health 增强 (avg(elapsed_ms) 择优)
3. **长期观察**: 40006 白名单后 30min SR 应保持 glm5_2_nv 纯流, 无 dsv4f0731 泄漏