# R1144 cc2 NOP 巡检轮 (不改码)

- 时间: 2026-08-08 01:40 CST
- 判定: **NOP** — 30min 主链零表面错误, cc2-primary 100% SR, fallback 0%, 无新错误
- 容器: nv_gw 22h, cc4101 22h, dsv4p_nv40066 3d (稳定未重启)

## 轮前链路数据 (2026-08-08 01:30 注入)

**30min 链路总览 (caller × model × status):**
```
cc4101-primary|dsv4f0731_nv|200|109     ← cc2 的请求
hermes|dsv4f0731_nv|200|20
hermes|dsv4f0731_nv|502|1
```

**30min cc4101-primary 专属 (cc2):** `200|109` = **0 行非-200, 100% SR**

**30min 错误分类 (type × sub × count × avg_dur):**
```
NVStream_IncompleteRead||1|55488
```
→ 唯一 surface 错误 (502, 55.5s) **归属 hermes**, cc2 0 行

**30min fallback:** `f|130` = 130 行 0 触发 = **0%** (未走 ms_gw)

**30min per-key tier 错误:**
```
0|NVCFPexecRemoteDisconnected|1
1|NVCFPexecRemoteDisconnected|1
2|NVCFPexecRemoteDisconnected|1
2|empty_200|1
3|NVCFPexecRemoteDisconnected|1
4|NVCFPexecRemoteDisconnected|3
```
→ RD 各 key 1×(+k4 3×) + empty_200 1× (k2) — 分布式单点 self-heal, 无同 key 连续复发, 未上浮 surface (延续 [[ssleof-error-transient-egress-blip]], [[k3-transient-execute-failed-self-heal]])

**buffer/wait 日志:** 无 (本轮 buffer 全 direct flush, 无 WAIT/无 exhaust)

## 判定理由

- cc2-primary 30min = 200|109, **0 行非-200, 100% SR** — 主链全绿。
- 唯一 surface 错误 NVStream_IncompleteRead 1× (502) **归属 hermes** (dsv4f0731_nv 本线), 非 cc2 范围。
- fallback 0% (130 行 0 触发) — 未触发 ms_gw。
- tier RD (k0/k1/k2/k3/k4) + empty_200 (k2) 分布式单点 self-heal, 未上浮 surface, 属稳态低频下沉。
- 本轮 buffer 无 execute_failed 日志 (较 R1143 的 5× 更干净), 全部 direct flush。
- 容器 22h~3d 稳定运行, 无重启。

→ **cc2 范围无配置回归, 不改码。取 NOP。**

## 容器健康验证

```
nv_gw /health: {"status":"ok","proxy_role":"passthrough","nv_num_keys":5,...} ✅
nv_gw: Up 22 hours    cc4101: Up 22 hours    dsv4p_nv40066: Up 3 days ✅
```

## 下一步

- 延续 NOP。主链滚动 30min 零表面错误、fallback 0%、buffer 无 WAIT/无 exhaust。
- 持续观察 tier RD / empty_200 分布式单点。若无同 key 多请求连续复发、不影响 surface, 继续 NOP。
- 若同 key RD/execute_failed 回升且浮上 surface (cc2 非-200 出现), 再查 mihomo 对应线路。
- hermes 侧 IncompleteRead 归 hermes 线, 非 cc2 范围, 不处理。