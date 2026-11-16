# 离线数据更新计划器

日期：2026-11-03。现有 WP-LAUNCH-001 内的第一阶段交付，ready / not accepted。

后续同日 [v2 A 股静态请求桥接](akshare-offline-refresh-bridge-2026-11-03.md)已补齐，
五项示例均可转换／校验请求；下文的四项通过／A 股不支持是 v1 原始交付状态。
本轮此前完整回归为 **3069 通过、6 跳过**，145.80 秒；Ruff、mypy（300 文件）、
治理（147 项）与 diff 检查通过。两份保留证据库哈希不变。v2 结果见后续文档。

## 本轮实现

```text
显式 TOML 自选范围 + 带时区计划时点 + 本地 Git 提交／脏状态
  -> 有界严格解析
  -> 复用已有静态 Provider 请求校验
  -> 确定性 JSON 计划／不支持项／缺口
```

新增 data.refresh_plan 和 scripts/plan_data_refresh.py，不建立新策略、研究模型、
数据库表、采集任务或定时服务。计划器不联网、不打开数据库、不读取凭据，也不
调用 Provider.fetch／下载器。CLI 仅读取指定配置和 Git 元数据，输出到终端。

使用示例（示例股票不是持仓、推荐、已验收身份或自动更新授权）：

```sh
.venv/bin/python scripts/plan_data_refresh.py \
  --watchlist config/refresh/example-watchlist.toml \
  --as-of 2026-11-03T05:00:00+00:00
```

示例显式覆盖 A 股／美股／港股／马股五项范围，包括价格和一项原生年度财务。
四项 Yahoo 请求为 REQUEST_SCOPE_VALIDATED，仅证明静态请求契约通过；一项
AKShare 为 UNSUPPORTED / no_offline_refresh_bridge，保留原始范围而不替换来源。
这**不表示现有 AKShare 采集不能工作**，只是统一更新计划到旧采集入口的桥接
尚未实现。CNInfo、SEC、原文、生命周期／公司行为等尚无本计划器的已核定桥接。
本轮不改变已有 Provider 接口或 Tushare 冻结状态。

所有项的提供商权限 NOT_TESTED，数据可用性、信任、可用时间精度和日历 UNKNOWN；
这里 UNKNOWN 表示未观测，不是修改已有数据的 DataTrustLevel／AvailabilityPrecision。
既不检测权限、网络、库存、过期或“是否需要更新”，也不推导缺失交易日。
币种／交易所／证券代码是声明，不是独立身份确认；原生年度财务并不验证这两个
身份字段，原生 OHLC 也未取得未复权准入。金融／非金融评分均不因此放行。

## 契约与安全

- 配置只有 version 和 scopes；每项必须显式给出 provider、dataset、market、
  subject、currency、exchange、timezone、start_date、end_date。
  最多 128 项／128 KiB，拒绝未知字段、错误类型、敏感字段、URL 和非法标签。
- 同一 provider/dataset/market/subject 只能出现一次，防止重叠窗口伪装独立任务；
  不支持项仍显示，不自动降级提供商。窗口不可倒置、超过 15000 天或延伸到
  计划时点之后的市场本地日期。当天窗口仅作原始请求，不宣称已收盘。
- 固定配置／范围哈希、版本、UTC 时点、框架／schema、适配器模型版本、Git
  提交／脏状态；输入排序和等价 UTC 时点不影响计划哈希，DST 两个时点须区分。
  scope_hash 固定包括窗口的声明；plan_hash 不是调度任务 ID、检查点或响应哈希。
  脏状态不是工作区内容指纹，Git 提交本身也不等于审查过的部署基线。
- planned_as_of 不是 captured_at／available_at。未来采集仍必须使用实际下载后
  获取时间，不能为符合旧计划而倒填时点。未知发布／修订时间保持未知。
- collection_authorized、schedule_enabled、research_refresh_authorized、
  closed_bar_qualified 恒为 false。无执行参数、网络探测、数据库初始化或文件输出开关。
- CLI 拒绝末级符号链接，限长读取，Git 查询各限时五秒；输入／Git 异常返回
  安全通用错误，不回显配置内容、原始异常或凭据。它不是密钥库，仍禁止在配置
  中放任何真实秘密；格式校验不能保证识别所有任意裸字符串秘密。

## 验证与影响

新增 46 项测试覆盖确定性、乱序、UTC／DST、四市场可见性、不支持项、窗口、
上下文哈希变化、类型／界限／重复项／敏感输入、CLI 安全错误及 I/O 边界。
网络／数据库／下载器替身会在调用时使测试失败；库不调用子进程，CLI 只准两次
Git 只读查询，临时配置目录无新增文件。真实提供商权限和可用性未测试。

唯一新增版本常量为 offline-data-refresh-plan-v1。框架 0.8.0、schema 0.8.2、
迁移头 0010_portfolio_evidence_lineage、Financial 版本及默认配置均不变。
全量检查结果已补记于文首；无新数据、原文、迁移、安装服务或交易代码。

## 余下工作

下一步先核定 AKShare／原文刷新桥接与专用任务／尝试账本的最小迁移，随后实现
一次性有界更新器、预采集尝试、租约隔离、重试、恢复／提交后对账与检查点。
失败快照留存成功不能算数据更新成功；没有响应不能伪造哈希。
此后才审查股票池、运行设备和数据授权，单独启用定时服务；最后连接经独立准入
的研究更新。当前不需 Tong 提供密码或新账户，不更改对话定时跟进任务。

PIT UNSUITABLE；production NOT_READY；R1–R6 partial；执行／通知默认关闭。
不提交、不推送。原有未提交工作、来源／行业方法验收、最新披露、策略验证与
代码／数据库／外部原文的加密共保留仍待完成；不能按对话次数保证可交易日期。
