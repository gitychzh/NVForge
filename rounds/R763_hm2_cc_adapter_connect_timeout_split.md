# R763: HM2 cc-adapter connect/read timeout 分离 (修复 connect 抖动卡 90s 才切 fallback)

> 根因: _post_upstream 用 HTTPConnection(timeout=PRIMARY_STREAM_TIMEOUT_S=90s) 同时管 connect+read.
> nv_gw 瞬时网络抖动时 connect 卡 90s 才报 TimeoutError 切 fallback, 浪费 90s.
> 修复: socket.create_connection(short connect_timeout) 预连, read 用完整 timeout.

## 改前数据 (10min)

### hm4104 connect 抖动卡 90s
```
01:54:23 UPSTREAM-ERR: connect to nv_gw failed: TimeoutError: timed out  (90s 才报)
01:54:23 PRIMARY-FAIL-STREAM: 切 fallback
01:57:05 UPSTREAM-ERR: connect to nv_gw failed: RemoteDisconnected
01:57:05 CIRCUIT-OPEN: primary 连续 2 次故障
```
对应时刻 nv_gw 无任何日志 (请求未到达/未 accept), ThreadingHTTPServer 不阻塞.
根因: 容器网络瞬时抖动, connect 阶段卡满 90s PRIMARY_STREAM_TIMEOUT_S 才超时.

### 问题
HTTPConnection(timeout=90s) 的 timeout 同时管:
- TCP connect (应短, 秒级)
- HTTP read (应长, 覆盖模型推理 30-90s)
抖动时 connect 卡 90s = 浪费整个 PRIMARY_STREAM_TIMEOUT_S 预算才切 fallback.

## 改动 (cc-adapter/gateway/forwarder.py, hm4104/opclaw4103/oc4105 共享源码)

| 项 | 改前→改后 | 理由 |
|---|---|---|
| connect timeout | PRIMARY_STREAM_TIMEOUT_S (90s) | 抖动卡 90s |
| connect timeout (改后) | CC_CONNECT_TIMEOUT_S (默认 10s, env 可调) | TCP connect 秒级, 10s 足够 |
| read timeout | 不变 (PRIMARY_STREAM_TIMEOUT_S / FALLBACK_TIMEOUT_S) | 覆盖模型推理 |
| 实现 | HTTPConnection(timeout=t) 混用 | socket.create_connection(connect_timeout) 预连 → sock.settimeout(read_timeout) → conn.sock=sock |

### 代码
```python
CC_CONNECT_TIMEOUT_S = float(os.environ.get("CC_CONNECT_TIMEOUT_S", "10"))
# _post_upstream:
sock = socket.create_connection((host, port), timeout=CC_CONNECT_TIMEOUT_S)  # 短 connect
sock.settimeout(timeout_s)  # 长 read
conn = http.client.HTTPConnection(host, port, timeout=timeout_s)
conn.sock = sock
conn.request(...)
resp = conn.getresponse()
```

### 影响范围
- hm4104, opclaw4103, oc4105 共享 cc-adapter/gateway/forwarder.py (bind-mount)
- cx4102 用独立的 cx-gw/gateway/forwarder.py (不改, codex 流量低)
- cc4101 用 cc4101/gateway (不改)
- nv_gw/ms_gw 不受影响 (模块化)

### 不改
- nv_gw/ms_gw 源码 (模块化)
- HM1 (冻结)
- cx4102 (独立源码, 流量低, 有需求再改)

## 改后验证

### 3 适配器 health OK
hm4104/opclaw4103/oc4105 restart 后 health 200.

### 非流式请求 200 OK
curl hm4104 dsv4p_nv 非流式 → 200 (content 空, 模型返回).

### DB 改后 5min
- nv_requests: 9 成功 / 0 个 502 (100% SR)
- ms_requests: 3 成功 / 0 error
- hm4104: 1 STREAM-UPSTREAM-ERR (restart 前残留), 之后 0
- opclaw4103/oc4105: 0 错误

## 预期
- nv_gw 抖动时 hm4104/opclaw4103/oc4105 在 10s 内切 fallback (而非 90s)
- 省下 80s/次抖动, hermes dialog_timeout 300s 余量更充足
- 不影响正常请求 (connect 正常时 <1s, 10s 阈值不触发)

## 风险
- 低: connect 10s 远大于正常 connect (0.03s 实测), 不会误杀
- SSL 场景: wrap_socket 在 connect 后, 用 read timeout (覆盖 SSL handshake + read)
- 回滚: forwarder.py.bak.R763

## 遗留
- ms_gw stream_no_data cycle (非阻塞)
- cx4102 connect timeout 未分离 (独立源码, 流量低, 有需求再改)
- HM1 同步待授权
- k3 NVAPI key 仍需用户更换 (R762 已隔离其影响)
