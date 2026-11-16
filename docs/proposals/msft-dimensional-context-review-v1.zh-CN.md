# MSFT 财报维度映射最小审查方案 V1

日期：2026-11-16，Asia/Kuala_Lumpur。
范围：ready 的 WP-LAUNCH-001 / P1 原文和定义审查。
状态：已完成留存原文清点与设计；未批准维度解析、金额准入或会计映射。
没有新增运行模块、域模型、来源、策略、阈值、schema 或交易功能。

## 1. 核对基线

复用已有 SEC 原文的父目录、批次、字节和固定时点核验，不联网重抓或请求命名空间 URI。
CIK：0000789019；accession：0001193125-26-436133。
固定截止时间：2026-11-09T15:13:28.573833+00:00，不是本轮的最新披露时点。
原文 SHA256：02b4114045c34fdd95c32b1efbf9acde4afffc094d887031b19b0be5bb5fc825。
既有排除审计哈希：38d5bfc88b729f32f684bc7fe1185f3a07859a62d88bd96fe32daf34340ad10a。
新清点哈希：216ccc701d265ba91a8d3d6097005b378ea1853e2661536ce5330679f61be647。

已在同一只读快照内重建并核对原审计，再验证原始 artifact 后才观察 XML 引用。
沿用有界 XML/DTD/entity 检查；按每个元素自己的命名空间作用域展开 QName。
URI 是观察到的名称组成部分，不代表已下载/认证对应 taxonomy 或模式文件。
没有提取被排除项目的金额，也没有关闭祖先范围、target、维度或上下文安全边界。

私有清点位于 data/processed/msft-dimension-audit-20261116/dimension-inventory.json。
两次清点规范 JSON 完全一致，4 个已存在的 DB/WAL/审计/期间文件哈希不变。
该目录被 Git 忽略，文件权限 600；不是 GitHub 代码同步或已完成的异地加密备份。
一次性审查工具不是生产适配器，也没有新增公开运行入口或调度任务。

## 2. 观察结果与分母

分母仅为五个显式标签在该文件中的 61 个出现项，原有 45 项仍被排除。
45 个出现项引用 35 个不同 context ID；每个引用可唯一解析不等于有 45 个不同上下文。
其中 37 项各有一个 explicitMember 观察，其余 8 项没有该类维度成员观察。
共观察到 6 种展开后的轴名与 17 种轴/成员组合；不是整份财报或公司的完整维度清单。

为便于阅读，下面以来源中的 namespace 缩写列示；实际清点和拟议绑定必须保存完整 URI。

- gaap26：http://fasb.org/us-gaap/2026
- srt26：http://fasb.org/srt/2026
- msft26：http://www.microsoft.com/20260930
- country26：http://xbrl.sec.gov/country/2026

| 展开后的轴 | 观察到的成员类别 | 排除出现项归属计数 | 不能据此做的事 |
| --- | --- | ---: | --- |
| srt26:ProductOrServiceAxis | Product、ServiceOther，以及 Azure、MicrosoftThreeSixFiveCloud 等来源成员名 | 20 | 将产品、服务和子业务相加或替代合并收入 |
| gaap26:StatementBusinessSegmentsAxis | msft26:AgentsAndInfraMember、DevicesAndConsumerMember | 8 | 当作已核实分部定义或移植旧分部映射 |
| srt26:StatementGeographicalAxis | country26:US、gaap26:NonUsMember | 4 | 将地区收入和产品收入当作互斥独立机会 |
| gaap26:StatementEquityComponentsAxis | gaap26:RetainedEarningsMember | 2 | 当作本期营业利润或可自由分配现金 |
| srt26:ScheduleOfEquityMethodInvestmentEquityMethodInvesteeNameAxis | msft26:OpenAIGlobalLlcMember | 1 | 当作微软合并业务整体增长 |
| msft26:ProductsOrServicesSecondaryCategorizationAxis | msft26:MicrosoftCloudMember | 2 | 当作 Azure 的等价定义或独立第二来源 |

这些类别只描述标签和结构，不认证其业务含义、合法性、合并范围或财务正确性。
原祖先范围阻断 34 项涉及 4 个 nonNumeric 名称，但祖先归属计数合计 36；同一事实可以
有多个嵌套祖先，不能相加为 36 个独立排除项。8 个无该类维度成员的项目也不能自动放行。

## 3. Azure 候选引用，不是已采用财务输入

两个仍被排除的出现项使用以下组合：

