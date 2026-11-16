# Tong Quant 跨设备交接

更新日期：2026-11-16，Asia/Kuala_Lumpur。本文是交接摘要，不代替运行时治理或验收。
代码事实以本地 PyCharm 项目为准；未推送的修改不会随 GitHub 克隆恢复。

## 1. 所有者与目标

所有者 Tong Li，UPM 计算机本科生。Python 3.12，主要使用 PyCharm，GitHub 账号
TONGResearch，仓库 https://github.com/TONGResearch/tong-quant-framework。
原设备项目目录：/Users/niujing/PycharmProjects/TongQuant_v1。

目标不是增加技术指标或只做基础设施，而是把实操技术与基本面结合，经验证后支持：
发现领域/股票机会、筛选、解释入场与退出条件、仓位百分比研究、持仓跟踪和风险控制，
最终在独立批准后发展受控执行。近期先交付真正可运行的只读研究辅助，不急于自动实盘。
11 月 30 日为美股只读增量目标，不是免除验收的承诺；总体范围仍含 A股、美股、港股、
马股，以及金融和非金融公司。不能以银行样本冒充全部金融行业已支持。

长期支持两种使用方式：与 AI 互动提出领域/候选，程序进一步计算、筛选和跟踪；以及
不依赖 AI 的定时数据更新与确定性计算。后者尚未完成生产部署。更新事实不等于允许
自动更换策略、阈值、数据可信度或交易权限。

## 2. 投资理念与研究链

Discovery → Hard Screening → Research Queue → Research → Investment Assessment /
Investment Score → Validation → Portfolio/Risk 研究产物 → 未来受控执行。

- 先找值得研究的机会，不把全市场直接打分后买最高分者。
- 硬失败不能被高分抵消；评分用于筛选之后的研究排序和投资质量辅助。
- Research Score 与 Investment Score 分开；队列 priority、urgency、confidence 分开。
- 长期价值研究：Survival、Cycle、Valuation、Growth，加财务、行业与政策证据。
- Market Regime 是高权重研究变量，不是牛市开/熊市关的单因子交易开关。
- 正式报告唯一模型为 research.models.ResearchReport，必须有 thesis、counter thesis、
  可证伪的失效条件；置信度不能只取评分平均值。
- 投资分数必须连同 COMPLETED / INCOMPLETE / LOW_CONFIDENCE / INSUFFICIENT_DATA
  状态解读；低置信度的高分不自动升级为机会。
- 持有长期/中期/短期是研究输入，不承诺程序能算出确定最佳买卖日或保证止损成交。

## 3. 七组实操技术与真实实现程度

这是交接分类，不是七套已经验证盈利的交易策略。多个组共享指标，不能重复投票。

| 技术组 | 当前代码事实 | 仍缺什么 |
| --- | --- | --- |
| 1. 改进海龟 | research/trend：Donchian、量比、ATR、追踪/加仓几何；完整评估要求突破、量能、情绪、行业热度四确认合取 | 合格情绪/行业数据、来源资格与真实验证；价格量能观测不是完整海龟信号 |
| 2. 指标共振 | technical/diagnostics.py：趋势结构与动能两个描述性家族，保留冲突 | 完整参与度、基本面、市值风格等证据家族和经过批准的综合决策口径 |
| 3. MACD + KDJ | technical/indicators.py：可配置数值、交叉及预热检查；MACD 柱定义为 DIF-DEA，不乘二 | 各市场参数稳健性、来源/交易时段核验和买卖有效性；超卖不代表见底 |
| 4. 大小市值 | 有股本、市值及连续性证据检查；技术诊断明确 INSUFFICIENT_DATA | 合格 PIT 市值、历史股票池、可流通股本/公司行为与跨截面风格研究；没有完成大小盘择股策略 |
| 5. 阴阳穿三线叠加均线 | technical/events.py：参数化 SMA 与蜡烛实体穿越，不能拿影线穿越冒充 | 定义/参数的真实验证；不能声称与所有软件的同名指标完全一致 |
| 6. 启动点与动态止损研究 | 因果 WATCH/ARMED/CONFIRMED/INVALIDATED/EXPIRED 状态与结构/ATR 动态失效参考 | 持仓/成本/实际风险状态和成交约束；不是持仓感知止损、触价成交或订单 |
| 7. 格兰维尔 | 八类明确事件，区分趋势延续与极端偏离均值回归 | 跨市场验证、复权/公司行为影响；均值回归不能额外算成趋势确认 |

“七加一”是另一项尚无完整规则、已由 Tong 暂缓的要求，状态 DEFERRED_BY_OWNER；
不要根据名字自行寻找相似网传方法代替。用户早期所称“海归”指上面的改进海龟。

