# R1245 cc2 模型链路切换 — primary=dsv4f0731_nv@40666, fallback=glm5_2_nv@40006

**日期**: 2026-08-10 05:51 CST (2026-08-09 21:51 UTC)
**结论**: **内容改动** (非 NOP) — 用户指定, 重设 cc2 链路:
- **primary** = `dsvf0731_nv40666:40666/v1/messages` (dsv4f0731_nv, fid 281478d0)
- **fallback** = `nv_gw:40006/v1/messages` (glm5_2_nv)
- 原 primary (nv_gw:40006 dsv4f0731) 降级为 fallback; 原 fallback (ms_gw:40007 glm5_2_ms) 移除。
- 端到端实测两链路均 **200 OK 生效** (primary 1.4-2.6s / fallback 73.5s)。

## 背景与依据 (改前数据, 铁律 1)

用户要求"cc→cc4101→dsv4f0731_nv40666(默认), glm5.2_nv40006(fallback)"。改前核实全部拓扑:
- **40666 (`dsvf0731_nv40666` 容器)** 与 cc4101 同 `cc-infra_cc-net` (cc4101=172.18.0.8, 40666=172.18.0.4), DNS 直达。
- 实测 40666 `/v1/messages + dsv4f0731_nv` → **200 OK, 0.7-3.1s, fid 281478d0** (acture healthy, ACTIVE per NVCF catalog)。
- 实测 40006 `/v1/messages + glm5_2_nv` → **200 OK, 78s** (integrate 通道; glm5.2 慢但可兜底)。
- 对比基线: 40666 dsv4f0731 快 (0.7s) vs 40006 glm5.2 慢 (78s) — primary 用快的 40666 合理。
- 40006 之前 n_gw 主链也走 dsv4f0731 (281478d0), 现改让 40006 专为 fallback 服务 glm5.2。

## 改动 (只改 cc4101 compose env, 铁律 3 只碰 nv 链)

`/opt/cc-infra/docker-compose.yml` cc4101 服务 (备份 `.bak.R1244`):
```
PRIMARY_UPSTREAM_URL   nv_gw:40006         → dsvf0731_nv40666:40666/v1/messages
PRIMARY_UPSTREAM_MODEL dsv4f0731_nv        (不变)
PRIMARY_UPSTREAM_TOKEN nv-gw-token         (不变)
FALLBACK_UPSTREAM_URL  ms_gw:40007         → nv_gw:40006/v1/messages
FALLBACK_UPSTREAM_MODEL glm5_2_ms          → glm5_2_nv
FALLBACK_UPSTREAM_TOKEN ms-gw-token        → nv-gw-token
depends_on: + dsvf0731_nv40666 (primary target)
```
格式: cc4101 透传 Anthropic /v1/messages body, 仅改 model 字段做路由 (R1705)。两 upstream 均用 `/v1/messages` (Anthropic), 格式一致。
应用: `docker compose up -d cc4101` (env 改动必须 up -d, 铁律 6)。容器 Recreated + Started。

## 验证 (端到端两链路, 铁律 2)

**primary (40666 dsv4f0731)** — 配置生效后, cc4101 发 `claude-opus-5`→dsv4f0731_nv:
```
curl 4101 /v1/messages → 200, dur=1.37s, model=dsv4f0731_nv, content="OK"
DB nv_requests: caller=cc4101-primary host=opc2sname-dsv4f40666 mapped=dsv4f0731_nv fid=281478d0 → 200
```
**fallback (40006 glm5.2)** — 临时 `docker stop dsvf0731_nv40666` 触发 primary conn 失败 → 立即 fallback:
```
curl 4101 /v1/messages → 200, dur=73.5s, model=glm5_2_nv, content="OK"
DB cc_requests: upstream_used=fallback, primary_error_type=conn (40666 已停), mapped=glm5_2_nv → 200
DB nv_requests: caller=cc4101-fallback host=opc2sname mapped=glm5_2_nv → 200
```
`docker start dsvf0731_nv40666` 恢复, 复测 primary 再回 40666 dsv4f0731 → 200 (2.6s, host=opc2sname-dsv4f40666, fid 281478d0)。

**容器健康**: 4101 / 40006 / 40666 全 `/health` ok。cc4101 env 复核生效 (上面新 6 项)。

## 判定
链路切换成功, 双链路端到端 200 OK 生效。primary=40666 dsv4f0731 (快, 0.7-3s), fallback=40006 glm5.2 (慢 73-104s 但兜底可用)。dsv4p_nv (deepseek-v4-pro) 已 EOL (NVCF 410 Gone, 见前一调查), 不再涉及。

## 下一步观察点
1. 观察下一窗 cc2-primary SR — 期望 dsv4f0731@40666 维持高 SR (此前 40006 dsv4f0731 ~93-98%)。
2. fallback 触发率 — 40666 健康时应 <5%; 若 40666 频繁 fail 致 fallback 到慢 glm5.2, 再评估 40666 自身健康。
3. glm5.2@40006 慢 (73-104s) — 兜底可接受, 但提升其 pexec/健康或保持 dsv4f 为主是后续杠杆。