---
name: glm52-function-id-fact
description: glm5.2在远程账号只有1个可用function(3b9748d8 ACTIVE); 5_1两个全404 INACTIVE无version; 5key同租户function集相同; 凑不齐5个
metadata: 
  node_type: memory
  type: project
  originSessionId: 8fd3e5ef-956b-47c8-bc05-6cf506d1c4aa
---

2026-07-13 实测 (远程 HM2). **glm5.2 在该 NVCF 账号下只有 1 个可用 function, 无法凑 5 个.**

**listFunctions API** (`GET https://api.nvcf.nvidia.com/v2/nvcf/functions`, Bearer key):
- 5 个 NVU_KEY 全部返回 **完全相同的 177 个 function** 集合 → 5 key 同租户, 看到同一个 function 池.
- glm 相关 function 仅 3 个:

| function_id | name | status | 备注 |
|---|---|---|---|
| `3b9748d8-1d85-40e8-8573-0eeaa63a4b63` | ai-glm-5_2 | **ACTIVE** | 唯一可用; versionId `e03df1e6-9e31-4d34-97d2-477f85a9fb05`; `ownedByDifferentAccount:true` |
| `af904f0c-594b-4fdf-af57-dbe5946868d5` | dynamo-glm-5_1 | INACTIVE | pexec 全出口 **404 "version 'null': Specified..."** (无可用 version) |
| `46f4fb53-0b89-4970-8c4b-6959d0e6ecb4` | dynamo-hicache-glm-5_1 | INACTIVE | 同上, 全 404 |

**结论: "挑 5 个最快 function id" 在 glm5.2 上物理只有 1 个候选 (3b9748d8).** 能优化的不是 function id, 而是 key+出口 IP 组合 (见 [[glm52-egress-geo-real-data]]).

**versions API**: `GET /v2/nvcf/functions/{fid}/versions` 每个function仅1个version. 5_2 的 version ACTIVE, 5_1 的 version 不存在(404 version null).

**pexec 5_2 function 多出口表现** (timeout=120s, [[glm52-egress-geo-real-data]]):
- 美国 7894/7899: 200, 2.6-5s ✓✓
- 新加坡 7891: 200, 62.6s ✓ (慢)
- 日本 7892: 202, 64.5s ⚠ (后端scaling, 202非失败但无content)
- direct直连: 504, 63.6s ❌ (后端网关错误)

**function_id 不归属本账号** (ownedByDifferentAccount:true): 说明这是 NVCF 官方公共 function, 5 key 都是被授权调用而非自有部署. 404 version null 对 5_1 可能是账号未开通 5_1 授权.

相关 [[glm52-egress-geo-real-data]] [[integrate-us-exit-glm52-breakthrough]] [[r839-glm52-mode-chain]]
