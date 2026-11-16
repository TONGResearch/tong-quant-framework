# A 股离线更新请求桥接

日期：2026-11-03。WP-LAUNCH-001，ready / not accepted。

## 实现

data.refresh_plan.akshare_daily_refresh_request 将显式 A 股日线范围转换成现有
DailyBarRequest：原代码、YYYYMMDD 窗口、China A、EQUITY、Adjustment.NONE。
不导入或实例化 AkShareAdapter，不联网，不调用下载、归一化或入库。
命令入口仍是 scripts/plan_data_refresh.py，没有采集／执行／定时参数。

静态桥接只接受 akshare / a_share_daily / china_a。CNY、Asia/Shanghai、显式交易所
和代码的保守路由声明须相符：SZSE 000/001/002/003/300/301；SSE
600/601/603/605/688/689；BSE 920/4/8。均须为六位 ASCII 数字。
这些是请求范围，不是经时点核实的上市、板块、证券类别或可交易证明。
未识别路由保留 UNSUPPORTED；已识别路由与币种／交易所矛盾则拒绝整个无效配置。
指数、基金、B 股、财报／状态等未实现范围不伪装成股票日线请求。

桥接不改变旧适配器的请求或回退逻辑，不删除 ST／停牌／退市对象。
NONE 仅声明请求不复权，不能证明上游历史值未经调整。BSE 路由可以转换，不等于
北交所真实响应已可得；实际来源、原文完整性、成交量单位、修订、日历／会话、
可用时间和上市状态仍须单独校验。未来采集器必须保留旧 AKShare 下载器实际
使用的端点，回退不能冒充新的独立提供商或成功校准。

## 两种请求边界不能混用

计划中新增 request_contract 与 provider_contract_versions，区分：

- Yahoo：ProviderDatasetRequest，已有静态校验，ISO 日期及各数据集原有参数。
- AKShare：DailyBarRequest，日期转换、显式 EQUITY/NONE/market；固定 fetch、
  routing、normalization 版本。这个对象不是 AkShareDailyBarEvidenceAdapter 的
  ProviderDatasetRequest；后者接收已经下载的 RawDataset 和匹配条目，要求空参数。

证据留存接口不能被这份计划调用、初始化或冒充。尚无完整收集／留存桥接、
预采集尝试、租约、重试／恢复或任务检查点。collection_authorized、
research_refresh_authorized 和 schedule_enabled 仍为 false，所有权限和数据观察
保持 NOT_TESTED／UNKNOWN。示例现在五项均为静态请求通过，不代表数据已获取。

计划版本升为 offline-data-refresh-plan-v2-akshare-request，避免静默解释旧哈希。
framework 0.8.0、schema 0.8.2、迁移头 0010_portfolio_evidence_lineage、Financial
与默认配置不变。本轮不改旧 Provider、交易、Portfolio、Notification 或数据库逻辑。

## 验证

在上轮 46 项计划测试上新增 23 项：A 股／创业板／科创板／BSE 路由、严格请求
转换、错误币种／交易所、指数／基金等拒绝或保留不支持项、来源版本与未知权限。
旧离线 I/O、凭据、UTC、未来窗口、确定性与四市场保留测试继续执行。
定向 **69 项通过**；全量 **3092 通过、6 跳过**，155.04 秒。Ruff、mypy（300 文件）、
治理检查（149 项）、git diff --check 通过。跳过项为可选真实联网测试；
本轮不进行真实网络可用性测试，测试通过不等于数据／策略／部署准入。

实际只读 CLI 在示例时点 2026-11-03T05:00:00+00:00 下保留全部五项静态请求，
plan_hash 为 7d6dc347f83c9af636f407ad85f601667494859350a160d35747f5c1d74f2366。
Git 仍为 8794b572f27262d73abdb031103b3bd57035efd8，dirty=true；该标志不能
代替未提交代码内容的审查／指纹。源码边界和新增配置未发现凭据或交易依赖；
本轮没有新增数据库／缓存／原文文件，不构成完整旧脏工作区的发布／保密认证。
价格／原生财务库与原文库的 SHA-256 分别保持
0f9e2f06c5e9763568b279d3b213081e70ea96569af053f266edaa5a0126c087 和
ce1e3ae4c2b97bb52733cd35724189ab80d2360ec62e3b5d3f38cf6ea506da13 不变。

下一步：专有任务／尝试账本最小迁移及故障恢复，再实现一次性受控更新器。
新[双模式使用边界](ai-assisted-and-independent-operation.zh-CN.md)明确 AI 互动是
研究入口，独立更新／规则运行是部署目标；两者不可跳过研究、验证与风控。
当前无需 Tong 提供密码或新账户；没有安装任何定时器，也没有自动提交或推送。
