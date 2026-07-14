---
name: nvcf-testing-methodology
description: "NVCF 模型可用性测试必须全方位(integrate+pexec 双通道×5key×5IP×stream), 单通道判定\"不可用\"是错误"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9f86955b-051d-43b2-9038-4442ccdeff80
---

测试 NV 上某模型是否可用时, 必须用多维度矩阵, 缺一不可:
1. **integrate 通道** `https://integrate.api.nvidia.com/v1/chat/completions`, body 带字段 `"model": "<org>/<model>"` (如 `minimaxai/minimax-m3`, `moonshotai/kimi-k2.6`, `deepseek-ai/deepseek-v4-pro`, `z-ai/glm-5.2`)
2. **NVCF pexec 通道** `/v2/nvcf/pexec/functions/{function_id}` on api.nvcf.nvidia.com
3. **5 个 key** (NVU_KEY1-5) 各走**不同 mihomo 出口 IP** (HM2 端口 7894/7895/7896/7897/7899 → 5 个 US-NV IP)
4. reasoning 模型 (dsv4p/glm5.2) 用 **stream=True 读首 chunk** 判定可用性, 非 stream + 30s timeout 会误判超时
5. pexec 请求体**必须带 `model` 字段**, 否则 400 "missing field model" (dsv4p 即如此)
6. socks5 代理偶发 SSLEOFError, conn() 必须 retry (3 次, 间隔 2s)

**Why:** 我曾只测 pexec 单通道 (同一直连 IP) 判定 minimax-m3 "不可用" (400 Inference error), 但用户亲测确认可用. 全方位重测发现: minimax 经 integrate 通道 5/5 200 OK 完全可用. 我之前是偷懒/方法缺陷.

**How to apply:** 判定任何 NV 模型"不可用"前, 必须同时测 integrate + pexec 两通道全 5key×5IP. pexec 404 "Not found for account" = function id 不属于该账号 (账号-归属问题, 非模型问题). pexec 400 "missing field model" = 请求体缺字段 (修请求体即可, 非模型问题). pexec 400 "DEGRADED function cannot be invoked" = NV 服务端 function 后端健康探测失败 (服务端问题, 客户端无法修). 只有 integrate+pexec 双通道全 fail 才能说模型不可用. 相关: [[shared-source-cross-host]] [[github-ssh-via-443-mihomo]]
