# R1095 cc2 NOP — 主链 102/102=100% SR, 零错误, fallback 0%; buffer 全 attempt-1 直flush 秒回; 3× zombie 归属 hermes 非主链

> 轮次: R1095  |  日期: 2026-08-07 21:58 CST (13:58 UTC)  |  容器: nv_gw Up 23h, cc4101 Up 18h
> 类型: **NOP 巡检轮 / 不改码**

## 判定: 清洁 NOP

30min 主链 (nv_gw:40006, 现 primary model=dsv4f0731_nv) cc2 专属全绿, 无 502, 无 fallback, 无新错误(cc2 专属)。SR 100%。

## 数据 (DB/日志实测 2026-08-07 21:58 CST)

### 30min nv_requests (caller × status)
| caller | model | status | count |
|---|---|---|---|
| cc4101-primary | dsv4f0731_nv | 200 | 102 |
| hermes | dsv4f0731_nv | 200 | 30 |
| hermes | dsv4f0731_nv | 502 | 3 |
| **cc2 专属 (cc4101-primary)** | | 200 | **102/102 = 100.0%** |

- **cc2 主链 (cc4101-primary) 零错误**: 错误分类 `(cc2 专属 0 rows)`
- 唯一 502 全部归属 **hermes**: 3× `zombie_empty_completion` (bc925d33 66s / 8cc82d57 5.5s / 322b7d2f 3s),
  tier_model=dsv4f0731_nv, upstream_type=nvcf_pexec, egress 134.195.101.197/193 — **peer caller, 非 cc2 优化范围**

### cc_requests 真实 SR (含 fallback)
```
total | ok | fb | sr
  103 |103 |  0 | 100.0
```
- **103/103 = 100.0%**, fallback 0/103 = **0.0%** — 零 fallback, 全走主链

### tier 错误 (nv_tier_attempts 30min)
```
pexec_success               | 102
empty_200                   | 1  (k4 一次性)
NVCFPexecRemoteDisconnected | 1  (k2 一次性)
```
- 5 key 全 pexec_success; 仅 2 个一次性 transient (k4 empty_200, k2 RD), 非分布, 无持续 tier 错误

### buffer 日志 (--since 30m)
- cc2 请求全 attempt-1 直flush 9-11s (success_tool_call), 零重试, 零 502, 零 buffer_exhausted, 零 WAIT 挂起
- 例: req=93f83c82 attempt-1 flush 13252b elapsed=8s; req=ae0e319d flush 2987b 9.8s; req=fa85824e flush 19350b 11.3s

### 容器 /health (2026-08-07 21:58 CST)
- nv_gw 40006: `{"status":"ok","nv_num_keys":5,"nvcf_pexec_models":[kimi_nv,dsv4p_nv,dsv4f_nv,dsv4f0731_nv,glm5_2_nv],"nv_default_model":"glm5_2_nv"}` — 200
- nv_gw env: NV_GLM52_MODE_CHAIN=pexec_us_rr, KEY_MODE_BINDING= 空, NV_INTEGRATE_MODELS=glm5_2_nv, NVU_DISABLE_MS_FALLBACK=0 (ms_gw fallback 恢复期中)
- 容器: nv_gw Up 23h, cc4101 Up 18h

## 配置观察 (记录, 不改)
- 现运行几何: cc4101.**PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv** (非 CLAUDE.md 历史 glm5_2_nv 描述), PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, FALLBACK 指 ms_gw 40007。
- nv_gw 侧多 model nvcf_pexec (kimi_nv/dsv4p_nv/dsv4f_nv/dsv4f0731_nv/glm5_2_nv), default=glm5_2_nv。
- cc2 主链实际经 nv_gw 走 dsv4f0731_nv, buffer 直flush 健康。**以 env + DB 铁证为准, 不改**。

## 下一步
- 保持 NOP 观察。cc2 主链 100% SR 零错误零 fallback, buffer 全 attempt-1 直flush, 无参数可调。
- **3× zombie_empty_completion 归属 hermes (dsv4f0731_nv 线, egress 134.195.101.x)** — peer caller 非 cc2 优化范围, 不计入 cc2 指标。
  若后续多轮 hermes zombie 持续复发, 归属权用 request_id JOIN nv_tier_attempts 复核 (记忆: bad-fid/越界容器 归属判 hermes)。本轮不动作。
- 若 egress IP (代理线路) 多轮连续失败不再 attempt-1 直flush, 才查 mihomo 端口。

## 参数快照 (未动, 与 R1094 一致)
- 与 R1094 完全一致, 无任何改动。见 R1093 参数快照。
