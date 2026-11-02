# 数据模型 v0.1

[English](data-model.md)

本文定义第一版概念数据模型，暂时不绑定某种数据库实现。在创建第一次数据库迁移之前，字段名称仍可能调整。

## 通用规则

1. 官方表述与规范化后的值必须分别保存。
2. 不是由本项目直接产生的事实，应关联来源证据。
3. 如果知道数据缺失的原因，就不能只保存一个含义不明的空值。
4. 保存人数而不是人工计算的比率；比率由人数自动计算。
5. 不能仅凭岗位名称推断门槛、技能、合同条件或竞争数据。
6. 信息的发布时间、系统观察时间和核查时间必须分别记录。

## 值的可用状态

可选事实字段使用 `availability` 表示值的可用状态。只有当状态为 `reported`，或者适用时为 `derived`，才填写具体数值。

| 值 | 含义 |
|---|---|
| `reported` | 某个可识别来源明确报告了该值。 |
| `derived` | 由已报告的数据按可复现规则计算得到。 |
| `not_reported` | 已审查的来源没有说明该值。 |
| `not_applicable` | 该字段不适用于此岗位或招聘流程。 |
| `not_yet_available` | 招聘尚未完成，数据以后可能出现。 |
| `inaccessible` | 已知来源存在，但当前无法访问。 |
| `ambiguous` | 来源包含相关信息，但无法可靠规范化。 |
| `redacted` | 来源明确隐去或拒绝公布该值。 |
| `not_collected` | 项目尚未尝试收集此字段。 |
| `parsing_failed` | 已尝试采集，但自动解析失败。 |

这里有意不使用 `unknown`，因为它无法解释为什么没有值。无法确认旧数据缺失原因时，应使用 `not_collected`，并记录导入限制。

## 时间字段

所有时间使用 ISO 8601。具体时刻统一存储为 UTC。如果来源只提供日期而没有时刻，就保留为日期，不能自行添加时刻或时区。

| 字段 | 类型 | 含义 |
|---|---|---|
| `posted_at` | 日期时间或日期 | 来源声明的公告发布时间。 |
| `application_deadline_at` | 日期时间或日期 | 官方申请截止时间。 |
| `first_seen_at` | 日期时间 | 本项目第一次观察到该岗位的时间。 |
| `last_seen_at` | 日期时间 | 最近一次成功观察到该岗位的时间。 |
| `observed_at` | 日期时间 | 某一次具体采集或快照的时间。 |
| `source_updated_at` | 日期时间或日期 | 来源声明的更新时间。 |
| `verified_at` | 日期时间 | 某项事实最近一次自动或人工核查时间。 |
| `closed_at` | 日期时间或日期 | 可以确认的关闭或撤销时间。 |

`posted_at` 和 `first_seen_at` 不能互换。如果来源只写“三天前”，应保存原始表达；推算出的日期必须标为派生值。

## 岗位 Posting

`Posting` 是项目为一次招聘机会建立的稳定身份。同一岗位可以通过多个来源和多次网页快照观察到。

核心字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `posting_id` | UUID | 由项目控制的稳定标识符。 |
| `title` | 文本 | 规范化显示名称。 |
| `official_title` | 文本 | 权威来源中出现的正式岗位名称。 |
| `institution_id` | UUID | 关联到规范化机构。 |
| `location` | 结构化值 | 可获得的国家、地区、城市及远程状态。 |
| `job_family` | 受控值 | 例如博后、教职、科研软件、技术人员或科研支持。 |
| `positions_available` | 非负整数 | 仅在来源明确说明时填写岗位数量。 |
| `status` | 受控值 | 观察到的岗位生命周期状态，不是预测。 |

可选字段必须使用前述可用状态。

## 机构目录

`Institution` 是岗位所引用的规范机构身份。经过审查的 ROR Schema 2.x 快照可以填充其 ROR ID、显示名称、状态、国家、首页、成立年份和来源日期。

关联表分别保存多语言名称、官方域名、机构类型和基于 GeoNames 的地点。域名具有首次发现、最后发现和是否活动字段，因此域名变更不会静默删除历史。每条导入数据保留 ROR 来源 ID；每次导入则记录数据集版本、文件哈希、导入器版本、schema 版本以及新增和更新数量。

进入 ROR 不代表该机构与天文学有关，也不代表项目获准抓取它的域名。相关性分类和招聘入口审查属于后续独立阶段。

## 雇佣条件

`EmploymentTerms` 将官方工作条件原文与规范化值分别保存。

