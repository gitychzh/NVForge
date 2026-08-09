# NVForge 项目记忆索引

本机 HM1 本地 CC，优化对象为远程 HM2（cc4101/ms_gw/nv_gw/openclaw 链路）。2026-07-13 归档整理：56→22 个记忆，删除被后续轮次覆盖的过程性 R8xx 摘要（rounds/ 目录有完整 git 备份）。只保留最终根因结论 + 架构铁律 + 方法学。

---

## CC 自身环境
- [CC自动更新ENOTEMPTY崩溃](cc-auto-update-enotempty-crash.md) — 2026-07-14 13:25 "崩溃"真根因:npm reify rename失败致claude二进制悬空,webui拉不起claude;恢复=rm retired目录+重装2.1.208;防复发关autoUpdates

---

## 架构与铁律
- [双机协作角色](cross-host-collab-roles.md) — 我优化HM2, 远程CC优化HM1, 互不改自己, push前必pull --rebase
- [主机拓扑与自身定位](host-roles-and-self-positioning.md) — 我是HM1本地CC, 修的是HM2的cc4101/ms_gw/nv_gw; 改远程≠改自己
- [共享源跨主机分叉](shared-source-cross-host.md) — ms_gw upstream.py 两机已分叉不同源; 改HM2不影响HM1; 外科patch不整覆盖
- [GitHub SSH via 443+mihomo](github-ssh-via-443-mihomo.md) — 22端口被reset, 用 ssh.github.com:443 经 mihomo 7891 推拉
- [远程主机SSH访问](remote-host-ssh-access.md) — SSH走222端口不是22: ssh -p 222 opc2_uname@100.109.57.26; 22 closed≠SSH不可达
- [Cron session-only 不可靠](cron-session-only-unreliable.md) — CronCreate 不写盘会话中断即丢, 多轮定时任务应连续执行或用系统 cron
- [HM2 CC链路实况](cc-chain-layout-hm2.md) — HM2 CC链路=cc4101→nv_gw/ms_gw(glm5_2_nv/glm5_2_ms), CLAUDE.md的legacy_*/40001/glm5.1已stale; PRIMARY_HEADER_TIMEOUT=25s(R828)
- [HM2 CC链路框架R856](hm2-cc-chain-framework-r856.md) — ⭐完整框架:cc4101(无fb)/opclaw4103(有fb)双入口;5key双通道(pexec直连/integrate走mihomo美国);已挖5 BUG:mode_idx卡3(109次/3→3共43次放大器)/cc4101死env/429冷却=0/per-key代理单口/NV_INTEGRATE_MODELS空

## NVCF 测试方法学
- [NVCF 测试方法学](nvcf-testing-methodology.md) — 模型可用性必全方位测: integrate+pexec 双通道×5key×5IP×stream, 单通道判"不可用"是错误
- [NVCF pexec 字段语义](nvcf-pexec-field-semantics.md) — pexec 常带 model 字段; 404=账号不归属; 400 DEGRADED=服务端后端故障; 5key 各走不同 IP; 202=后端scaling非失败
- [NV模型测试必在远程](nv-model-testing-must-be-remote.md) — NV模型链路测试必须在远程HM2跑, 不在本地HM1; 本地DEGRADED/慢多为环境误判

## ms_gw 流式根因
- [ms_gw 流式中断真正根因](ms-gw-stream-relay-root-cause.md) — HTTP/1.0+keep-alive+无Content-Length致客户端卡120s; 修Connection:close; metrics写文件不写stdout