- 概念：gaap26:RevenueFromContractWithCustomerExcludingAssessedTax。
- 轴：srt26:ProductOrServiceAxis；成员：msft26:AzureMember。
- 原始期间文本分别为 2026-07-01 至 2026-09-30、2025-07-01 至 2025-09-30。
- 原始元素位置：37456、37469；确切 context ID 和完整路径保存在私有清点中。
- 祖先名：gaap26:ScheduleOfEntityWideInformationRevenueFromExternalCustomersByProductsAndServicesTextBlock。
- 原排除原因为 nested or targeted document scope is unsupported；本次只观察到祖先阻断。

这说明存在需要进一步审查的 Azure 命名候选，不说明 Azure 金额/增速已被模型采用。
不能把它替换成 MicrosoftCloudMember、合并总收入或旧的分部定义。
2026 命名空间中出现 2025 比较期间是观察事实，不得强制 namespace 年份等于财务期间年份；
也不能由此认定历史定义未变化、没有重分类或这些数据已在 2025 年可用。
原始期间字符串尚未被本清点认证，不能直接当成已批准连续财季。

## 4. 现有接口缺口

SECPeriodSelection 仅有 native_tag、period_start、period_end。当前非维度安全子集阻止了
上述混用，不能为接通候选字段而移除该边界。未来仅靠同名 tag 加相同期间不足以选择维度。
ThesisMetricBinding 有 namespace 与自由文本 statement_scope，但后者不是完整、类型化的
维度集合，也不是会计口径资格。不能把旧 scope 字符串自动解释成合格合并/分部定义。

最小扩展应在现有来源/期间绑定路径旁提供前瞻版本的显式 context 限定，不新增第二个
ResearchReport，也不静默改变旧模型、序列化、历史身份或默认查询含义。具体 API 尚待审查。

## 5. 拟议约束，尚未实现

1. 绑定精确 CIK/accession、原文/输入/批次哈希、事实索引、context 引用和实际 UTC 可用时点。
2. 绑定概念及所有轴/成员的展开名称：namespace URI 加 local name；词法前缀只留原文痕迹。
3. 使用完整的维度集合精确匹配，额外/缺失维度必须阻断；不得只挑出一个喜欢的成员。
4. 区分“未声明”“显式维度集合”“经审查的合并口径”。空集合不自动等于合格合并数据。
5. 期间、entity、单位、scale/sign/精度仍走原有检查；比较期间和修订另行核验，不按容器数量放行。
6. 包装范围只允许独立审查后的精确展开名称和结构。不得全局删除 nonNumeric 阻断，
   也不得放宽 target、tuple、continuedAt、嵌套数值或重复身份限制。
7. typedMember、多轴、维度默认成员、扩展 schema/linkbase 未核验时维持明确不支持。
8. 原文变化、上下文身份变化或最新失败须重新审查，不猜测新 ID 或回退到旧有利值。
9. 观察到 URI 或同源数字一致不构成会计资格；LOW/retrieval_time 和 PIT 限制独立保留。
10. 仅在来源及方法资格单独满足后，才讨论数值条件。此方案不批准阈值、窗口、评分或结果标签。
11. 不因命名空间或schema引用自动联网加载。后续语义验证需另有固定来源、版本哈希、
    截止时点和外部实体/资源边界；若范围扩大，应评估成熟实现，而非扩写成自制完整验证器。

## 6. 未来验收清单

- 相同展开名称的前缀改名保持等价；同 local name 不同 namespace 绝不能合并。
- 节点内部重新绑定前缀须使用当地作用域；未知或不受支持的维度引用不能猜测。
- Azure 与 MicrosoftCloud、产品与地区、分部与权益项目以及无维度/额外维度不能互换。
- 相同 context 被多个事实引用、相同事实有多层祖先时不增加独立证据票数。
- 同标签同期间的多处披露必须保留来源位置及潜在冲突，不挑首次、最新或更有利的金额。
- 固定旧截止时间不得消费新抓取/修订/映射；不得由 taxonomy 年份推断期间或可用时间。
- 新能力必须是可选、前瞻版本；旧默认 JSON、哈希、数值和拒绝行为必须保持。
- 没有来源资格、真实队列、方法预注册及 Validation 时，不输出 InvestmentScore 或买卖决定。

这些是待实现的测试规格，不是本轮新增并通过的测试。
本轮只有只读来源清点与设计；运行代码、schema、依赖和默认关闭状态不变。
PIT UNSUITABLE、production NOT_READY，未提交或推送。
基线 pytest：4121通过、6跳过，384.34秒；Ruff、mypy（318源文件）、治理（176项）、
差异/新文件空白和限定默认关闭/私有产物检查通过。这些混合工作区检查不是精确发布候选、
独立来源资格或会计/方法验收；没有新增运行测试或把设计清单计入通过数。
