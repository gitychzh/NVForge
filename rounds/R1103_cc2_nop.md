# R1103 cc2 NOP 巡检轮 (HM2 nv_gw)

日期: 2026-08-07 22:36 CST | 容器: nv_gw Up 19h, cc4101 Up 19h, nv_gw_stable Up 5d

## 结论: NOP — 不改码

cc2 主链 (cc4101-primary 经 nv_gw:40006, primary_model=dsv4f0731_nv) 30min = **104/104 = 100% SR, 零错误**。
cc2 专属零 502 零错误零 fallback, 无任何新签名 (cc2 范围)。唯一 1× zombie_empty_completion 归属 hermes (peer)。

## 数据 (实测 DB 2026-08-07 22:36 CST)

### 30min nv_requests (caller × status)
```
cc4101-primary | 200 | 104   ← cc2 主链 100% SR, 0 bad
hermes         | 200 | 27
hermes         | 502 | 1     ← 归属 peer
```

### 错误分类 (status != 200)
- zombie_empty_completion × 1 — caller=hermes (peer), JOIN 归属铁证, 非 cc2 主链

### fallback (cc_requests 30min)
- 104 total, fb=0 → **0% fallback** (104 全走 primary)

### per-key tier 错误 (nv_tier_attempts 30min)
- 5 key 基本全 `pexec_success` (fid 281478d0)
- 仅 k0 1× + k3 2× `NVCFPexecRemoteDisconnected` (fid **52e1ddb6**, 历史记忆坏 fid — 越界容器 40666 hermes 线泄漏源) 一次性 distributed transient, 单请求 buffer 自愈
- 零 buffer_exhausted, 零持续 tier 错误

### buffer 日志 (nv_gw 30m)
- 全 `attempt=1/5` 直 flush 秒回 (1-14s), 零重试零级联零 buffer_exhausted
- 示例: req=2322778b elapsed=1s, req=1e0d854b elapsed=14s, 均 attempt-1 done=True

### 容器 /health (22:36 CST)
- nv_gw:40006 http 200 | cc4101:4101 http 200 | docker ps 全 Up

## 判断依据
- SR 100% >= 99% 且无 cc2 新错误 → NOP 巡检轮
- k0/k3 RD (fid 52e1ddb6) 量小 (总 3x, 均单请求), 一次性 distributed transient, 与历史模式一致 (记忆: fid 52e1ddb6 泄漏源=越界容器 40666 hermes 线)。无 multi-key 连续复发, 不构成配置漂移

## 下一步
- 延续 NOP。cc2 主链连续多轮 (R1096-R1103) 100% SR + zero fallback, 无参数可调。
- 关注 hermes 1× zombie_empty_completion (peer 属性), 若进 cc2 (c.parent 归属) 才排查。
- fid 52e1ddb6 的 k0/k3 RD 仅当 multi-key **连续复发** (多个独立请求多 key 持续失败) 才查链路/线路。

## 参数快照 (未动, 同 R1102)
- nv_gw: NVU_DISABLE_MS_FALLBACK=0, UPSTREAM_TIMEOUT=90, NVU_BUFFER_CALLERS=cc4101-primary,openclaw2,
  NVU_CALLER_KEY_MAP=hermes:2;openclaw:3;opencode:4, KEY_FID_BIND=0:0;1:0;2:0;3:0;4:0
- cc4101: PRIMARY_UPSTREAM_MODEL=dsv4f0731_nv, FALLBACK_UPSTREAM_MODEL=glm5_2_ms,
  PRIMARY_UPSTREAM_URL=http://nv_gw:40006/v1/messages, STREAM_TOTAL_DEADLINE_S=470, PRIMARY_HEADER_TIMEOUT=400