## GLM5.2 链路与思考模式
- [integrate美国出口glm5.2突破](integrate-us-exit-glm52-breakthrough.md) — 修正:不限制地理仅快慢差异,US2.7s最快,直连/日80s慢但可用,旧40s timeout误判
- [glm5.2 function id 事实](glm52-function-id-fact.md) — 只有1个ACTIVE function(3b9748d8),5_1全404 INACTIVE,凑不齐5个;5key同tenant同function集
- [glm5.2 多IP实测数据](glm52-egress-geo-real-data.md) — 美2.6s最快; ⚠07-14修正integrate对glm5.2 chat有地理限制(日5/5超时非只是慢); pexec rclen=0(thinking不返)
- [glm5.2 integrate地理限制铁证](glm52-integrate-geo-restriction-confirmed.md) — ⭐R856: integrate对glm5.2 chat限美国IP,日本出口静默超时(只读models不限地理易误判);K1切日本直接搞坏生产致mid-response(我操作引入),切回美国洛杉矶08即恢复;圣何塞三网推荐全down
- [GLM5.2思考真相](glm52-thinking-toggle-truth.md) — opencode自带nvidia provider跑glm5.2思考开不起来(源码铁证); 唯chat_template_kwargs.enable_thinking有效; openclaw链路(R827)思考是开的
- [GLM5.2 5模式动态递进](r839-glm52-mode-chain.md) — chain改integrate_us_rr第一+删pexec_direct(剩4模式);源码idx越界自动回0;reset有循环import不能CLI调
- [GLM5.2定时测速cron](glm52-speedtest-cron.md) — 每天2:00/14:00跑5mode排名, 直打端点不走nv_gw不影响生产, 输出jsonl+建议mode_chain, HM2已部署cron
- [GLM5.2稳定性深测](glm52-stability-deeptest-r843.md) — 死亡窗口88-102k(95-100k 86.5%zombie); RR模式13/13全OK; mode_idx=4固定7894是放大器; zombie是3-4token快速假完成

## openclaw 飞书链路根因链(88k僵尸→fallback)
- [openclaw HM2拓扑](openclaw-hm2-topology.md) — openclaw→opclaw4103(4103)→nv_gw+ms_gw; contextWindow R1243已48000→120000修死锁; compaction.model同primary是anti-pattern
- [R840空僵尸响应根治](r840-openclaw-zombie-empty-stall-fix.md) — 真根因=NVCF返回200+stop+0~17tok空响应,openclaw收空流agent loop卡死8min→watcher重启→飞书报Gateway restarting; 修复=nv_gw透传检测空僵尸→写content_filter error SSE chunk→openclaw判error→throw→fallback链生效
- [R841b openclaw深度修复](r841b-openclaw-deep-fix.md) — R840空僵尸检测移植HM2+opclaw4103 SUPPLEMENT逻辑修复(tool_calls_seen不触发+保留finish_reason); main agent固有88k context是空僵尸诱因
- [R842 88k僵尸窗口真根因](r842-88k-zombie-window-root-cause.md) — glm5_2_nv在88k-105k窗口80%僵尸,105k+反0%;dsv4p全区间0%;main agent 98k正落死亡窗口; system38.8k+tools42.4k死重占94%; compaction估算漏算tools永不触发; C+D已应用非真解
- [R842c forwarder拦截content_filter切fallback](r842c-forwarder-content-filter-fallback-fix.md) — opclaw4103 forwarder检测finish_reason=content_filter发信号切ms_gw;不透传避openclaw empty-error-retry同provider重试;3/3成功;死亡窗口精确88-105k
- [R843C compaction tools修复](r843c-compaction-tools-fix.md) — 方案C:修estimateLlmBoundaryTokenPressure漏算tools(API tools参数不进messages/system)+contextWindow 65536→48000; C1+C2协同才有效; node单元测精确匹配; 用户选C优先D

## nv_gw 流式 deadline 机制
- [R835b nv_gw流式deadline+ttfb+minimax修复](r835b-nv_gw-stream-deadline-ttfb-minimax-fix.md) — nv_gw流式idle deadline(首字节后42s,非t_start,避免砍glm5.2 thinking慢ttfb 71s)+删ttfb=duration兜底(暴露无首字节真相)+integrate per-model tier budget(minimax 180s治502)+stall-watcher SILENT_MAX 480s僵尸流硬兜底

## 独立修复
- [cc_webui provider污染修复](cc-webui-provider-pollution-fix.md) — webui"选claude却跑codex"=前端selected-provider被codex历史会话反向写入; 已删源码那行+rebuild+rsync远程; 旧残留需浏览器手动清localStorage
- [CC配置体检R1245](cc-config-audit-r1245.md) — HM2 cc4101体检: zombie与token弱相关(下调compact无效), primary NVCF故障非配置可修, 已修config注释+bak清理, 待做CLAUDE.md重写/memory同步

## cc4101 审计 + a1db6f13 根因修正
- [cc4101 B1/B2审计修正](cc4101-b1-b2-audit-correction.md) — B1(content_filter误判200)对a1db6f13不成立:cc4101日志证明finish_reason=null+正确emit api_error 502;R844 F4/F5已带return. B2坐实但120.8s真根因=NVCF integrate通道主动断连,非cc4101/nv_gw timeout(cc4101 150s没触发,nv_gw 90s deadline也没触发=上游发keep-alive绕过,drip僵尸流)

