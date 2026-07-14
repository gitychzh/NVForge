---
name: nv-model-testing-must-be-remote
description: "NV模型链路测试必须在远程HM2上跑, 不能本地HM1; minimax-m3实际可用, 本地测出DEGRADED是环境/方法问题"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

# NV模型测试必须在远程HM2

**Why:** R837我在HM1本地跑180req矩阵, 测出minimax_m3全400 DEGRADED、glm5.2波动67-87%. 用户纠正: minimax-m3实际是好的, 是我的测试方式/环境有问题; 所有测试必须在远程HM2进行. 本地HM1的egress/account瞬时状态/代理链路与生产HM2不同, 本地结论不可直接外推到生产. NVCF function status(DEGRADED/ACTIVE)会波动, 单次本地查询不代表实时可用性.

**How to apply:**
- NV模型链路测试一律 SSH 到远程HM2 (`ssh -p 222 opc2_uname@100.109.57.26`) 上跑, 不在本地HM1跑.
- 见 [[remote-host-ssh-access]] [[host-roles-and-self-positioning]].
- 测出某模型"不可用"前先质疑环境: 多环境多key多轮重测, 单次DEGRADED/404/timeout不等于真不可用 — 见 [[nvcf-testing-methodology]].
- minimax_m3_nv(fid 87ea0ddc) 用户确认实际可用, 之前DEGRADED是瞬时/环境误判.
- glm5.2测试: 用5个不同美国IP, 以nvidia.com测延迟筛选5个最低节点, 再跑integrate+pexec矩阵.
- kimi/dsv4p切直连: 同意, 但每次关注function_id是否变化(NVCF会上下架fid).

## 相关记忆
[[nvcf-testing-methodology]] [[nvcf-pexec-field-semantics]] [[remote-host-ssh-access]] [[host-roles-and-self-positioning]]
