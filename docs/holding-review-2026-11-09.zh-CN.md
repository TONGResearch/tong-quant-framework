# 单股持仓复核与微软优先交付

日期：2026-11-09。沿用 WP-LAUNCH-001 的美股只读增量，不接受整个工作包。
Tong 本轮优先要求：先让真实微软持仓能持续获得技术加基本面的解释，研究持有、退出和补仓条件。
11 月 30 日仍是可运行只读版本目标，不是保证策略通过验证或批准实盘的日期。

## 本轮实现

在已有 `scripts/inspect_global_technical.py` 增加可选 `--holding-context`，复用同一价格读取、
原始日线选择和现有技术公式，不新建 ResearchReport、投资评分、券商账本或交易入口。
`application.holding_review` 只接受显式本地手工备注；这是应用复核合同，不是 Portfolio 持仓模型。
版本 `HOLDING_REVIEW_VERSION=owner-holding-review-v1-readonly`。

- 明确证券、市场、报价币种、数量、备注成本、观察时间、声明记录时间、投资意向和年龄上限。
- 数量/成本/亏损复核百分比用有界 Decimal 字符串；拒绝浮点、非有限数、异常精度、未知字段和凭据。
- 观察/记录/分析时间比较实际 UTC；未来记录、错证券/币种和原始行情未来/复权/重复冲突均阻断。
- 最新停牌不回退；旧行情、早于持仓观察的行情或陈旧持仓备注不计算价格差异和仓位观察值。
- 只有可对照的价格才计算不含费用/汇率/分红/公司行为的描述性变化，不声称是账户实际收益。
- 用户声明的亏损百分比仅产生复核提醒，不是建议止损位、自动卖出或保证最大损失。
- 保留技术家族冲突、预热、原生财务缺口；行情/技术的输入哈希绑定到单独复核标识。
- 期限保持 NOT_ESTIMATED，基本面论点失效保持 NOT_EVALUATED，补仓依据未验证则保持阻断。
- 原生年度财务与当前季度披露不同；本切片不新增财报映射、跨源合并、验证结果或推荐分数。
- 原入口 JSON/Markdown 不选择该参数时不变。只读模式不抓取、不改数据库，退出码仍为 2。

声明记录时间不是可信时钟证明或历史 PIT 资格。哈希只核对内容；真实成交、账户现金、费用、融资、
结算和后续仓位/公司行为连续性没有核实。即使条件看似有利，也不授予交易/评分/验证权限。

## 本地微软样例

所有者提供的 22:48:49 持仓截图包含 MSFT 数量和显示平均成本；实际数值仅写入本地备注。
仅作为 OWNER_REPORTED_UNVERIFIED 备注录入忽略目录，未保存账号、订单号或完整账户截图。
不能从平均成本推定费用口径或真实成交均价。融资状态、成本是否含费均 UNKNOWN。
没有把这笔真实交易包装成策略通过或 Paper Trading 记录。

```sh
.venv/bin/python scripts/inspect_global_technical.py \
  --database data/processed/equity-comparison-20261109-QXEqWg/snapshot.sqlite3 \
  --artifact-root data/processed/equity-comparison-20261109-QXEqWg/raw \
  --market us --symbol MSFT --as-of 2026-11-09T15:02:58+00:00 \
  --fundamentals --sector-profile nonfinancial --trend-observations \
  --holding-context data/processed/msft-holding-review-20261109/holding.toml \
  --format markdown
```

这里两个 604800 秒上限只是此次显式示例配置，不是已批准的日常时效标准或 7 天内无需复核的承诺。
截至本次留存，最新日线仍是 11 月 6 日，因此相对于今晚持仓观察，应该输出
PRICE_PREDATES_HOLDING_OBSERVATION，价格收益为空。不得拿旧 530.61 与新成本假造当日账户亏损。
没有新网络抓取，不声称覆盖 11 月 9 日收盘或当前盘口。

这些备注、原文和数据库由 Git 忽略，不随 GitHub 同步或自动加密备份。换设备需按已有恢复流程另迁移。
本地示例路径不是跨设备可保证存在的固定部署路径。代码没有安装后台更新或提醒服务。

## 本轮最新季度证据推进

随后通过现有 SEC adapter/neutral ingestion 实际抓取目录与正文，未修改提供商实现。
目录含 1005 条披露记录，明确选择 2026-10-28 的 10-Q：
CIK 0000789019，accession 0001193125-26-436133，原生文件 msft-20260930.htm。
正文 SHA256 为 02b4114045c34fdd95c32b1efbf9acde4afffc094d887031b19b0be5bb5fc825。
仅在本次进程内使用所有者已提供的联系身份，不持久化请求头或联系信息。