另有 A股专属 K线研究：涨家数严格 >3000、放量长上影、一进二、强股回调、VWAP/
开盘价支撑、缩量回调，以及 10:40 前/14:40 后等原始研究时间窗。已有部分上影计算、
涨家数检查和外部证据接口；连板、支撑、回调及时间窗不是完整自动分钟交易实现。
不能移植到美/港/马，也不能把外部注释当已验证实时计算。T+1/涨跌停/停牌等市场规则
只有限定 SSE 主板试点和证据检查，尚非深沪北及所有板块的通用执行实现。

## 4. 已有的可用工程

- 11月16日完成MSFT维度映射的来源清点与最小设计，未放宽解析：45个排除出现项只引用
  35个不同context，不能当45份独立证据。两个AzureMember候选属于ProductOrServiceAxis，
  与MicrosoftCloud二级分类不同；不能换用、合计或直接生成增长结论。金额仍未采用。
  方案要求完整展开名称/维度集合/原文/期间和包装范围的审查及版本化绑定，尚未实现。
  见proposals/msft-dimensional-context-review-v1.zh-CN.md；未来测试清单不是本轮通过项。

- 11月16日新增SEC排除项的可选结构说明（explain_exclusions=True / --explain-exclusions）。
  原61项中的45项仍排除，数值/默认JSON/期间检查不变。37项出现segment，34项有祖先
  scope阻断，重叠26项；结构数量不能判断合法维度、财务错误或合并口径。哈希绑定原文，
  不授予来源资格。仅限已有SEC只读入口，尚未接入全局单股摘要、正式报告或论点执行。
  详见SEC原文审查和MSFT论点规格附记；仍无持有期限/补仓/卖出决定或PIT升级。

- 11月16日修复日历表的显示歧义：旧版在无行情/未来日期也显示原始“冲突=False”，
  新版v7明确区分未评估、行情区间外、缺盘中依据、候选日期冲突与非认证的行情缺席。
  重算哈希也不能掩盖自相矛盾的观测/span/冲突字段。原始JSON及其哈希不变，旧v6报告
  不覆盖，未选择Nasdaq来源的默认报告不变；没有来源、完整性、评分或买卖权限升级。
  同目录*-v7.zh-CN.md为新报告；详细检查结果见PROJECT_STATUS和Nasdaq来源记录。

- 11月16日完成真实日历更新演练，使用新诊断库/原文目录，不覆盖旧证据。新原文哈希变化，
  但12条完整日期声明与旧源相同，不能算第二来源验证。新源在旧分析时点不可见；新时点下
  可与微软报告合读；行情在演示24小时时效限制下仍过期，不因日历更新复活。未设置生产TTL，
  周末自然间隔不能当接口故障；价格默认UNASSESSED也不是已新鲜。新增三项端到端回归。
  私有报告在data/processed/msft-calendar-refresh-20261116；原库/WAL/报告哈希不变。
  详见nasdaq-calendar-source-2026-11-07.md；没有新运行功能、自动更新调度或实盘授权。

- 11月15日接入显式Nasdaq来源对照：海外单股入口增加日历库、原文目录、年份、正整数
  来源年龄上限四项选项，必须带--as-of，只读且仅US。新版receipt/v6摘要绑定行情哈希，
  保留完整来源、提前收市时刻、未来/过期/失败观测；不复制为TradingSession，不填周末。
  微软留存源在固定时点约8.7天，演示24小时上限下STALE，保留12条观测但当前对照为0。
  不是正式TTL，未完成完整日历、股票交易所、来源/PIT或持仓买卖条件认证。旧指标、覆盖率
  与默认摘要不改，见nasdaq-calendar-source-2026-11-07.md。

- 同日补齐年度日期覆盖核对：--calendar-coverage可结合--long-horizon或--multi-timeframe，
  仍只读同一行情库。新v2 coverage/v5摘要绑定日线、时点和日历父哈希，旧结果不改。
  微软选定行情库日历记录为0，2023/24/25年度未知日期分别365/366/365，覆盖率未确定，
  不表示没有交易日或行情为假。下一步接入可追溯、明确交易所及生效范围的日历证据，不能猜周末。

- 同日后续增加--multi-timeframe周/月/年观察与来源时间对照，新v2观察/v4中文摘要。
  周均线13/26/52和MACD/KDJ已接入；旧--long-horizon月/年结果、JSON与摘要保持原样。
  微软样例201个已结束日历周，最后来源仍是11月6日，不可当作11月13日最新日线的同步确认。
  日历周不是已核验完整交易所周K；无独立投票、共振评分或投资权限，详见同一长周期文档。

