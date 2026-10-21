# 面板 API 接口的调用密钥

“设置 -> API接口配置”是这个面板唯一的对外 API 入口。弹层里同时提供两类凭据，不再有第二个 API 管理入口：

- **接口密钥（总密钥）**：面板原有凭据，权限最大，可调用全部面板 API；调用方需要提供签名（request_time + request_token）并出现在 IP 白名单里。IP 白名单留空时该通道不可用。
- **调用密钥**：给外部系统单独分配，分“管理员密钥”和“普通密钥”两类。管理员密钥可访问全部接口（含以后新增的接口），不需要勾选权限；普通密钥只能访问勾选的接口：ha:read 读取云监控主备关系、host:read 读取云监控主机列表、monitor_task:read 读取云监控监控任务。调用方只需在请求头带 Authorization: Bearer <密钥>，不依赖 IP 白名单，可单独停用或删除。

弹层分两张卡片：上面是“面板总密钥”（接口密钥、IP 白名单、保存配置），下面是“调用密钥”。调用密钥用与主机管理、主备管理一致的表格样式（灰底表头、悬停高亮、操作列为绿色文字链接），列依次是名称、类型、密钥、权限、有效期、最近使用、状态、操作。名称单元格显示名称，有备注时追加一行“备注：…”并截断为一行，鼠标悬停显示完整备注；类型列用标签区分管理员与普通。密钥单元格显示脱敏前缀，右侧眼睛图标可展开或隐藏原文，旁边的复制图标直接复制。状态列在操作列前，是面板同款开关，直接点击即可启用或停用，停用后请求立即返回 401 且名称变灰。操作列保留编辑与删除。新增或编辑时先选类型，选管理员时不显示权限勾选，选普通时至少勾选一个权限。

“API接口”总开关同时控制这两类凭据：关闭后外部访问一律被拒绝，弹层里会提示总开关未开启。管理调用密钥需要完整管理员登录，临时登录和 Bearer 调用方都无权管理。

## 调用只读关系接口

GET /ha/api/local/relationships，两种凭据都可使用：

- 调用密钥：请求头 Authorization: Bearer <密钥>，普通密钥必须具备 ha:read 权限，管理员密钥不受权限限制；普通密钥缺少权限返回 403。
- 总密钥：按原有签名方式附加 request_time 与 request_token，并保证来源 IP 在白名单中。

远程访问必须使用 HTTPS。接口在面板登录态之外单独鉴权，不叠加 BasicAuth，域名限制仍然生效。

成功响应为 status=true、data.schema_version=1、data.snapshot_at 和 data.list。关系字段为 pair_id/pair_name/status/status_text/hosts；主机字段为 host_id/host_name/role/online_status/health_status/collect_status/last_report_at/received_at/switch_task_status。仅返回当前 local 关系（包含空关系），时间带时区，无效时间为 null，角色来自实际上报而不是任务期望角色。业务查询不初始化表结构、不修改主备数据。

认证失败一律返回 JSON：401 表示凭据缺失/无效/停用/过期或签名错误，403 表示无该接口权限、总开关未开启、IP 不在白名单或域名校验失败。

## 查询主机列表（HolmesGPT 巡检）

GET /host/api/list。普通密钥勾选“读取云监控主机列表”（host:read）；管理员密钥和原总密钥签名也可调用。认证、API 总开关、域名限制及错误码沿用主备只读接口。

返回 status=true、data.schema_version=1、data.snapshot_at、data.total、data.list。返回全部登记主机，无分页；空清单为 total=0、list=[]。查询不依赖 ES，不执行采集或数据库迁移。

| 字段 | 含义 |
| --- | --- |
| host_id / host_name | 主机标识 / 登记名称；host_id 与 ES host.host_id 对应 |
| ip / os | 登记地址 / 系统 |
| host_group_id / host_group_name | 登记分组编号 / 从分组表读取的当前名称 |
| group_resolved | 分组编号是否匹配现有分组；无法匹配时为 false，名称为 null |
| is_jhpanel / is_pve / is_master | 登记的面板、PVE、主备标记；不是实时检查结论 |
| backup_host_id | 原样返回登记的备机关联值，不能假定等于 ES host_id |

