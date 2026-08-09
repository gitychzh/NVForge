---
name: glm52-integrate-geo-restriction-confirmed
description: "glm5.2 经 NVCF integrate 的 chat 调用有地理限制,日本出口静默超时;只读 models 接口不限地理易误判"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3c8d8f5f-50f9-4f31-9c0c-b1eae74a0183
---

# GLM5.2 NVCF integrate 地理限制确认(R856 实测)

**铁证(2026-07-14 23:50 实测)**: NVCF integrate.api.nvidia.com 对 `z-ai/glm-5.2` 的 **chat completions 调用有地理限制**,只接受美国出口 IP。

交叉测试矩阵(经 mihomo socks5):
- 美国节点(7895)+任意NV key → **OK** "Hi there! I'm the GLM language model"(1.5-10s)
- 日本节点(7894,出口103.62.49.138)+任意NV key → **5/5 全超时**(25s 0字节)
- 日本节点 + /v1/models(只读列表) → **正常返回**(models 列表能拿到)

**坑**: 只读 models 接口不查地理,所以"日本节点能连 NVCF"是假象——chat 调用被静默挡住(不返明确错误,直接超时/空)。这推翻了旧记忆 [[glm52-egress-geo-real-data]] 里"integrate 不限地理"的错误结论。

**故障案例(R856)**: 我在调查 mid-response 错误时手动把 mihomo ♻️US-NV-K1 切到 `🇯🇵AWS日本01`,导致 K1(7894)走日本出口 → glm5_2_nv 每5次 chat 调用全超时 → nv_gw 5 key 全失败 → ABORT-NO-FALLBACK 502 → CC 报 "Server error mid-response"。23:44-23:54 集中爆发约20次 STREAMBREAK/TIMEOUT。切回 `🇺🇸美国洛杉矶08 | 三网推荐` 后 23:55 起立即恢复,5/5 OK,真实CC模拟5/5 OK。

**教训**:
- 调查 mihomo 时**绝不能把生产 K 组切到日本/新加坡节点**做测速——会直接搞坏 glm5_2_nv 生产路径。要测地理只在不影响生产的独立测试里做。
- K1-K5 必须全部指向美国节点(美国出口 IP 段 134.195.101.x = Linode/Akamai 美国)。
- `🇺🇸美国圣何塞01-07 | 三网推荐` 2026-07-14 实测全 down(5s 超时),不可用;`🇺🇸美国洛杉矶08 | 三网推荐` 可用(7-8s);0.1倍美国节点当前可用(6-8s)。
- R827 记忆里"integrate 对 glm5_2 有地理限制,需美国代理"是对的,本条是其铁证补全。
