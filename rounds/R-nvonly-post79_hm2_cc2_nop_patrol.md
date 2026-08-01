# R-nvonly-post79 — hm2 cc2 NOP 巡检轮

## 元信息
- 日期: 2026-08-02 05:25 CST
- 轮次: R-nvonly-post79
- 改动: 0 (NOP 巡检轮)
- 重启: 0
- 仓库 HEAD: 4be5a4b (post78 已 push), 本轮新增本文件

## 判稳依据
注入的轮前链路分析 (05:22 CST) 与 STATE post78 同构:
- cc2 (cc4101-primary) 30min: 0 req (session 轮前无流量产生)
- 链路健康无故障: /health ok (glm5_2_nv, 5 keys, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv]),
  容器全 Up (nv_gw/cc4101/nv_gw_stable 3h, ms_gw/logs_db 2d)
- 0 cc2 tier error, 0 cc2 buffer/wait/error 日志, 0 stream_total_deadline (6h)
- 其他 caller 数据 (非 cc2 链路):
  - hermes/openclaw 打 dsv4p_nv SR=53.8% (7/13): 4×all_tiers_exhausted + 4×429 + 2×zombie_empty_completion(502)
  - per-IP: 203.10.96.139=7×100%, 其余 IP=0% (egress IP 漂移, 单 IP 限流)
  - per-key: key2=7×200, key3=2×502, key?=4×429 (单 key 限流)
  - **与 cc2 无关** (cc2 走 glm5_2_nv, 不打 dsv4p_nv)
- 三阈值: cc2 SR=0req(无数据, 链路健康), 新错误=无, transport=0错, buffer=无触发, deadline(6h)=0次
- → **NOP 巡检轮**, 不改码, 不重启.

## 健康验证 (05:25 CST)
| 验证项 | 结果 |
|--------|------|
| nv_gw `/health` | status=ok, nv_default_model=glm5_2_nv, nv_num_keys=5, pexec=[kimi_nv,dsv4p_nv,glm5_2_nv] ✓ |
| docker ps | nv_gw/cc4101/nv_gw_stable Up 3h, ms_gw/logs_db 2d ✓ |
| 配置 | NVU_DISABLE_MS_FALLBACK=0 (fallback 已恢复), FALLBACK_UPSTREAM=ms_gw:40007 ✓ |

## 下一步
- 继续 NOP 巡检. 等 cc2 有流量时再判 SR.
- dsv4p_nv 低 SR 是 NVCF 侧限流, 非 cc2 链路 (cc2 走 glm5_2_nv), 不在本轮优化范围.