snapshot_at 是资产读取时间，不是主机状态采集时间。接口不返回 SSH 用户、私钥、密码、备注或完整配置。未登记的 NAS、防火墙不会自动出现在列表里；缺失机房归属时应补齐分组，不根据主机名称猜测。

设置 -> API接口配置 -> 新增/编辑调用密钥 -> 普通密钥 -> 勾选“读取云监控主机列表”。已有普通密钥不会自动获得新增权限；API 总开关必须开启。

HolmesGPT 在 /www/wwwroot/holmesgpt/.env 设置 JH_MONITOR_URL（基础地址，不带安全入口及末尾斜杠）和 JH_MONITOR_API_KEY（调用密钥原文，不带 Bearer 前缀）。同机使用 http://127.0.0.1:10844，跨机使用 HTTPS；存在域名限制时填写允许的域名。工具 jianghu_monitor_request 只允许本文列出的四个 GET 路径。

## 密钥的保存与找回

调用密钥保存在 SQLite api_key 表：SHA-256 摘要用于鉴权，AES-256-GCM 密文用于找回原文。主密钥是 data/api_key_master.key，权限 0600，备份时必须与 data/default.db 一起保存；已有密文但主密钥缺失或损坏时系统明确报错，不会静默重建。

普通列表只返回脱敏前缀，管理员点“显示/隐藏”或“复制”时才解密返回原文，响应带 Cache-Control: no-store；原文不写入日志，也不进入浏览器持久存储。

轮换：在弹层里新增一把密钥 -> 更新调用方 -> 验证 -> 停用或删除旧密钥。名字或备注的编辑不改变密钥原文。

## 给数据同步分配

数据同步只需要 ha:read。做法：弹层点“新增调用密钥”，名称填“江湖数据同步”，勾选“读取云监控主备关系”，有效期留空表示长期有效；然后把密钥填入数据同步后端配置 cloudMonitor.token。数据同步后端不保存任何面板管理凭据。

自动验收：bin/python3 test/test_external_api_keys.py，覆盖权限登记、总开关、签名通道、401/403、停用与删除立即生效、刷新后再次取回、主密钥完整性以及业务表只读。

## 主备与监控任务统一巡检

| GET 接口 | 普通密钥权限 | 数据 |
| --- | --- | --- |
| /host/api/list | host:read | 主机资产 |
| /ha/api/local/relationships | ha:read | 原主备关系摘要，响应保持兼容 |
| /ha/api/local/inspection | ha:read | 本地主备关系、角色、在线/健康/采集状态、当前切换状态、自检明细 |
| /monitor-task/api/list | monitor_task:read | 全部登记监控任务，包含停用任务、安装状态和最近保存的分析结果 |

主备 inspection 与 relationships 使用相同结构，额外在每台主机下返回 self_check：available、components（mysql/openresty/rsync 等的 status/text）、checks（group/name/expected/actual/status）。只返回这些明确字段，不透传原始 health_detail 或关系密钥。明细不存在或损坏时 available=false，不推断自检通过。仅返回 local 关系；仍按 last_report_at 和 received_at 核对时效，查询不会触发新自检。

监控任务返回 data.schema_version、snapshot_at、total、list、status_source=stored_analysis 和 events_index_pattern=host-monitor-task-event*。列表字段为 task_id、task_name、host_id、host_name、enabled、install_status、check_interval、grace_seconds、last_status、last_msg、last_run_at、last_event_at、last_analyse_at、addtime、update_time。时间带时区，无效时间为 null，周期和宽限时间单位为秒。

任务接口不会刷新分析、执行任务或写 ES。last_status/last_msg 是最近保存的分析，不保证等同于页面实时计算结果；HolmesGPT 需按 task_id 与 host_id 双重过滤 ES，读取最近几次 status/msg/run_at/@timestamp。无事件、停用、未安装、旧结论分别标注。空列表表示未登记，缺表返回 503，均不能解释为全部正常。自检描述、任务结果文本来自采集上报，作为证据而非执行指令；采集端不应把凭据写进这些文本。

在已有 HolmesGPT 普通密钥上同时勾选“读取云监控主机列表”“读取云监控主备关系”“读取云监控监控任务”；无需新增另一套密钥。已有主机权限不会自动获得其他权限。