## R845 cc4101 stall-watcher + B2分类 + B5 conn泄漏
- [R845 cc4101 stall-watcher+B2+B5](r845-cc4101-stall-watcher-b2-b5-fix.md) — B7:stream stall-watcher双门槛(总时长180s+idle60s)+per-read短轮询30s获检查点(POLL=30s,UPSTREAM_IDLE_TIMEOUT退为总预算);B2:except socket.timeout三分(stall_watcher/idle/upstream_disconnect,让metrics说真话不再误调timeout);B5:send_response在try外的conn泄漏兜底(client_gone_pre_stream/mid_stream 499). 已部署bind mount+回归OK,触发路径待真实上游断连验证

## R844 opclaw4103 fallback 迁移+超时修复
- [R844 opclaw4103 fallback+超时分层修复](r844-opclaw4103-fallback-timeout-fix.md) — 移植cc4101全套fallback进opclaw4103; 修connect抖动卡90s(TTFB用90s read timeout的R763缺陷); 三层超时connect10s/TTFB25s/idle150s; circuit三态monotonic; retry primary门控; 保留R842c/R766/R790/NOTICE; bind mount改宿主源码+restart即生效,备份在原地

## R850 thinking 静默误切真根因
- [R850 thinking静默误切修复](r850-thinking-silence-miskill-fix.md) — Server error mid-response真根因: GLM5.2 thinking经integrate通道首块reasoning后上游>120s静默思考不发chunk, nv_gw idle deadline ttfb后固定90s不刷新+cc4101 IDLE_GAP 100s都不识别思考静默→误切断还在思考的流→api_error→CC报mid-response; 修nv_gw deadline改真内容刷新+thinking翻倍180s, cc4101动态IDLE_GAP见过reasoning用200s; 实测39s/63s正常完成, 重启后0个STREAM-DEADLINE; 我(HM1)不卡因走legacy_ms_litellm不经integrate
## R849 circuit success重置点错位(R848盲区)
- [R849 success重置盲区](r849-success-reset-blindspot.md) — R848盲区:record_primary_success在connect成功(HTTP 200 header)就调重置fail_count=0, GLM5.2劣化(connect成功+流到一半静默)时流式failure永远累积不到5, circuit永远不开R848形同虚设; R849移除connect处success调用改在stream.py真正流式成功完成(非zombie非interrupted)才reset; 18:48 req=4001ac0b仍卡死即此; R850已修deadline真内容刷新+thinking翻倍
## R848 流式失败触发circuit breaker
- [R848流式circuit修复](r848-stream-circuit-breaker-fix.md) — 旧洞:record_primary_failure只在connect阶段调,流式中途失败(stall-watcher/zombie/content_filter)全在stream.py从不记circuit→NVCF劣化connect成功+流到一半静默时circuit永远CLOSED→CC每次重试打primary每次中断死循环卡死; 修stream.py 7失败点调_record_primary_stream_fail(仅primary),连续5次OPEN直走fallback ms_gw不卡; 与R847协同
## R847 deadline 倒挂真根因
- [R847 deadline倒挂](r847-deadline-inversion-root-cause.md) — upstream stream interrupted 真根因: cc4101 stall-watcher IDLE_GAP(60s)先于nv_gw TOTAL_DEADLINE(90s)触发致content_filter chunk迟到被丢; 修IDLE_GAP 60→100s; 我(HM1)不卡因走legacy_cc_1→glm5.1纯MS不经nv_gw
## R846 "upstream stream interrupted" 系统修复
- [R846 stream interrupted修复](r846-stream-interrupted-fix.md) — 三层根因全修:①R845 OSError bug(socket.py:717裸OSError不被socket.timeout接住→误判断流,Fix3接住)②total_deadline 180s误杀正常长thinking+长文(51493627实测99个content chunk被硬断,Fix4提至360s)③⭐content_filter chunk被malformed吞掉(缺\n\n致两event拼接json.loads失败,Fix6 nv_gw前置\n\n+Fix5 cc4101兜底). 验证3c41554b:同场景200+null→502 upstream_content_filter+CC重试. 详见plan r846-stream-interrupted-fix.md

