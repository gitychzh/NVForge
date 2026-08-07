# R1105 cc2 NOP — cc2 primary 109/109=100% SR 零错误

- 时间: 2026-08-07 22:45 CST
- 轮次: R1105 (NOP 巡检轮 / 不改码)
- 容器: nv_gw Up 19h, cc4101 Up 19h

## 结论

**NOP。** 30min cc2 主链 (cc4101-primary 经 nv_gw primary model=dsv4f0731_nv) =
**109/109 = 100.0% SR 零错误**, 较 R1104 的 107 略升。fallback 0%。cc2 范围无任何新签名。
唯一 1× zombie_empty_completion (502) 归属 peer (hermes) 非 cc2 主链。不改码。

## 数据 (实测 DB 2026-08-07 22:45 CST + 实时复核 + /health)

### 30min cc4101-primary (cc2 专属)
- status: 仅 200 × **109** = 100.0% SR, 0 错误

### 30min 全量非-200 归属
- 唯一 1× `zombie_empty_completion` (502), caller=**hermes** (peer) —— JOIN 铁证归属 peer 非 cc2 主链 (cc4101-primary 0)

### fallback
- 0% (109 total, fallback_triggered=0, 全走 primary)

### 30min nv_tier_attempts (tier=dsv4f0731_nv)
- 5 key 基本全 `pexec_success` (fid 281478d0)
- 仅 k0 1× + k3 2× `NVCFPexecRemoteDisconnected` + k3 1× `empty_200` —— 全部一次性 distributed transient,
  单请求 buffer 自愈, 无 multi-key 连续复发。量 (总 4x 含 1x empty_200) 与上轮基本持平
- k3 empty_200 = 一次性 transient (历史模式 k4/k3 偶发), 单请求, 无 buffer 重试

### buffer 日志
- 全 `attempt=1/5` 直 flush 秒回 (req=be834acc 14s, req=112487c4 5s, req=e23d94d6 6s,
  req=de9a39cb 8s), verdict 全 success_tool_call/success_text, 零重试零级联零 buffer_exhausted

### 容器 /health (2026-08-07 22:45 CST)
- 40006 nv_gw: http 200
- 4101 cc4101: http 200
- docker ps: nv_gw Up 19h, cc4101 Up 19h

## 判定依据
- SR=100% ≥ 99% 且无 cc2 范围新错误 → NOP 巡检轮, 只记数据不改码
- 非-200 (hermes zombie) 归属 peer, 不进 cc2 指标
- k0/k3 RD + k3 empty_200 量小一次性 transient, 与历史记忆模式一致, 无 multi-key 连续复发, 非配置漂移

## 参数快照 (未动, 同 R1104)
- 本轮零改动。nv_gw env 复核: NV_GLM52_MODE_CHAIN=pexec_us_rr, NVU_DISABLE_MS_FALLBACK=0,
  UPSTREAM_TIMEOUT=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2, NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4,
  KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0, NVU_BUFFER_MAX_RETRIES=5 (90s×5=450s)。
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, CC4101_STREAM_TOTAL_DEADLINE_S=470,
  PRIMARY_HEADER_TIMEOUT=400, FALLBACK_UPSTREAM_URL=http://ms_gw:40007/v1/chat/completions。

## 下一步
- 延续 NOP。cc2 主链连续多轮 (R1096-R1105) 100% SR + zero fallback, 无参数可调。
- **k0/k3 RD** (fid 52e1ddb6 历史坏 fid) + **k3 empty_200**: 量小一次性 transient, 与历史 memory
  模式一致 (泄漏源=越界容器 40666 hermes 线, 宿主分离), 单请求 buffer 自愈。仅当 RD/empty_200
  在多 key **连续复发** (多个独立请求多 key 持续失败) 才查链路/mihomo。
- **hermes 1× zombie_empty_completion** (peer) 持续关注, 归属 peer 非 cc2 不改动。
- 若 zombie_empty_completion 中出现 caller=cc4101-primary (c.parent) 才进 cc2 指标。