独立忽略目录 `data/processed/msft-sec-20261109-xok7gp2w` 保留 snapshot.sqlite3、raw/ 和
exact-quarter-periods.json。既有精确期间读取器按明确起止日读取 2026/2025 年 7 月 1 日至
9 月 30 日的以下五个原生标签，共 10 项期间检查：RevenueFromContractWithCustomerExcludingAssessedTax、
OperatingIncomeLoss、NetIncomeLoss、NetCashProvidedByUsedInOperatingActivities、
PaymentsToAcquirePropertyPlantAndEquipment。10 项状态均为 OBSERVED_SUBSET_UNQUALIFIED；
不能把这称为 10 项已核实财务事实或完整季度研究。

来源实际可用时间为本轮 11 月 9 日抓取，不回填成 10 月 28 日已经持有的数值证据。
完整所选标签共61个原生出现项，45项不支持；10项期间检查中6项提示存在未解析的其他标签上下文。
须连同期间原文一起审查，不因所选子集一致就忽略。目录声明可找到MSFT，但状态仍为
TICKER_DECLARED_UNVERIFIED，不是股类/历史证券身份认证。
这些标签不自动映射 Yahoo 原生年度字段，不生成财务分数、财务失效结论或持有年限。
同源SEC原文不是独立双源校准。新库原文根与旧行情根不同，当前单根 CLI 不能直接混配；
本轮未自动复制原文、改注册路径或声称已完成同一入口的合并研究。

新诊断库新增2批次、2条证据、2份注册原文，canonical daily_bars/fundamental_facts均0条；
无schema变更。两份注册原文 2/2 哈希核对通过，不等于完整备份、数值真实性或 PIT 准入。
精确期间 JSON 的分析时点为 2026-11-09T15:13:28.573833+00:00，内容标识为
055be22569c2c37f32c262168b48ccf82234340df525f495d382c6868629bcec。
重复离线读取完全一致，较早15:02:58读取为SOURCE_UNAVAILABLE，数据库无改写；当前门槛不放行。

## 从这一步到真正有用的持仓分析

以下是本轮优先级，不是新增方法/阈值的自动批准：

1. 微软证据：完成最新季度和历史可比季度的官方原文留存、精确财年/单位/股类与字段核对；
   把网页人工研究和现有 SEC 输入之间的缺口明确消除，不把原生年度变化冒充当前季度。
2. 预先定义持仓论点：云与软件竞争力、利润和现金兑现、估值及反论点；每个失效条件绑定指标、
   期间、来源和待审阈值。3—5 年只是聊天中的人工规划，不是当前模型计算值。
3. 技术结合：沿用 MACD/KDJ、均线/三线、格兰维尔及改进海龟；不重复投票、不将缺少情绪/行业热度
   的价格突破当四确认。长期价值与趋势跟随分别研究，不用短线死叉机械决定长期清仓。
4. 真正验证：预注册适用的退出/分段研究和不同持有窗口，再做可靠样本的滚动、样本外、稳健性和
   成本/汇率敏感性检查；保留失败、低置信度和来源缺口，不能用单只历史最优参数反推今晚策略。
5. 部署：按已批准数据范围接更新、时效与失败恢复，验证安装/重启/加密恢复与源树身份；受限版本
   输出证据、冲突和复核条件，不把未通过部分称为决策完成。实盘另需独立审查与批准。

月底最低交付验收：输入 MSFT 能运行同一研究路径、解释持仓与证据时间差、展示真实技术与财报，
列出已评估/未评估条件和验证状态，重复运行可复核，缺失/冲突/过期明确阻断。
本轮仅完成持仓复核基础；不把这张清单算成上述五项已经完成。

## 测试与边界

覆盖成本/数量输入、恰好触及用户阈值、旧价/陈旧上下文、未来/夏令时、停牌不回退、证券/币种、
复权拒绝、内容标识和 US/HK/MY CLI 默认不变、只读/无建库/错误过滤。
新增54项（46项单元、8项CLI）；最终全量pytest为3829通过、6跳过，379.05秒；
Ruff、mypy（315个源文件）、治理检查（172项）和git diff --check通过。
静态检查三个应用/CLI文件没有Execution/Broker/Order/Trade/Fill/Paper/Portfolio/Notification导入。
原候选和当前代码对真实MSFT的默认JSON/Markdown完全一致，旧行情库哈希保持不变。
本轮无新增凭据或账号字段；真实备注和新库/原文均被Git忽略，备注文件权限设为600，
但文件权限不等于加密。合成/跳过网络测试不验证微软投资收益或数据真实性。
测试针对当前混合工作区，不是独立候选树验收或独立变更审查；未提交/推送。
没有 schema/依赖/默认开关变化，没有 Execution、Paper、Broker、Portfolio 或 Notification 实现。
PIT UNSUITABLE、production NOT_READY、execution/notifications disabled 均保持。
