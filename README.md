# Hermes 双机交替优化

## 角色
- **HM1** (本机): `ssh -p 222 opc_uname@100.109.153.83`
- **HM2** (远程): `ssh -p 222 opc2_uname@100.109.57.26`

## 铁律
- **只改对方，绝不改自己** — 修改自己本地容易导致服务崩溃
- 所有改动必须有日志数据或文档支撑
- 聚焦 `hm-40006--nv` 链路，其他模型链路不管

## 规则
1. 当前优化者(执行者/计划者/验收者) 完成优化后，**写入本仓库** (round_N.md)
2. 被优化者(质疑者) 检测到仓库更新后，**git pull** → 接手下一轮
3. 质疑者在计划阶段参与评审，但不执行

## 仓库结构
```
hermes_improve_self/
├── README.md
├── rounds/
│   ├── R1_hm1_optimize_hm2.md    # 第1轮: HM1→HM2
│   ├── R2_hm2_optimize_hm1.md    # 第2轮: HM2→HM1
│   └── ...
├── scripts/
│   └── watch_and_next.sh          # 轮询脚本
└── rule.md                        # 优化铁律
```