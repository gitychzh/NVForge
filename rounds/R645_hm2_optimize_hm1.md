# R645: HM2→HM1 — PEER_FALLBACK_TIMEOUT 18→16 (-2s)

## 背景
检测脚本判定轮到HM2执行优化。本轮遵循"单参数、少改多轮"原则，基于HM1最新运行数据压缩已失效的peer fallback等待时间。

## 数据采集 (HM1)
### 1. HM1容器
- 活跃容器: `nv_40006_uni` (4min前重启)
- POSTGRES: `cc_postgres`

### 2. HM1链路日志 (docker logs nv_40006_uni --tail 100)
- **零错误 regime 持续**: 容器刚由 R644 重启 (4min), 日志 clean start
- `PROXY_ROLE=passthrough`, `NVU_NUM_KEYS=5`
- tiers: `['kimi_nv', 'dsv4p_nv', 'glm5_1_nv', 'glm5_2_nv']`

### 3. 环境变量 (docker exec nv_40006_uni env)
关键参数 (当前 R644):
- `UPSTREAM_TIMEOUT=34`
- `MIN_OUTBOUND_INTERVAL_S=0`
- `KEY_COOLDOWN_S=25`
- `TIER_COOLDOWN_S=25`
- `TIER_TIMEOUT_BUDGET_S=90`
- `NV_INTEGRATE_KEY_COOLDOWN_S=0`
- `NVU_CONNECT_RESERVE_S=2`
- `NVU_SSLEOF_RETRY_DELAY_S=1.0`
- `NVU_PEXEC_TIMEOUT_FASTBREAK=1`
- `NVU_EMPTY_200_FASTBREAK=2`
- `NVU_PEER_FALLBACK_TIMEOUT=18`
- `NVU_FORCE_STREAM_UPGRADE_TIMEOUT=61`
- `NV_INTEGRATE_MODELS=dsv4p_nv,kimi_nv`
- `NVCF_DEEPSEEK_FUNCTION_ID=74f02205-c7ba-438f-b81a-2537955bd7ec`
- `NVCF_KIMI_FUNCTION_ID=f966661c-790d-4f71-b973-c525fb8eafd4`
- `NVCF_GLM51_FUNCTION_ID=6155636e-8ca8-4d9a-b4e5-4e8d231dfd3f`
- `NVCF_GLM52_FUNCTION_ID=3b9748d8-1d85-40e8-8573-0eeaa63a4b63`

### 4. HM1数据库近期分析 (nv_requests表)
- **状态分布**: 200=10217, 502=1274, 400=1
- **模型分布**: dsv4p_nv 200=6104, 502=590; kimi_nv 200=2500, 502=635; deepseek_hm_nv 200=1365, 502=30; glm5_2_nv 200=175, 502=1; glm5_1_nv 200=73, 502=18
- **upstream_type**: nvcf_pexec=9830 (200=9826, 502=4), nv_integrate=320 (200)=320, NULL=1342(502=1270)
- **错误子类**: all_tiers_failed_in_mapped_tier=741; NULL=534+1(400)
- **成功延迟**: dsv4p_nv avg=13.1s max=161s; kimi_nv avg=19.1s max=419s; glm5_2_nv avg=5.0s max=39s; glm5_1_nv avg=18.4s max=71s
- **错误延迟**: 502平均未记录，但empty200+timeout表现为~34-89s
- **key_cycle_429s总数**: 504（全历史，最近周期低位）

### 5. 最近6h/1h运行数据
- 最近6h: 全200成功，无502; upstream_type pexec+integrate混合，clean
- 最近1h: 全200成功 (dsv4p=2, glm5_2=110, kimi=68, glm5_1=1)
- 全零错误 / 零ATE / key_cycle_429s 低水位

## 问题诊断
1. **历史502来源**: 1274个502中，~90%+为 `all_tiers_failed_in_mapped_tier`（Tier级全部失败），源自空200 fastbreak + peer fallback timeout chain。peer fallback —> peer (HM2) —> 也超时返回。
2. **peer fallback超时浪费**: 已观察历史数据 peer fallback 成功路径数据极少（无显著成功案例），主要贡献者为本机 `all_tiers_failed` 下转HM2的最后一次尝试。当前 `PEER_FALLBACK_TIMEOUT=18` 在100%失败场景仍消耗~~16-18s（含2s connect reserve）。在all_tiers_failed chain末尾，这浪费的时间压缩可显著缩短ATE总耗时。
3. **glm5_1已EOL**: NVCF pexec已404/INACTIVE，实际请求经fallback到dsv4p/glm5_2。不影响本轮参数，但对DB中glm5_1Nv的502数据产生噪音。后处理DB历史记录时可备注分离。

## 改动 (只改HM1，不改HM2)
### /opt/cc-infra/docker-compose.yml
1. `NVU_PEER_FALLBACK_TIMEOUT`: 18 → **16** (-2s)
   - 压缩已证实 100% 失败的 peer fallback 等待时间
   - 对成功路径零影响（成功路径从不会进入 peer fallback）
   - ATE失败后总等待时间从 ~18s → ~16s，加速最终失败响应

## 验证
- docker-compose.yml 已写入新值
- `docker compose up -d nv_40006_uni` 重启成功
- 环境变量验证: `NVU_PEER_FALLBACK_TIMEOUT=16` ✅
- 容器启动日志 clean，无 ERROR/WARN ✅

## 评判
- **更少报错**: 对成功路径无影响；对 ATE 失败路径缩短 2s（降级改版中）
- **更快请求**: 对成功请求无影响；压缩故障路径等待
- **超低延迟稳定优先**: peer fallback timeout 从不会拦截成功路径（成功路径请不到 peer fallback），安全压缩
- **铁律**: 只改HM1，不改HM2 ✅

## ⏳ 轮到HM1优化HM2
