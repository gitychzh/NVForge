# R2028: nv_s0 探针调研基线节点 (打 tag + 目录备份, 0 代码改动)

> **状态**: 已部署 (tag + 备份), 0 代码改动 0 restart. HM2 only.
> **目的**: 为 "nv_gw 多 key 软挂重试探针调研" (撤 40007 前置) 建立可回退的稳定基线.

## 背景 (用户 message 8/9 链)

最终目标: **撤掉 40007 (ms_gw) 也能正常运行, cc2 不中断**.
当前障碍: nv_gw peek barrier (R1716) 在首内容前判健康, 软挂时**直接切 ms**,
**不试其它 nv key**. 用户问: 为什么不试下一个 nv key? 是已知道其它 5 key 都挂吗?

## 根因 (代码实锤, 非猜测)

peek barrier (handlers.py:928-1075) 发生在 `_stream_openai_to_anth` 里, 这是
`execute_request` (upstream.py key 循环) **返回成功 (某 key 回 200) 之后** 才调用的.
key 循环语义 = "回 200 = 成功", 第一个回 200 的 key 就 `return result` 退出循环
(pexec: upstream.py:763-765 `result.success=True; result.resp=resp; return result`;
 integrate: upstream.py 同构). **其它 nv key 根本没被试过**.

peek 软挂 (NVCF 回了 200 但流到一半挂住, `_fb_s` 内无真实 content/reasoning chunk) 时,
当前代码调 `_ms_fallback_request(oai_body)` 直接切 ms. 没有 "换 nv key 重试 peek" 路径.

## 为何直接切 ms (部分合理, 部分可改进)

合理: `_ms_fallback_request` 是现成的干净重放入口 (重放原 oai_body, ms 是独立上游,
peek 软挂时 nv_gw 未向 cc4101 发过任何字节, 200 还憋着, 无重复内容问题).

可改进 (离撤 40007 最近的改动): peek 软挂 → 先试其它 nv key, 5 key 全软挂才切 ms.
ms 从 "首道兜底" 降级为 "末道兜底", 理论降 ms 压力 5×.

## 三个结构性障碍 (必须先靠探针数据回答, 不能拍脑袋上代码)

1. **Q2 同段 IP 问题**: 实测 5 mihomo 端口出口 IP, 4/5 在同一段 `134.195.101.0/24`
   (7894=.193 / 7896=.188 / 7897=.180 / 7899=.195), 只 7895 是 IPv6. 若 NVCF 把 /24 当
   同一来源, k1/k3/k4/k5 软挂时其它 key 大概率同步软挂 → "5 key 全软挂才切 ms" 变成
   "5 key 同步软挂白白多挂 5×40s" → 反而更慢. 必须探针验证换 key 救不救得回来.

2. **peek 软挂可能是误判**: peek 软挂 = `_fb_s` (45-60s) 内无真实 content chunk. 但 NVCF
   对大 input 正常 prefill p99 TTFB 32.3s (R1648e 数据), peek 可能把 "正常 prefill 的大请求"
   和 "真软挂" 都判成软挂. 若误判正常大请求 → 试 k3 也被误判 → 5 key 全被误判逼到 ms.
   Q3 R1627 FULL_BUFFER 致命 bug 在 peek 阶段以另一种形式重演.

3. **架构改动**: peek barrier 在循环外, 要 "换 key 重试 peek" 得把 peek 搬进 key 循环,
   或 peek 软挂时显式重调 `execute_request` 带 "跳过已软挂 key" 参数. R1716 当时把 peek
   放循环外是为复用 `_ms_fallback_request` 不写新函数.

## 此轮改动 (0 代码改动, 只建回退点)

| 动作 | 内容 |
|---|---|
| git tag `nv_s0` | annotated tag, 指向 R2027 cb323d1, 已 push remote |
| 目录备份 `gateway.bak.nv_s0/` | rsync 整个 gateway/ (只 .py/.json/.yaml/.txt, 排除 .bak.R*), md5 与 live 一致 |
| 容器状态记录 | ContainerID 1d7334f, StartedAt 2026-07-19T13:33:43Z (R1933 重启点), Image cc-infra-nv_gw |

## 回退方法 (后续不稳时)

```bash
# 1. 代码回退 (bind-mount 源码)
cd /opt/cc-infra/proxy/nv-gw
rsync -a --delete gateway.bak.nv_s0/ gateway/   # 整目录回退
# 或单文件: cp gateway.bak.nv_s0/handlers.py gateway/handlers.py
# 2. 重启 (铁律: 改 .py 必须 docker compose restart nv_gw, 非 up -d)
cd /opt/cc-infra && docker compose restart nv_gw
# 3. 验证三看
docker inspect nv_gw --format "{{.State.StartedAt}}"   # 应为新时间
docker logs nv_gw 2>&1 | tail -5                        # Listening 日志
curl -s http://localhost:40006/health
```

## 下一步 (探针调研, 30min 数据)

给 nv_gw 加**只读日志** (不改判定/不换逻辑/不写 ms), 记录每个 peek 事件:
- peek 软挂时的 key_idx, input 大小, peek 等了多少 ms
- peek 健康时的同上 (作对照基线, 区分 "真软挂" vs "正常 prefill 被误判")
- peek 软挂后切 ms 的结果 (ms 成功? ms 也软挂?)

30min 后据数据回答两问:
1. peek 软挂时换 nv key 救得回来吗? (看同段 IP 是否致同步��挂)
2. peek 软挂里几个是真软挂, 几个是大 input 正常 prefill 被误判?

## 铁律

- 改前有数据 ✓ (Q1/Q2/Q3 全代码+DB+实测 IP 实锤)
- 改后有验证 ✓ (tag + 备份 md5 一致 + 容器状态记录)
- 聚焦 nv_gw ✓ (只动 40006 nv_gw, 不碰 ms_gw 源码)
- 所有修改写入仓库 ✓ (本 round + tag push remote)
- 只改 HM2 ✓ (tag/备份只在 HM2, HM1 不动)
- 探针调研期间 cc2-resume.timer 不停 (用户: "自优化的任务暂时不要停掉")
- 不清活动 session (用户: "当前活动的那个 session 不要清")
