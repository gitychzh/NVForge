# R2258 (HM2): webui idle-stream watchdog + cc4101 header_timeout 观测点 — 根治 webui session 僵尸

> 承接: session 89985e17 静默中断深挖。用户指令"彻查根因 + 与 ChatGPT 讨论"。
> 本轮全改(webui + cc4101),HM2 only。HM1 未动。

## 一、根因(深挖 + ChatGPT 确认)

### 现象
- session `89985e17-6d4e-47f1-a8aa-8f506d477a5b` (cwd=`~/cc_ps/chatgpt_api`, entrypoint=sdk-ts,
  kind=interactive, webui `/api/agent` spawn 的 ad-hoc session) **毫无提示中断**。
- jsonl 33 行,最后 assistant turn `stop_reason=end_turn` **正常结束**(text="Let me read the first
  part of that session file for git clone/pull commands.", usage: input=20189/output=245,
  model=glm5_2_nv)。**不是 mid-stream 崩**。
- 之后 jsonl 再无新行(mtime 停 21:41:43)。下一个 turn 的请求发出去了,响应永远没回来。
- 进程 1841921 (`claude --resume 89985e17`) **仍然活着**, STAT=Sl+, etime 18min+,
  wchan=ep_poll, %CPU 1-3%, RSS 300MB, 7 线程, **整组卡在 ep_poll 空转**。
- 它没有 timeout 包裹(webui spawn 的, 不是 systemd cc2-resume.service), 会一直僵尸到机器重启。

### 事实链(均抓证)
1. telemetry `tengu_api_slow_first_byte` (model=claude-opus-4-8[1m], elapsed_ms=30009) —
   SDK 等下一个 assistant turn 的首字节等了 30s+, **只发 telemetry 事件, 不中断**。
2. cc4101 日志 21:43:27.9 `[PRIMARY-FAIL] primary(glm5_2_nv) timeout status=0 after 60053ms:
   header/ttfb timeout after 60s` → 21:43:30.2 `[ERR] client gone mid-stream after 66546ms:
   Broken pipe`。NVCF TTFB 超 60s → cc4101 header_timeout 60s 到期主动断流 → Claude SDK 收到 Broken pipe。
3. nv_gw 日志: 该时段 glm5_2_nv 5 key 连环 "Remote end closed connection without response",
   pexec_us_rr 全 fail → ms_gw fallback 救回(48s 后), TTFB 实测 48-66s。
   **上游 NVCF glm5.2 大 input TTFB 系统性慢**。
4. jsonl 末尾 assistant text 有裸 `[/thinking]` 闭合标签(前无开标签, glm5.2 偶发输出瑕疵)。
   但上一个 turn 是 end_turn 正常结束, 解析没崩 → **质量瑕疵非中断根因**。

### 根因结论(与 ChatGPT 讨论确认)
> **主因 = NVCF glm5.2 上游 TTFB 太慢(>60s) → cc4101 header_timeout 60s 到期主动断流
> → Claude SDK HTTP 流被对端 RST/Broken pipe → SDK 进入"等首字节"状态, 发了
> slow-first-byte(30s) telemetry 但进程不退, 卡在 ep_poll 等永远不来的数据。
> session 静默中断: 上一个 turn 已写盘, 下一个 turn 请求悬空, SDK 既不报错也不继续, 僵尸式活着。**

> **放大根因 = webui `/api/agent` spawn 用 Claude Agent SDK 的 `query()` 起 claude.exe,
> 靠 `session.instance.interrupt()` abort, 但 webui 没有"无消息超时自动 abort"的 watchdog
> 去触发 interrupt()。** 对比 cc2 自优化那套有 systemd `KillMode=control-group` +
> `TimeoutStartSec` 兜底, 所以即使卡也会被下一轮 timer 清。**这个漏洞只影响 webui 手动起的
> ad-hoc session(包括本 session 89985e17), 不影响 cc2/hermes2/openclaw2 自优化三套(systemd 兜底)。**