| 字段 | 类型 | 含义 |
|---|---|---|
| `contract_type` | 受控值 | `permanent`、`fixed_term`、`fellowship`、`temporary`、`casual` 或 `other`。 |
| `contract_type_availability` | 受控值 | 规范化合同类型的可用状态。 |
| `contract_duration_months` | 非负整数 | 来源明确说明或可复现推导的合同期限。 |
| `contract_duration_availability` | 受控值 | 合同期限的可用状态。 |
| `employment_fraction` | 0至1之间的数值 | 全职当量，1.0表示全职。 |
| `employment_fraction_availability` | 受控值 | 全职当量的可用状态。 |
| `start_date` | 日期或来源文本 | 预计或要求的入职日期。 |
| `start_date_precision` | 受控值 | `date`、`month`、`year` 或 `text`。 |
| `start_date_availability` | 受控值 | 入职日期的可用状态。 |
| `work_mode` | 受控值 | `onsite`、`hybrid`、`remote`、`flexible` 或 `other`。 |
| `work_mode_availability` | 受控值 | 工作模式的可用状态。 |
| `official_text` | 文本 | 支持这些条件的来源原文。 |
| `evidence_id` | UUID | 支持证据。 |

“可能续约”不能使固定期限合同变成永久合同。将年数换算成月数时，应将期限标为 `derived`，而不是 `reported`。

## 薪酬

每条 `Compensation` 表示一项薪资或报酬说明。如果公告提供多种方案或分开的报酬组成，可以保存多条记录。

| 字段 | 类型 | 含义 |
|---|---|---|
| `amount_min` / `amount_max` | 非负数值 | 确切金额或来源说明的范围。 |
| `currency` | ISO 4217代码 | 来源声明的币种。 |
| `pay_period` | 受控值 | 年、月、周、日、小时或整个合同。 |
| `gross_net` | 受控值 | `gross`、`net` 或 `not_stated`。 |
| `availability` | 受控值 | 值的可用状态或缺失原因。 |
| `official_text` | 文本 | 薪资官方原文。 |
| `evidence_id` | UUID | 支持证据。 |

数据库保存来源给出的名义金额。货币换算、购买力调整和税后收入估计属于后续分析层，并且必须记录各自的日期和假设。

## 工作语言

`PostingLanguage` 将每种语言分别记录，并保留官方原文和要求等级。岗位所在国家本身不能作为语言要求的证据。

## 官方求职门槛

`EligibilityRequirement` 记录官方或其他可识别来源明确说明的申请条件。每项门槛单独保存，使互相矛盾或随时间改变的要求能够与各自证据同时存在。

| 字段 | 类型 | 含义 |
|---|---|---|
| `requirement_id` | UUID | 稳定标识符。 |
| `posting_id` | UUID | 关联岗位。 |
| `requirement_type` | 受控值 | 学位、专业、经验、国籍、居留、语言、论文记录、可入职日期、安全许可或其他。 |
| `level` | 受控值 | `required`、`preferred`、`desirable` 或 `informational`。 |
| `official_text` | 文本 | 在合理引用范围内保存的相关官方原文。 |
| `normalized_value` | 结构化值 | 能够可靠转换时保存的机器可查询解释。 |
| `availability` | 受控值 | 值的可用状态或缺失原因。 |
| `evidence_id` | UUID | 支持该事实的证据。 |
| `valid_from` / `valid_to` | 日期时间 | 要求发生变化时可用的有效区间。 |

项目不能把“优先考虑”转换成“必须具备”。学位门槛应区分学位类型、专业、是否已经取得，以及是否允许在入职前取得。

## 技能要求

`SkillRequirement` 表示来源提到的一项研究或技术能力。

| 字段 | 类型 | 含义 |
|---|---|---|
| `skill_requirement_id` | UUID | 稳定标识符。 |
| `posting_id` | UUID | 关联岗位。 |
| `skill_id` | UUID | 关联到规范化技能词表。 |
| `official_term` | 文本 | 来源使用的术语，例如 Python 或 HPC。 |
| `level` | 受控值 | `required`、`preferred`、`desirable` 或 `mentioned`。 |
| `experience_minimum` | 时长 | 仅在来源明确说明时记录最低经验。 |
| `official_text` | 文本 | 相关来源上下文。 |
| `availability` | 受控值 | 值的可用状态或缺失原因。 |
| `evidence_id` | UUID | 支持该事实的证据。 |

规范化技能可以有别名，但必须保留官方术语。仅仅出现某个关键词，并不能证明它是硬性技能要求。

## 外国申请资格与签证难度评估

外国申请可行性分为两层。招聘方的明确表述是观察事实；结合这些事实与官方政策得到的签证可行性，是带日期并且针对特定申请人情景的派生判断。派生判断不能覆盖底层证据。

### 招聘方明确说明的外国申请资格

`InternationalEligibility` 记录招聘公告或招聘机构明确说明的内容。