- 11月15日新增--long-horizon只读月/年观察，见long-horizon-observations-2026-11-15.zh-CN.md。
  显式年聚合、月/年SMA/MACD/KDJ和中文摘要已接入；公式复用，旧默认JSON/摘要不改。
  未结束周期不参与指标；整期缺口/停牌及已知年内缺月阻断计算。微软留存样例46个已结束月、
  3个已结束年，年MACD/KDJ明确不足。不是已核验完整月/年K、长期持有规则或多周期投票评分。

- 11月15日第二轮把论点绑定接入现有正式报告：显式配置
  DefaultResearchReportBuilder(thesis_binding_plan=plan)，由既有ResearchEngine运行。
  计划必须匹配队列、公司、UTC时点及全部原条件；现有features/SQLite可保存并重建。
  所有启用报告仍INCOMPLETE、无InvestmentScore；未来引用拒绝发布。默认旧报告字节/版本
  不变，未增加CLI或Request/Report字段。真实微软来源核验和业务条件计算仍未完成。

- 11月15日增加research.thesis_bindings可调用合同：把旧论点条件与公司/原生指标定义、
  明确期间、文件/批次/修订/时间戳引用绑定并生成确定性诊断。缺失/冲突/未来引用不算满足；
  完整声明仍NOT_EVALUATED，不能升级来源或输出买卖。未接CLI/正式报告/持久化，
  下一步才做版本化可选接入；旧模型与哈希不改。不是已完成持仓业务论点评估器。

- 11月14日完成微软持仓论点/验证实施规格设计与代码能力审查，见
  proposals/msft-holding-thesis-validation-v1.zh-CN.md。条件描述不等于已实现的窗口评估器，
  现有论点验证统计外部结果标签；不可说程序已经能自动判定持有年限、卖出或补仓。

- 11月10日增加显式SEC原文根选择，真实微软行情、最新10-Q精确期间和手工持仓可在同一只读JSON
  读取；修复组合哈希遗漏附加持仓内容，旧记录不改写。来源/会计/策略仍未准入，不是买卖判断。

- 11 月 9 日增加可选持仓复核 --holding-context，见 holding-review-2026-11-09.zh-CN.md。
  真实持仓备注只放本地忽略目录；拒绝拿买入前/陈旧日线计算当前持仓收益，不自动输出补仓/卖出
  或最优持有年限。近期优先完成微软最新季度证据、论点失效条件和实际验证，不继续只堆展示入口。

- V0.1–V0.8 已建立分层接口、配置/测试、SQLite、数据采集与缓存、筛选/队列、研究、
  验证/历史重放、Portfolio/Risk 研究产物和 Notification outbox；有迁移、完整性及恢复工具。
- 后续已有原文留存/哈希、PIT 可见性、UTC/DST、停牌保留、回滚保留和有界更新设计等硬化。
- AKShare/CNInfo 中国证据、Yahoo 海外行情与选定原生财务、SEC 目录/正文有限数值核对、
  港马原始披露/人工观测已能留存和读取。Tushare 实现冻结为可选校准源，权限不是代码缺陷。
- Massive、Finnhub 等在路线图或有限校准边界中，不得声称已有生产级全市场接入。
- scripts/inspect_global_technical.py 的只读 JSON/中文 Markdown 已能展示真实留存样本，
  包括 MACD/KDJ、三线/格兰维尔、启动状态、原生财务和可选海龟价格/成交量观测。
- A股使用既有独立检查入口。海外 CLI 支持 US/HK/MY，不是已验收的四市场统一业务入口。
- 真实 NVDA 样例已由代码运行和离线复核，不是“仅有空接口”；但取数时间是 11 月 8 日，
  最新日线观测为 11 月 6 日，不能拿它当后来任一时刻的实时价格或买入信号。

没有提供商默认可信。Trust、Coverage、AvailabilityPrecision、HistoricalContinuity、
CrossProviderConsistency 分开核查。LOW/retrieval-time 观测不能回填成历史披露时间。
同源 SDK/网页或同份 PDF 的一致不是独立双源验证，哈希也不是来源真实性证明。

## 5. 当前门槛与未完成项

| 项目 | 交接时的事实 |
| --- | --- |
| Framework / Schema / Migration | 0.8.0 / 0.8.3 / 0011_refresh_ledger |
| PIT / Production | UNSUITABLE / NOT_READY，不因测试通过或时间流逝而升级 |
| 默认模式 | execution disabled；allow_live_orders false；notifications disabled |
| WP-LAUNCH-001 | ready，未 accepted |
| WP-PAPER-001 / WP-BROKER-001 | planned；整体方向允许受控模拟/沙盒，但本包未具备开工前置，不得跳门槛 |
| 只读 R1–R6 | 规则口径、合格数据、真实研究链、策略验证、统一入口、部署恢复六组均部分完成，尚未整体验收 |
| 最新完整本地回归 | 2026-11-09：3775 passed / 6 skipped，281.65 秒；Ruff、mypy 314 文件、治理 171 项、diff 检查通过 |

