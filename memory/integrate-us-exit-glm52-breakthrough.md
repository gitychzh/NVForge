---
name: integrate-us-exit-glm52-breakthrough
description: "integrate对glm5_2美国出口最快(2.7s); 2026-07-13修正:并非只接受美国,直连/日本也能通但慢60-80s, 旧40s卡死是timeout太短误判"
metadata:
  node_type: memory
  type: project
  originSessionId: 7826648e-45db-49ea-9bef-2d1a605e19d5
---

2026-07-08 22:40 深挖integrate链路发现 (远程opc2sname)。**2026-07-13 修正见末尾,推翻"只接受美国"的绝对结论。**

**原结论 (2026-07-08): integrate.api.nvidia.com 对 z-ai/glm-5.2 有地理限制, 只接受美国出口IP。**

实测端口-出口IP映射 (mihomo ~/.config/mihomo/config.yaml):
- 7891=新加坡(203.27.106.146) → 原: 40s卡死超时
- 7892=日本(103.62.49.138) → 原: 40s卡死超时
- 7894=美国A(134.195.101.193) → integrate 200, 3-6s
- 7896=美国B(134.195.101.195) → integrate 200, 3-6s
- 7899=美国C(134.195.101.180) → integrate 200, 1.7-5.4s
- **无台湾节点** (provider只有日本东京/新加坡/美国旧金山)

**07-08 完整测试数据 (美国出口):**
- 5key × 3美国出口 × 流式thinking(15次): 14/15成功(1次k4@7899偶发30s超时, 重测5/5通)
- 5key thinking(chat_template_kwargs.enable_thinking): 5/5, reasoning_content 92-99字
- 大max_tokens=200 thinking+content: 3/3, 两者同时完整(content="2+2=4", rc="1. Analyze...")
- 流式: 3/3, ttfb 0.36-0.38s

**推翻的旧结论:**
1. ~~integrate对glm5_2不可用~~ → 假, JP/SG出口慢但非不可用
2. ~~glm5_2 thinking路径504~~ → 只对pexec 3b9748d8成立; integrate的thinking完全健康

**对比 pexec 链路 (nv_gw现状)**: 成功率0-33%, ttfb 40-70s, R797已关thinking(inject:{}). integrate+美国出口全面碾压。

**架构关键**: nv_gw `_try_integrate_keys` (upstream.py) 已支持per-key代理, 调用 `_make_nvcf_proxy_conn(proxy_url, nvcf_host=NV_INTEGRATE_HOST)` (nvcf_conn.py). 但integrate与pexec共用 `NVU_PROXY_URLS[key_idx]`. 当前 `NVU_PROXY_URL1~5`全空→全直连. `NV_INTEGRATE_MODELS=`(空)把integrate关了, R839接管 glm5_2_nv.

---

## 2026-07-13 修正 (timeout=120s 重测, 推翻"只接受美国出口")

用 timeout=120s 重测 integrate 多出口, **推翻"只接受美国出口"的绝对结论**:
- **direct直连 → 200, 80s** ✓ (之前 timeout=40 误判为"卡死")
- **7892 日本 → 200, 66.4s** ✓ (之前 timeout=40 误判)
- 7899 美国B → 200, 2.7s ✓✓ 最快
- 7894 美国A → curl HTTP 000 (curl经mihomo瞬时连接问题, 非真实失败; python urllib 路径之前测 200)

**真相**: integrate 对 glm5_2 **不限制地理**, 美国/日本/直连都能通. 只是**美国出口快 (2.7-5s), 日本/直连慢 (60-80s)**. 之前说"JP/SG卡死"是 timeout=40 太短, 实际是慢响应 (60-80s) 被误判为卡死.

**测试方法学教训**: NVCF/integrate glm5_2 慢响应可达 60-80s, 测速 timeout 必须 ≥120s, 否则会把"慢"误判为"不可用". 见 [[nvcf-testing-methodology]].

相关 [[nvcf-testing-methodology]] [[nvcf-pexec-field-semantics]] [[glm52-egress-geo-real-data]] [[glm52-function-id-fact]]