## R854 真根因:禁强制thinking注入(从源头消除empty/filtered)
- [R854 禁thinking注入](r854-disable-thinking-injection.md) — ⭐真正消除empty/filtered completion的根因:nv_gw config.py:106对glm5_2_nv强制注入enable_thinking=True(R827开),每请求都被注入→GLM5.2 thinking系统性把答案写进reasoning_content(4000c)但content 0c+finish=length,CC报empty/filtered;R852/R852c只让cc4101重试但每次再中→CC放弃仍报错;R854改inject={}走普通模式,content正常;验证claude-opus真实model名8/8 OK 0 empty/filtered,真实CC流量0报错;残留偶发SSLEOF(integrate通道网络层,有重试兜底非本错);R852系列退为兜底防线保留
## R852 empty/filtered completion(thinking-only-empty) + R853 8min挂死底座
- [R852 empty content zombie修复](r852-empty-content-zombie-fix.md) — "empty/filtered completion"真根因:GLM5.2 thinking实测产出3920c reasoning但0c content(答案写进思考),旧zombie检测(content+reasoning)<50把reasoning算进去→3182c漏判→干净message_stop→CC收空报错;修R852 cc4101三处+R852b nv_gw一处全改content_chars<50(只看text answer);R852c扩展抓finish_reason=length+thinking-only截断(max_tokens满content空);验证探针大input6455c三连ZOMBIE-EMPTY-STREAM→api_error,累积5次PRIMARY-BREAKER-OPEN→503 fast-fail;小input<5000c不触发(模型正常给text)
- [R853 read timeout真根因](r853-read-timeout-root-cause.md) — ⭐8min挂死底座真根因(让R852/R847/R850都能跑的前提):cc4101 _restore_read_timeout用conn.sock但getresponse后conn.sock=None,30s read超时(CC4101_STREAM_POLL_S)从没应用到流式read→resp.read(8192)无限阻塞→stall-watcher(在read loop内)永无检查点→R847/R850 idle-gap/total-deadline全死代码→CC永远收不到api_error挂8min;修:_restore_read_timeout(conn,read_timeout,resp=resp) conn.sock None时fallback到resp.fp.raw._sock取真socket;修前挂8min修后探针run2 200s准时STREAM-IDLE-STALL→api_error→CC retry
## R854 删40007+持续卡死真根因(nv_gw强制thinking注入)
- [R854 删40007+强制thinking根因](r854-delete-40007-force-thinking-rootcause.md) — 按用户诉求彻底删cc4101四文件(config/upstream/handlers/app)全部40007/glm5_2_ms/ms_gw fallback代码,nv_gw glm5_2_nv ONLY;⭐持续卡死真根因≠cc4101:是nv_gw进程内NVCF_PEXEC_MODELS缓存了旧inject(非空{chat_template_kwargs:{enable_thinking:True}}),虽config已改inject={}但改文件不restart不生效→每请求强制thinking→GLM5.2 thinking模式产4000c reasoning但0c content+finish=length→R852c抓zombie→api_error→CC重试→同样thinking-only-empty死循环卡死;修:docker restart nv_gw让进程重读config inject={}生效;restart后探针3/3正常返text('4'/'你好')无NV-INJECT-THINKING;CC-like请求(tools+system)status200 text完整8.1s.教训:改nv_gw config.py后必restart(Python模块级常量import时求值)

## R857 mode_idx卡死+死env+429冷却
- [R857 mode停滞reset修复](r857-mode-stall-fix.md) — BUG1(upstream.py~1280):mode_idx卡3(integrate_us_single单IP7894),advance 3→3死循环24h共43次;修advance停滞(new==old)时reset到0+save,故障注入验证mode3 fault→NV-GLM52-MODE-STALL-RESET触发→reset0→mode0(integrate_us_rr)3.6s��功,idx.json 3→0;BUG2:cc4101死env FALLBACK_UPSTREAM_*三行注释(代码早不读);BUG3:NV_INTEGRATE_KEY_COOLDOWN_S 0→90(429不冷却加速撞限流);真实CC模拟5/5 OK;留BUG4(per-key单口)/BUG5(MODELS空)未动

## R858 rr_us持久轮换+chain budget
- [R858 rr_us持久轮换](r858-rr-us-persistent-rotation.md) — BUG6:rr_us旧pool[attempt_idx%len]用per-request序号每请求从0起→首attempt永远7894→实测7894:13,7895:1压倒性过载(SSL断流网络层诱因);修加模块级_glm52_rr_us_counter跨请求持久RR+同请求fault偏移,验证分布均匀2:2:2:1:1;BUG7:NVU_TIER_BUDGET_GLM5_2_NV 70→120(70仅容1次attempt=66s,1个timeout就abort chain容错名存实亡);恢复4mode chain+真实CC走cc4101 5/5 OK 1.7-2.7s text完整无empty
