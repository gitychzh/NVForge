---
name: nvcf-pexec-field-semantics
description: NVCF pexec 请求体常需带 model 字段; 404=账号不归属; 400 DEGRADED=服务端后端故障; 全5key同 IP 直连会掩盖 IP 维度
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9f86955b-051d-43b2-9038-4442ccdeff80
---

NVCF pexec `/v2/nvcf/pexec/functions/{fid}` 请求体语义 (2026-07 实测):
- **dsv4p fid 74f02205**: pexec 请求体**必须带 `model` 字段** (`deepseek-ai/deepseek-v4-pro`), 否则 400 "Failed to deserialize...missing field model". 带上后 5/5 200.
- **kimi fid f966661c**: pexec 不需 model 字段, 裸 body 即 5/5 200.
- **glm5_2 fid 3b9748d8**: 400 "DEGRADED function cannot be invoked" — 服务端后端健康探测失败, 所有 key 所有 IP 都同样失败, 客户端无法修, 等 NV 恢复. 
- **minimax fid 88d57e31**: 404 "Not found for account" — 该 fid 不属于当前 5 个 NV 账号. 但 **minimax fid 87ea0ddc (ai-minimax-m3)** 是正确的: HM2测pexec_direct 100% avg1.6s, integrate 93%. (R837本地HM1曾误判DEGRADED, 实为环境瞬时, 见 ).
- **per-function per-key 授权**: K2(KEY2) 对 dsv4p(74f02205) 持续403 "Authorization failed"(2轮×3链路0/6), 但K2对kimi/glm5.2/minimax全可用. 不是所有key对所有function有权限, 5key全测才能暴露. 生产nv_gw的key cycle会跳过无授权组合.
- **202 = 请求接受后端scaling, 非失败**: 并发触发NVCF返回202/504, 串行低频则200. 生产有轮询重试. 裸测脚本把202当失败会低估SR.
- **NVCF function status会波动**: DEGRADED可能瞬时, 单次查询不代表实时可用性, 多环境多时刻重测才定论.

mihomo 出口 IP (HM2 host, docker 经 172.18.0.1 访问):
- 7894 → 134.195.101.193, 7895 → .194, 7896 → .195, 7897 → 103.62.49.162, 7899 → 134.195.101.180
- 全5key走同一 IP (容器直连) 会掩盖 IP 维度问题, 必须 5key 各走不同 IP 才能区分账号问题 vs IP 问题.

容器内调用方式: `docker exec nv_gw python3 -u /tmp/script.py`, 容器有 NVU_KEY1-5 env + PySocks. 脚本用 socks.socksocket set_proxy SOCKS5 172.18.0.1 789x → wrap_socket. 相关: [[nvcf-testing-methodology]]
