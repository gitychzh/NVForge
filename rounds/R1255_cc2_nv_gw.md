# R1255 — cc2 链路切换: primary glm5_2_nv@40006 + fallback glm5_2_ms@40007 (同模型跨供应商)

**时间**: 2026-08-13
**触发**: 用户指定 — 把 cc 自身链路从 dsv4f0731_nv@40666 切到 glm5_2_nv@40006 主线, glm5_2_ms@40007 备用.

## 背景

- 前主链 dsv4f0731_nv@40666 7d SR=81% (5380×200 + 1225×502 + 31×499), p50=17.7s, fallback 触发率 ~30%.
- 用户要求切到同模型跨供应商双链: glm5_2_nv (NVCF/美国) + glm5_2_ms (ModelScope/中国).
- 切前必须分别测稳定性, "确定好用再切".

## 测试

### ① 重新获取 fid (NVCF functions 列表 182 个, grep glm)

| fid (8) | status | name | 实测 pexec |
|---|---|---|---|
| **3b9748d8** | ACTIVE | ai-glm-5_2 | 429 Too Many Requests (3 IP 全 429, 配额满载) |
| **bfcf495b** | ACTIVE | mn-baseline-glm-5_2 | **200 OK 全通** (5×5+3×3 = 15/15=100%, p50 1.8s) |
| b6029a96 | **INACTIVE** | mn-tp8dp1 | 404 Function id not found |
| b1b22d03 | **INACTIVE** | mn-tp8-b200 | 404 |
| 5532e90c | **INACTIVE** | mn-baseline-wb | 404 |

发现 config.py 候选 5 个 fid 中 3 个已 INACTIVE → pexec 踩死 fid 失败后 fallback integrate 拖慢 8-15s.

### ② 40006 (glm5_2_nv) 稳定性

修复前 (候选含 3 死 fid): 非流式 6/6=100% 但延迟 2.4-16.4s (踩死 fid 后 integrate 兜底).
修复后 (候选精简到 2 ACTIVE): 非流式 6/6=100%, 流式 3/3=100%, 延迟 3-16s (NVCF 侧波动, bfcf495b 裸 pexec 同期 3-12s).
bfcf495b 裸 pexec 5 连测: 3.1/4.9/5.6/8.1/12.2s 全 200, 无失败.

### ③ 40007 (glm5_2_ms) 稳定性

非流式 6/6=100%, 延迟 0.9-5.6s, p50~1.1s.
流式 2/2=100%, 12-14 个 SSE 事件, 延迟 1.3-1.6s.
7d 历史: 48×ok (avg 39s) vs 779×error (历史主链崩溃期污染, 非当前状态).

## 改动

### 1. config.py glm5_2_nv function_ids 精简 (R1255)

`/opt/cc-infra/proxy/nv-gw/gateway/config.py`:
- **前**: 5 候选 [3b9748d8, b6029a96, b1b22d03, 5532e90c, bfcf495b]
- **后**: 2 候选 [3b9748d8 (pos0, ACTIVE 但 429-prone), bfcf495b (pos1, ACTIVE 快稳)]
- 删除 b6029a96/b1b22d03/5532e90c (NVCF INACTIVE, pexec 404).
- 备份: `config.py.bak.R1255`

### 2. cc4101 docker-compose.yml env 切链 (R1255)

`/opt/cc-infra/docker-compose.yml` cc4101 块 L552-558:
- `PRIMARY_UPSTREAM_URL`: `http://dsvf0731_nv40666:40666/v1/messages` → `http://nv_gw:40006/v1/messages`
- `PRIMARY_UPSTREAM_MODEL`: `dsv4f0731_nv` → `glm5_2_nv`
- `FALLBACK_UPSTREAM_URL`: 保持 `http://ms_gw:40007/v1/messages`
- `FALLBACK_UPSTREAM_MODEL`: `dsv4f0731_ms` → `glm5_2_ms` (同模型跨供应商)
- 备份: `docker-compose.yml.bak.R1255`

### 3. 重启

- `docker compose restart nv_gw` (config.py bind-mount 改动)
- `docker compose up -d cc4101` (env 改动必须 up -d)

## 验证

| 检查 | 结果 |
|---|---|
| 40006 health | ✅ `['glm5_2_nv']` |
| cc4101 health | ✅ `primary=glm5_2_nv` |
| cc4101 env | ✅ PRIMARY=nv_gw:40006/glm5_2_nv, FALLBACK=ms_gw:40007/glm5_2_ms |
| 端到端冒烟 (cc→4101→40006) | ✅ 3/3=200, model=glm5_2_nv, text=OK, 4.8-25.4s |
| fallback 直测 (40007) | ✅ 200, model=glm5_2_ms, 47s (ModelScope 偶慢) |
| DB 新流量 | ✅ 5min 内 7×200, host_machine=opc2sname, mapped_model=glm5_2_nv |
| docker ps | ✅ cc4101 Up, nv_gw Up, ms_gw Up |

## 下一步

- 下个 30min 窗口观察: 新链路 SR, fallback 触发率, glm5_2_nv 延迟分布.
- 关注 3b9748d8 的 429 是否持续 (若持续, 可考虑只保留 bfcf495b 单 fid).
- 关注 NVCF pexec 延迟波动 (3-16s), 若持续高位考虑调 cc4101 fail threshold 加速 fallback.
- dsv4f0731_nv@40666 容器保留运行 (不删), 作为应急备用.
