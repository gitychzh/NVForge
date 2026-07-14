---
name: r845-cc4101-stall-watcher-b2-b5-fix
description: "cc4101 R845: B7 stream stall-watcher双门槛(总时长180s+idle60s,per-read短轮询30s获检查点) + B2 socket.timeout三分分类(stall_watcher/idle/upstream_disconnect) + B5 client早断conn泄漏兜底"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88f513be-ac30-40ea-b01d-436b672c0fa8
---

# R845 cc4101 stall-watcher + B2分类 + B5 conn泄漏修复 (2026-07-14)

## 背景
a1db6f13 审计后, B1(content_filter误判200)被日志证伪(R844 F4/F5已修带return, a1db6f13 finish_reason=null正确emit api_error 502). 真暴露的bug:
- B2: `except socket.timeout` 一律记 idle timeout, 上游120.8s主动断连被误归类(elapsed<150s证明非idle).
- B7: cc4101 无 stall-watcher, per-read socket timeout(150s)被keep-alive drip绕过即失明(nv_gw至少有stream_idle_deadline检查点, cc4101连这个都没有).
- B5: send_response在主try之外, CC早断BrokenPipe冒泡致上游conn泄漏+metrics漏记.

## R845 改动 (3文件, 已部署 bind mount)
- **config.py**: 新增3常量 `CC4101_STREAM_TOTAL_DEADLINE_S=180`(ttfb后绝对总时长兜底) / `CC4101_STREAM_IDLE_GAP_S=60`(无真内容idle间隙上限) / `CC4101_STREAM_POLL_S=30`(per-read短轮询). UPSTREAM_IDLE_TIMEOUT(150s)语义退为"总预算", 不再作per-read.
- **upstream.py**: `_call_upstream` 默认 `idle_timeout=CC4101_STREAM_POLL_S`(原UPSTREAM_IDLE_TIMEOUT). `_restore_read_timeout(conn, POLL_S)`.
- **stream.py** (stream_to_anth + collect_stream_to_anth 双路径):
  - 主循环顶部加双门槛检查点: `ttfb后 total>180s` 或 `idle_gap>60s` → raise socket.timeout(带error_type).
  - `resp.read(8192)` 包try, socket.timeout时continue回检查点(非致命, 让双门槛在纯静默期也能判定).
  - ttfb记录点同步设 stream_total_deadline + last_progress_time.
  - 真内容累积处(content/reasoning/tool_call)刷新 last_progress_time(防drip绕过).
  - `except socket.timeout` B2三分: error_type已是stall→stall_watcher; elapsed>=150s→idle; 否则→upstream_disconnect(覆盖误判的StreamSocketTimeout).
  - B5: stream_to_anth 的 send_response段包 try/except(BrokenPipe等), 异常时close conn+记client_gone_pre_stream/499+return.
- **handlers.py**: stream_to_anth/collect_stream_to_anth 调用包 try/except(BrokenPipe/ConnectionReset/OSError), 兜底close conn+记client_gone_mid_stream/499.

## 部署+验证
- 备份 `*.preR845.20260714_124722`.
- `docker restart cc4101` + `docker exec rm __pycache__/*.pyc`. import OK, 常量180/60/30加载正确.
- 回归: collect(stream=false) 200 ttfb4745ms; stream(true) 200 ttfb5965ms thinking不误杀. 两条正常路径干净.
- stall-watcher触发路径+B2分类: 需真实上游断连/静默场景才能触发, 下次自然发生日志出 STREAM-DEADLINE/STREAM-IDLE-STALL/StreamUpstreamDisconnect. 无法不impact生产主动构造.

## 关联
- B1证伪 + a1db6f13真根因(NVCF integrate 120.8s主动断连非timeout) 见 [[cc4101-b1-b2-audit-correction]]
- R835b nv_gw stall-watcher参考(但记忆里的SILENT_MAX=480s在当前nv_gw源码不存在, 实际是NVU_STREAM_TOTAL_DEADLINE_S=90s首字节后绝对总时长, 不重置) 见 [[r835b-nv_gw-stream-deadline-ttfb-minimax-fix]]
- 未做: B6(_estimate_text_chars漏算tools, R842同源) / B3+B4(zombie tool_call判定永远False+阈值过低) / B8/B9/B10 — P2-P3后续轮次.

**Why:** cc4101连检查点都没有是B7核心, per-read短轮询(30s)是让单线程阻塞read模型也能获得检查点的解法(用户选定总时长+idle双门槛). B2让metrics说真话, 运维不再误调timeout治标不治本.
**How to apply:** 下次报stream interrupted先看cc4101 metrics error_type: StreamUpstreamDisconnect=上游主动断(根因在上游NVCF, 调timeout没用); StreamSocketTimeout=真idle(可调); StreamStallWatcher=stall-watcher命中(总时长或idle超限). 注意POLL=30s会让thinking静默期每30s进一次except→continue, 若日志频繁出现但请求正常完成是预期行为.