| 字段 | 类型 | 含义 |
|---|---|---|
| `international_eligibility_id` | UUID | 稳定标识符。 |
| `posting_id` | UUID | 关联岗位。 |
| `applicant_eligibility` | 受控值 | 招聘方说明的申请资格类别。 |
| `applicant_eligibility_availability` | 受控值 | 申请资格类别的可用状态。 |
| `work_authorization_requirement` | 受控值 | 是否要求申请人已经拥有工作许可。 |
| `work_authorization_availability` | 受控值 | 工作许可要求的可用状态。 |
| `visa_support` | 受控值 | 招聘方对签证担保或协助的说明。 |
| `visa_support_availability` | 受控值 | 签证支持表述的可用状态。 |
| `official_text` | 文本 | 相关来源原文。 |
| `evidence_id` | UUID | 来自公告或招聘机构的证据。 |

初始 `applicant_eligibility` 值包括：

- `explicitly_open`：来源明确欢迎或允许外国申请者；
- `open_with_conditions`：满足明确条件时允许外国申请；
- `citizenship_required`：必须具有指定国籍；
- `residency_required`：必须具有指定居留身份；
- `existing_work_authorization_required`：必须已经拥有工作许可；
- `restricted_other`：存在其他明确限制；
- `not_reported`：已审查来源没有说明；
- `ambiguous`：存在相关表述，但无法可靠分类。

初始 `visa_support` 值包括：

- `sponsorship_available`：可以提供签证担保；
- `relocation_or_visa_assistance_available`：可以提供搬迁或签证协助；
- `case_by_case`：逐案决定；
- `sponsorship_unavailable`：明确不提供签证担保；
- `not_applicable`：不适用；
- `not_reported`：没有说明；
- `ambiguous`：表述含糊。

初始 `work_authorization_requirement` 值包括：

- `not_required`：不要求已有工作许可；
- `required_before_application`：申请前必须已有工作许可；
- `required_before_start`：入职前必须取得工作许可；
- `employer_may_sponsor`：招聘方可能提供担保；
- `other_condition`：存在其他明确条件。

公告没有提到国籍或签证时，必须保存为 `not_reported`，不能解释为允许，也不能解释为禁止。

### 派生签证可行性评估

`InternationalAccessAssessment` 针对某个明确申请人情景，在特定时间点评估一个岗位。它是分析结果，不是官方签证承诺，也不是法律意见。

| 字段 | 类型 | 含义 |
|---|---|---|
| `assessment_id` | UUID | 稳定标识符。 |
| `posting_id` | UUID | 关联岗位。 |
| `applicant_profile_id` | UUID | 只包含评估所需因素的版本化情景档案。 |
| `destination_country` | ISO 国家代码 | 适用移民政策的目的国。 |
| `route_id` | 文本 | 能够确定时记录的签证或工作许可路径。 |
| `assessment_level` | 受控值 | 总体难度类别。 |
| `eligibility_result` | 受控值 | `apparently_eligible`、`conditionally_eligible`、`apparently_ineligible` 或 `indeterminate`。 |
| `reason_codes` | 受控值列表 | 支持评估结果的因素。 |
| `explanation` | 文本 | 不包含敏感个人数据的可读推导说明。 |
| `availability` | 受控值 | 值的可用状态或缺失原因。 |
| `policy_as_of_at` | 日期 | 审查政策来源所对应的日期。 |
| `assessed_at` | 日期时间 | 自动生成或人工核查评估的时间。 |
| `method_version` | 文本 | 评估规则版本。 |
| `job_evidence_ids` | UUID 列表 | 来自岗位或招聘机构的证据。 |
| `policy_evidence_ids` | UUID 列表 | 来自官方移民政策的证据。 |
| `expires_at` | 日期 | 可选的强制重新评估日期。 |

初始 `assessment_level` 值包括：

- `low_friction`：除常规材料外，未发现明显移民障碍；
- `moderate`：存在明确可用路径，但有实质行政条件；
- `high`：是否可行取决于较多条件或招聘方采取行动；
- `very_high`：可能存在路径，但重大限制使申请非常困难；
- `ineligible`：明确规则或岗位限制使该情景不符合资格；
- `indeterminate`：现有证据不足或互相矛盾。

该等级是有序分类，不是概率。例如 `moderate` 不代表签证获批概率为 50%。

初始原因代码可以包括：

