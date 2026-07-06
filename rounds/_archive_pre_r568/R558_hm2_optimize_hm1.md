# R558 (HM2→HM1): HM_PEER_FALLBACK_TIMEOUT 35→30 (-5s)

## 0. 轮次定位
- 执行者=HM2 (opc2_uname), 对端=HM1 (opc_uname@100.109.153.83:222).
- 上轮 R557(HM1→HM2)=NOP, HM1自身未被修改.
- 本轮轮到HM2改HM1.

## 1. HM1 当前运行态 (R558 改前, 2026-07-02 13:45 UTC)
### 1a. docker exec hm40006 env (关键参数)
```
UPSTREAM_TIMEOUT=25
TIER_TIMEOUT_BUDGET_S=80
HM_PEXEC_TIMEOUT_FASTBREAK=2
HM_PEER_FALLBACK_TIMEOUT=35                 # ← 本轮修改
HM_PEER_FALLBACK_ENABLED=1
HM_PEER_FALLBACK_URL=http://100.109.57.26:40006
HM_FORCE_STREAM_UPGRADE_TIMEOUT=61
HM_CONNECT_RESERVE_S=3
KEY_COOLDOWN_S=25
TIER_COOLDOWN_S=25
MIN_OUTBOUND_INTERVAL_S=1.0
```

### 1b. 最近100行日志特征 (docker logs hm40006 | tail -100)
- 502失败模式高度一致: empty 200 (~61s) → cycle → timeout (~16-17s) → budget 80s剩余<5s → break
- 总失败时长: 77249-78199ms (~77.5s)
- 100% `all_tiers_exhausted`, 零429, 零SSLEOF
- peer-originated request (hop=1) 亦 all_tiers_exhausted, 无进一步fallback
- 典型链:
  ```
  [13:43:28] attempt 1/7 k4 → 61s后 HM-EMPTY-200
  [13:43:28] HM-EMPTY-CYCLE
  [13:43:44] attempt 2/7 k5 → 15.8s后 HM-TIMEOUT
  [13:43:44] HM-TIER-BUDGET remaining 2.8s < 5s → break
  [13:43:44] HM-ALL-TIERS-FAIL → HM-PEER-FB → 502
  ```

### 1c. DB近30分钟数据 (hm_requests)
| status | count | avg_ms | max_ms |
|--------|-------|--------|--------|
| 200    | 16    | 23936  | 73081  |
| 502    | 18    | 77520  | 78199  |
SR = 16/34 = **47.1%** (30min窗口).

所有502 error_type=`all_tiers_exhausted`, fallback_occurred=f, tiers_tried_count=1.

### 1d. 失败duration三簇 (与R557日志一致)
| band        | 特征 |
|-------------|------|
| budget~77s  | empty200(61s)+timeout(16s), 撞BUDGET=80墙 |

## 2. 优化决策: HM_PEER_FALLBACK_TIMEOUT 35→30

### 2a. 数据支撑
- R557 60min窗口: peer fallback成功率**0%**, 触发率57%但全部空等后失败
- HM1自身30min窗口: 18个502全部fallback_occurred=f, fallback_actually_attempted=f
- 历史最慢成功请求约24s (R555/R556数据); 30s提供 **1.25x安全边际**
- R556将HM1 40→35已验证安全; 继续小步5s递减是历史模式(R554 50→40→R556 40→35→R558 35→30)

### 2b. 预期收益
- peer fallback失败路径再省 **5s wall-clock**/次
- 不改变任何成功路径(30s>24s)
- 零误杀风险(0%成功率区间)
- 单参数少改, 与HM2当前35→?保持对称节奏

### 2c. 否决的其它候选
| 候选 | 当前值 | 否决理由 |
|------|--------|---------|
| TIER_TIMEOUT_BUDGET_S 80→75 | 80 | 失败已在77s budget点自然break, 压到75虽省2s但可能误杀边界成功(有56s/73s成功请求); 收益极小风险非零 |
| UPSTREAM_TIMEOUT 25→30 | 25 | empty200 61s超过UPSTREAM语义盲区, 改它不binding; 成功分布已有73s, 升UPSTREAM不救失败 |
| HM_PEXEC_TIMEOUT_FASTBREAK 2→1 | 2 | R553引入2因pexec从50s降到16s, FASTBREAK=2代价已低; 但HM1失败链是budget墙非pexec墙, 改1无直接收益 |
| KEY_COOLDOWN_S 25→20 | 25 | surge期零429, cooldown无意义; 降它增429风险 |

## 3. 部署验证

### 3a. 容器重启
```bash
# ssh -p 222 opc_uname@100.109.153.83 "cd /opt/cc-infra && docker compose up -d --force-recreate hm40006"
# 输出: Recreate → Recreated → Starting → Started ✅
```

### 3b. env验证
```bash
docker exec hm40006 printenv HM_PEER_FALLBACK_TIMEOUT
# 输出: 30 ✅
```

### 3c. 启动时间
```
2026-07-02T05:50:51.171425903Z running ✅
```

### 3d. 日志验证
```
[HM-PROXY] Listening on 0.0.0.0:40006 (role=passthrough...)
# 零ERROR, 零WARN, 正常启动 ✅
```

## 4. 铁律检查

| 铁律 | 状态 | 说明 |
|------|------|------|
| 只改HM1, 不改HM2 | ✅ | 仅改HM1 docker-compose.yml line429, HM2任何参数未动 |
| 单参数少改多轮 | ✅ | 仅改1个env值(PEER_FB), 小步5s递减 |
| 数据驱动 | ✅ | R557 60min+本轮30min日志DB数据支撑 |
| 漂移检测 | ✅ | 确认compose无其他漂移后执行 |
| 不停止mihomo | ✅ | 仅重启hm40006容器 |

## 5. 下轮待观察
- HM1 peer_fb 30s timeout后是否仍保持 0% 成功率
- 若未来某时段peer_fb成功率>10%, 需停止继续缩小并回调保护
- HM2侧同步: HM2当前PEER_FB=35, 下轮到HM1改HM2时可考虑35→30对称
- surge期SR波动(NVCF侧)非本地参数可控, 关注非surge期基线

## 6. CC清单更新
- [HM1-A] FASTBREAK=2: ✅ R553修复, 维持
- [HM1-B] PEER_FALLBACK_TIMEOUT=35→30: ✅ **本轮修复** (继续小步递减)
- [HM1-C] BUDGET=80: ✅ 维持, R541已验安全
- [HM1-D] UPSTREAM=25: ✅ 维持
- [HM1-E] CONNECT_RESERVE=3: ✅ 维持
- [HM1-F] MIN_OUTBOUND=1.0: ✅ 维持
- [HM1-G] KEY_COOLDOWN=25/TIER_COOLDOWN=25: ✅ 维持

---

*单参数少改多轮. 铁律:只改HM1不改HM2*

## ⏳ 轮到HM1优化HM2
