---
name: glm52-speedtest-cron
description: "GLM5.2定时测速脚本每天2:00/14:00跑5mode排名, 不影响生产(直打端点不走nv_gw), 输出jsonl+建议mode_chain, HM2已部署cron"
metadata: 
  node_type: memory
  type: project
  originSessionId: c3734594-fcf5-43ff-9b8d-e14d8c206a00
---

# GLM5.2 定时测速脚本 (2026-07-11 部署, HM2)

用户要求: 每天凌晨2:00+下午14:00 各跑一遍5mode测速, 选最优→最次排名保留5候选, 启动期间不影响生产.

## 部署位置 (HM2, 用户级无需sudo)
- 脚本: `/home/opc2_uname/scripts/glm52_speedtest.py`
- 日志: `/home/opc2_uname/glm52-speedtest.jsonl` (jsonl, 每跑1次追加1条)
- cron日志: `/home/opc2_uname/glm52-speedtest/cron.log`
- crontab (opc2_uname用户级): `0 2 * * * /usr/bin/python3 /home/opc2_uname/scripts/glm52_speedtest.py >> /home/opc2_uname/glm52-speedtest/cron.log 2>&1` + `0 14 * * *` 同款

## 脚本行为 (不影响生产铁律)
- 直打 NVCF pexec端点(fid 3b9748d8) / integrate端点(integrate.api.nvidia.com), **不走nv_gw**, 不改任何配置
- 5 mode各测5次(N=5), 串行低并发, key按rep%5轮, 用容器内NVU_KEYS
- egress实测: direct + 5 mihomo端口(7894-7899) 各测出口IP
- 排名: SR高优先, 同SR则avg低优先
- 输出: 控制台排名 + suggested NV_GLM52_MODE_CHAIN(最优在前) + jsonl追加
- jsonl字段: ts/egress_map/results(25条)/ranking(5条)/suggested_chain

## 5 mode定义 (与[[r839-glm52-mode-chain]]一致)
1. pexec_direct (pexec+直连)
2. pexec_us_rr (pexec+5美国IP轮换 7894-7899)
3. integrate_us_rr (integrate+5美国IP轮换)
4. pexec_us_single (pexec+单IP 7894→193)
5. integrate_us_single (integrate+单IP 7894→193)

## 历史测速结果 (jsonl累积, 看趋势)
- 2026-07-11首次(verify): 全100%SR, #1 integrate_us_single(1.25s) > #2 pexec_us_rr(1.53s) > #3 integrate_us_rr(2.11s) > #4 pexec_us_single(2.19s) > #5 pexec_direct(4.42s)
- 早先矩阵(同日): pexec_direct HM2=0.84s最快 → 印证"今天稳明天不稳", 定时测速必要

## 用途
- 给 R839 (glm5_2_nv per-key-mode动态递进) 提供 mode_chain 顺序参考: 按最近测速排名配 NV_GLM52_MODE_CHAIN
- 长期jsonl可看每mode稳定性趋势, 找出"今天稳的mode"
- 不影响生产: 完全独立测试, 25req/次, ~3-5min跑完

## HM1 同步 (待做, R839落地时)
HM1 部署同款脚本+cron (路径 /home/opc_uname/scripts/). 两机各自测速, 对比mode排名差异.