ChatGPT 原话: "你的这次定位已经抓到了关键: 不是模型输出问题, 而是分布式流式调用里'最后一层没有
owner 负责杀死悬挂请求'。下一步最值得做的是把 /api/agent spawn 改成和 cc2-resume.service
同等级的 supervisor。"

### ChatGPT 纠正/补充
1. 主因确认: NVCF 慢 TTFB 触发 cc4101 断流 + Claude SDK/Node 调用链没有最终 timeout 导致挂死。
   **不是 resume bug / session 损坏 / thinking tag**。
2. `tengu_api_slow_first_byte`: 大概率是"30s 没收到首字节就报一次 telemetry 事件但继续等",
   **不是 abort**。之后 SDK 继续等待(所以进程不退)。
3. 进程卡 ep_poll 18min: **不能证明是 Claude SDK bug**, 更像"外层(webui spawn)没有生命周期
   管理, 导致 Node 等待一个永远不完成的 async"。
4. `[/thinking]` 裸标签: 质量瑕疵(P3 最低优先级), 不追。

## 二、改动(本轮全改, 分层执行)

### P0 止血 — webui idle-stream watchdog (已完成)
**文件**: `~/cc_ps/cc_webui/dist-server/server/claude-sdk.js`
**备份**: `claude-sdk.js.bak.R2254_20260722`

webui 用 Claude Agent SDK 的 `query()` 起 claude.exe, 在 `for await (const message of
queryInstance)` 循环里处理流。**原代码没有 idle/首字节超时** — 如果上游 NVCF 慢 TTFB,
SDK async generator 卡在 `await` 下一条 message 上, 永远不推进, `interrupt()` 没人调, 进程僵尸。

**改法**(最小侵入, 符合 SDK 设计, 不碰 SDK 内部):
1. 加常量 `STREAM_IDLE_TIMEOUT_MS`(读 env `CLAUDE_STREAM_IDLE_TIMEOUT_MS`, 默认 120000ms):
   ```js
   const STREAM_IDLE_TIMEOUT_MS = parseInt(process.env.CLAUDE_STREAM_IDLE_TIMEOUT_MS, 10) || 120000;
   ```
2. 把 `for await (const message of queryInstance)` 循环改成 `while` + `Promise.race`:
   每条 message 用 idle timer 竞速, 超时调 `queryInstance.interrupt()` 打断 generator,
   让它自然结束(走 complete/error 分支清理)。
   - 120s 覆盖 glm5.2 TTFB p99 ~66s 留余量; 0 = 禁用(回退旧行为)。
   - interrupt() 后 generator 抛错或返回 done, 正常 cleanup(removeSession/cleanupTempFiles) 跑完。
3. 超时时打 `[R2254-WATCHDOG] session <sid> idle 120000ms, calling interrupt()` 留痕。

**验证**: `node --check` syntax OK; scp 回 HM2; 重启 `cloudcli-webui.service`(PID 1858689);
新代码 5 处 watchdog 标记加载; webui 3001 listening; WebSocket 重连 OK; jsonl 同步 7 个 claude session。

### P0 止血 — kill 僵尸进程 (已完成)
- `kill -TERM 1841919 1841921` 干净杀掉僵尸进程组(进程组无独立 PGID, 直接 kill 正 PID 生效)。
- 注意: webui 检测 session 断后会**自动 `--resume` 重启**同 sid — 重启 webui 前又 spawn 了
  1850829(同一 89985e17)。光 kill 僵尸不够, 必须给 webui spawn 加 watchdog(已做)。

### P1 治标(观测) — cc4101 header_timeout 观测点 (已完成)
**文件**: `/opt/cc-infra/proxy/cc4101/gateway/upstream.py` (bind-mount)
**备份**: `upstream.py.bak.R2254obs_20260722`

深查发现 cc4101 **R2154/R2202 的 6 档动态 header_timeout 早已存在且精细**:
  <30K=PRIMARY_HEADER_TIMEOUT(60), 30-50K=40s, 50-90K=150s, 90-150K=160s,
  150-350K=180s, >350K=120s。