上述测试来自混合本地工作区，不是隔离发布候选验收；网络跳过与合成数据不证明行情
真实、策略盈利或生产可用。最新修复为摘要所有子上下文按实际 UTC 截止时刻匹配，
新增 34 项回归；新版摘要是 equity-diagnostic-note-v2-utc-context，原 JSON/旧文件不改写。

关键缺口：证券/行业/期间/单位/修订资格、独立源一致性、历史股票池与状态连续性、
合格情绪/行业热度、大小市值、完整分钟形态、金融子行业口径、真实候选到唯一报告链，
以及技术+基本面样本外、walk-forward、稳健性、消融和成本/不可退出风险验证。
周/月观测已有聚合，但交易所完整时段资格未验收；不能把 5/21 观测代理叫完整周/月 K线。
84 天提供商证据与获准软件开发并行，不能据此停写已批准代码，也不能降低历史验证门槛。

禁止当前启用真实资金执行、真实券商下单、自动实盘、资产配置或自动再平衡。
研究产物不是订单；风险预算和仓位建议结构不代表已经为 Tong 算出了可执行金额。

## 6. GitHub 与跨设备恢复

本次交接读取时分支 codex/wp-launch-001-hardening，HEAD
8794b572f27262d73abdb031103b3bd57035efd8。大量较新代码仍未提交，最新内容不能只靠这个
提交恢复。11 月 9 日只读远端核对返回 Permission denied (publickey)，远端最新 SHA
最初未确认；不是网页登录失败。随后使用本机钥匙串成功加载已有 SSH 密钥，
只读远端查询成功，核对该分支为 6be0a842d997b7707b0d347b3206e6e003aac7fb。
该 SHA 是本轮查询记录，不是未来状态保证，也不表示已经推送。
本段记录同步前快照；后续若已完成审查推送，须以实际 Git 日志/远端核对为准，不能把
这里的历史“未提交”字样当成永久当前状态。

旧 HEAD 含已知共享原文回滚删除风险，本地保留修复尚未提交。不能绕过修复独推旧 HEAD，
也不能把全部混合改动直接打包发布。先形成明确候选及依赖闭包，在精确隔离树运行全套
检查并独立审查完整待推送范围；审查清单排除凭据、原文、数据库、缓存、日志和 IDE 文件。
仅向 TONGResearch/tong-quant-framework 对应分支非强制推送，再核对远端 SHA。

新设备启动前：

1. 先确认本次最新代码确已审查推送；克隆/更新正确分支，对照已报告的远端提交号。
2. 在新设备建立独立开发环境和自己的 GitHub 认证，不通过聊天传私钥或令牌；环境安装
   遵循 README、requirements/README.md 和匹配平台的依赖锁，不把旧 .venv 拷过去。
3. 按序读 config/project-governance.toml、AGENTS.md、PROJECT_STATUS.md、本文和选定工作包。
4. 在新设备运行下面的检查，再根据缺口继续，而不是重新搭一个平行框架。
5. 数据库和外部原文不在 GitHub；需通过已批准的加密备份共保留、恢复及哈希/迁移核验。
   较早的加密恢复成功不代表最新 NVDA 或其他样本已经备份。缺原文时明确阻断，不造数据。

```sh
.venv/bin/python scripts/check_project_governance.py
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/mypy src scripts
git diff --check
```

## 7. 下一位 Codex 应如何接手

先解决可复现交付基线：SSH 认证、审查候选/完整依赖、隔离验证、独立审查与安全同步。
不以“本地通过 3775 项”替代该步骤；不重置用户改动，不 git add .，不强推/自动变基。

然后按已批准的美股只读增量优先级，核对当前工作包与 R1–R6：补合格真实输入及行业口径，
完成真实 Discovery/Hard Screening/Queue 到 ResearchReport 的链路，再按预注册问题做
技术+基本面验证并完善只读展示。四市场的其他样本与来源证据可并行，不伪造队列/高分。
源数据暂缺时可继续获准的计算/测试，但必须保留缺口，不能把诊断包装成可信买卖判断。

后续才按依赖推进确定性 Paper 账本、成本/成交模拟、对账和恢复，再评估只读/沙盒券商。
实盘始终另行审批。只读工具能运行不等于策略有效，也不等于账户已可交给程序自主交易。

参考入口：PROJECT_STATUS.md；docs/architecture.md；docs/decision-delivery-plan-2026-10-27.zh-CN.md；
docs/four-market-readonly-release-2026-10-27.zh-CN.md；docs/technical-implementation-audit-2026-10-20.md；
docs/single-equity-usability-2026-11-08.zh-CN.md；docs/turtle-price-observations-2026-11-08.md；
docs/github-reviewed-sync-2026-11-03.md；docs/engineering-continuity.md。