- `citizenship_restriction`：国籍限制；
- `residency_restriction`：居留限制；
- `existing_authorization_required`：要求已有工作许可；
- `employer_sponsorship_required`：需要招聘方担保；
- `employer_sponsorship_confirmed`：招聘方确认提供担保；
- `employer_sponsorship_not_stated`：招聘方没有说明担保；
- `salary_threshold_met` 或 `salary_threshold_uncertain`：满足或无法确认薪资门槛；
- `occupation_or_researcher_route_available`：存在职业或科研人员专用路径；
- `qualification_recognition_required`：需要学历或资质认证；
- `security_clearance_restriction`：安全许可限制；
- `contract_too_short_for_route`：合同期限不满足路径要求；
- `policy_source_outdated`：政策来源已经过期；
- `insufficient_job_information`：岗位信息不足。

### 申请人情景与隐私

评估可能取决于国籍、当前居留或工作许可、学位层级、职业阶段及签证路径要求的其他事实。公开数据应使用不具身份识别性的版本化情景，例如“没有现有欧盟工作许可的非 EEA 博士申请者”。个人真实档案必须保存在私有层，不能提交到公开仓库。

### 评估规则

- 以政府官方移民信息作为主要政策证据。
- 记录政策日期，并在政策或岗位变化时重新评估。
- 不能仅根据目的国推断外国申请难度。
- 招聘方是否提供担保与法律上是否存在签证路径必须分开记录。
- 不能把 `not_reported` 的签证支持解释为 `sponsorship_unavailable`。
- 缺少必要申请人条件时不能强行评分，应使用 `indeterminate` 并说明原因。
- 结果只能作为求职研究参考，不能表述为法律意见，也不能保证入境、担保或签证获批。

## 招聘人数指标

竞争数据不直接作为岗位表中的固定列，而是保存为带日期的指标。这样可以同时记录招聘阶段、统计定义和来源不同的数据，而不会互相覆盖。

| 字段 | 类型 | 含义 |
|---|---|---|
| `metric_id` | UUID | 稳定标识符。 |
| `posting_id` | UUID | 关联岗位或招聘批次。 |
| `metric_type` | 受控值 | 类型见下文。 |
| `value` | 非负整数 | 数据可用时的人数。 |
| `availability` | 受控值 | 值的可用状态或缺失原因。 |
| `as_of_at` | 日期时间或日期 | 该人数对应的统计日期。 |
| `population_definition` | 文本 | 来源对统计人群的定义。 |
| `evidence_id` | UUID | 支持该指标的证据。 |

初始 `metric_type` 包括：

- `applications_submitted`：来源定义的全部已提交申请；
- `applications_eligible`：正式认定符合资格的申请；
- `applications_complete`：单独公布时的完整申请；
- `candidates_shortlisted`：进入短名单的人数；
- `candidates_interviewed`：进入面试的人数；
- `offers_made`：发出的 Offer 数量；
- `hires_final`：最终录用人数或正式填补的岗位数量。

这些人数不能互相替代。公开的合格申请人名单不能保存为总报名人数，除非来源明确说明两者属于同一统计人群。

## 派生录用指标

“录用比”容易产生歧义，因此主要指标命名为 `selection_rate`（录用率）：

```text
selection_rate = hires_final / applications_submitted
```

为了便于理解，也可以显示其倒数：

```text
applicants_per_hire = applications_submitted / hires_final
```

计算规则：

- 分子和分母必须属于同一岗位或同一招聘批次。
- 两个人数都必须为 `availability = reported`，且统计人群定义相容。
- `selection_rate` 必须标为 `derived`，不能人工录入。
- 报名人数为零时，录用率不可计算，原因为 `not_applicable`。
- 最终录用人数为零时，录用率为 `0`；每个录用名额对应的申请人数不可计算，原因为 `not_applicable`。
- 派生比率应继承两项人数的证据链接和统计日期。
- 来源公布的比率可以作为原始证据保存；如果同时公布了人数，项目仍应自行重新计算。

面试率、Offer 率等阶段性比率必须使用明确名称，并明确分母。

## 证据 Evidence

`Evidence` 用于支持某项事实、门槛、技能或招聘人数指标。

最低字段包括：

- `evidence_id`；
- 来源及规范 URL；
- 来源机构；
- 来源类型及权威等级；
- 可获得的发布日期；
- `observed_at`；
- 内容哈希；
- 解析器版本；
- 核查方式和 `verified_at`；
- 足以定位相关表述的引用或位置；
- 已知的再发布限制。

权威等级描述来源与某项事实之间的直接程度，不代表该事实为真的概率。

## 实现前仍需决定的问题

- 岗位类别和技能应该使用什么受控词表？
- 只有日期的值和带时区的时刻应共用字段还是分开保存？
- 同一公告招聘多个要求不同的岗位时，应如何拆分？
- 对第一批来源，哪些证据片段允许保存和再发布？
- 移民政策证据经过多长时间应自动过期并触发重新评估？
- 公开数据应该包含哪些不具身份识别性的申请人情景？