那个 60s 误杀(req=e60791ac msgs=2)说明 `_hdr_ic` 落 <30K 档, 但请求带 27 工具定义,
实际可能更大 — **观测盲点**。ChatGPT 警告: 治根前必须先有观测数据, 盲改分档表违反铁律。

**改法**: 在 `_try_primary` 的 `_call_upstream` 调用前加观测日志:
```python
_nm = len(oai_body.get("messages", [])) if isinstance(oai_body, dict) else 0
_nt = len(oai_body.get("tools", [])) if isinstance(oai_body, dict) else 0
_log("R2254-OBS", f"primary req={request_id} _hdr_ic={_hdr_ic} hdr_to={_hdr_to} msgs={_nm} tools={_nt}")
```

**验证**: restart cc4101; 立刻抓到 3 条样本:
```
22:28:24.9 R2254-OBS primary req=a7810795 _hdr_ic=152572 hdr_to=180 msgs=15 tools=27
22:28:32.8 R2254-OBS primary req=1a33a7c3 _hdr_ic=161465 hdr_to=180 msgs=18 tools=27
22:28:44.1 R2254-OBS primary req=e776d081 _hdr_ic=166672 hdr_to=180 msgs=20 tools=27
```
**证实 R2154 分档正确生效**(152-166K 落 150-350K 档=180s)。小请求(tools=0)场景待后续抓,
观测点已就位持续记录。下一轮据数据对症调档或确认 60s 是 <30K 档的合理行为。

## 三、未做(P2 治根 + P3, 留下一轮, 数据驱动)

- **P2 nv_gw peek 覆盖 cc4101 直连路径**: R2252 的 peek 内部换 key 只覆盖 nv_gw 自己的
  peek barrier, 不覆盖 cc4101 直连 nv_gw 的 header 路径。需先抓证 cc4101 header 超时前 nv_gw
  是否有机会切 key, 再定改法。
- **P3 glm5.2 裸 `[/thinking]` 文本过滤**: 质量瑕疵, 最低优先级。
- **真根治 NVCF TTFB 慢**: 上游 NVCF glm5.2 大 input TTFB 48-66s 系统性慢, 非 nv_gw 旋钮能修,
  等 NVCF 端修复(同 R2110+ openclaw2 域归因)。

## 四、影响域

- **webui watchdog**: 只影响 webui `/api/agent` spawn 的 session(手动 ad-hoc + 未来所有 webui
  session)。cc2/hermes2/openclaw2 自优化三套走 systemd timer, 已有 KillMode 兜底, 不受影响
  (但也不会被 watchdog 误伤 — 它们不走 claude-sdk.js 的 query 路径)。
- **cc4101 观测**: 只加日志, 不改行为, 全链路无影响。

## 五、回滚

- webui: `cp ~/cc_ps/cc_webui/dist-server/server/claude-sdk.js.bak.R2254_20260722
  ~/cc_ps/cc_webui/dist-server/server/claude-sdk.js && systemctl --user restart cloudcli-webui`
- cc4101: `cp /opt/cc-infra/proxy/cc4101/gateway/upstream.py.bak.R2254obs_20260722
  /opt/cc-infra/proxy/cc4101/gateway/upstream.py && docker compose restart cc4101`
- watchdog 禁用(不回滚代码): webui env 加 `CLAUDE_STREAM_IDLE_TIMEOUT_MS=0` 重启。

## 六、铁律遵守

- 改前必有数据 ✅ (session jsonl + telemetry + cc4101/nv_gw 日志 + ChatGPT 讨论)
- 改后必有验证 ✅ (node --check + webui restart + 3001 listening + cc4101 restart + R2254-OBS 抓到样本)
- 聚焦 nv_gw 链路 ✅ (cc4101→nv_gw 是 nv_gw 链路一部分; webui watchdog 是 session 层止血)
- 写入仓库 ✅ (本 round 文件)
- 只改 HM2 ✅ (HM1 未动)
- 改 .py 必须 restart ✅ (cc4101 bind-mount restart 已做)
