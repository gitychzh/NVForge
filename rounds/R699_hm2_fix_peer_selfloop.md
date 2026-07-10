# R699: HM2 PEER_FALLBACK_URL 自环bug修复

## 时间
2026-07-05 01:10 CST

## 发现
HM2 (100.109.57.26) 的 `NVU_PEER_FALLBACK_URL` 指向 `http://100.109.57.26:40006` —— **HM2自身的Tailscale IP**！

这造成了一个**自环循环**：
1. HM2 本地 all_tiers_exhausted (ATE)
2. 触发 peer fallback → 调用自己 (100.109.57.26 = HM2)
3. 自身再次 ATE → 返回 502
4. peer fallback 失败 → 最终返回 502 给用户

## 根因
- R683 的注释声称 "HM2 peer fallback URL 修自环后恢复互备"，但 `docker-compose.yml` 从未实际更改
- HM2 的 compose 文件中 `NVU_PEER_FALLBACK_URL` 一直保持 `100.109.57.26` (自身IP)
- 容器从未被 force-recreate，所以即使 compose 被改过也从未生效

## 影响 (Jul 4 数据)
- 112 次 502 all_tiers_exhausted 失败
- 平均时长 45530ms (应为 ~25s = PEER_FALLBACK_TIMEOUT)
- 最大时长 154098ms (= 6x PEER_FALLBACK_TIMEOUT，自环级联超时)
- peer fallback 从未成功过 (因为调用自己必然失败)

## 修复
`/opt/cc-infra/docker-compose.yml` line 507:
```
# 旧值 (自环bug):
NVU_PEER_FALLBACK_URL: http://100.109.57.26:40006
# 新值 (修复):
NVU_PEER_FALLBACK_URL: http://100.109.153.83:40006  # HM1 IP
```

## 验证 (4-way consistency)
| Source | Value | Status |
|--------|-------|--------|
| Container env | `http://100.109.153.83:40006` | ✅ |
| Compose file | `http://100.109.153.83:40006` | ✅ |
| Container status | `Up, healthy, CreatedAt=01:10:48` | ✅ |
| HM1 reachable from HM2 | `200 OK, 7.8ms` | ✅ |

## 互备拓扑 (修复后)
```
HM1 (100.109.153.83) → PEER_FALLBACK_URL = 100.109.57.26:40006 (HM2) ✅
HM2 (100.109.57.26) → PEER_FALLBACK_URL = 100.109.153.83:40006 (HM1) ✅
```
双向互备恢复，无自环。

## 注意事项
- HM1 PEER_FALLBACK_TIMEOUT=45, HM2=25 (不对称但非critical)
- R683注释称timeout两机对齐为25，但HM1仍是45 (次要问题，下轮处理)
- 容器需 `docker compose up -d --force-recreate` 才能真正应用新env

## 下一轮
- 观察 1h，确认 peer fallback 成功率
- 如果 ATE 仍高，考虑调整 PEER_FALLBACK_TIMEOUT 对齐

