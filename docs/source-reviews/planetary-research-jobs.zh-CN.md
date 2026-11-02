# 来源审查：Planetary Research Jobs Atom feed

[English](planetary-research-jobs.md)

## 1. 身份与用途

- 来源 ID：`planetary-research-jobs-feed`
- 公开名称：Planetary Research Jobs
- 所属机构：Planetary Research Cooperative
- 首页：<https://jobs.planetary-research.org/>
- 预期用途：通过网站支持的 Atom feed 发现行星科学职位
- 预期维护者：AstroCareer Observatory 贡献者
- 审查日期：2026-11-01
- 下次强制审查：2027-05-01；若 feed、政策或所有权发生变化则提前审查

## 2. 支持的访问方式

- [ ] 官方 API
- [x] RSS 或 Atom feed
- [x] 邮件订阅
- [ ] 可下载数据集
- [x] 公开 HTML 页面
- [ ] 仅人工采集

首选方式是官方全量职位 Atom feed：<https://jobs.planetary-research.org/feed>。网站 FAQ 明确将其提供给 feed 阅读器使用，因此它比抓取 HTML 更稳定、侵入性更低。

## 3. Robots 与条款

- Robots：<https://jobs.planetary-research.org/robots.txt>
- 获取日期：2026-11-01
- 获取结果：没有提供 robots 文件；应用返回普通的“Job announcement not found”页面
- Feed 文档：<https://jobs.planetary-research.org/faq#feeds>
- 隐私政策：<https://jobs.planetary-research.org/privacy>
- 审查日期：2026-11-01

本次审查没有在公开导航中发现独立的使用条款或数据集许可证。没有许可证不等于允许重新发布 feed 内容。以下批准只覆盖对网站明确提供的 feed 进行克制访问，不覆盖批量再发布。

Feed 和公开职位页面不需要账户，本采集器不得进行身份验证。

## 4. 明确访问决定

- [x] `approved`
- [ ] `manual_only`
- [ ] `api_only`
- [ ] `permission_required`
- [ ] `prohibited`
- [ ] `pending_review`

批准对官方全量职位 Atom feed 进行单次、未认证的 GET 请求，频率不得高于每六小时一次。HTML 列表和详情页不在批准范围内。实现审查已经完成，并使用公开项目仓库作为联系 URL。

审查者：AstroCareer Observatory 项目审查

决定日期：2026-11-01

## 5. 技术边界

- 精确允许域名：`jobs.planetary-research.org`
- 允许路径：仅 `/feed`
- 最小间隔：21,600 秒（六小时）
- 每次运行最多请求：1 次
- 预期类型：`application/atom+xml` 或其他 XML 媒体类型
- 2026-11-01 观察到的响应大小：约 1.25 MB
- 最大允许响应：2 MB
- 分页：未发现；feed 表示当前可见公告
- 稳定标识：Atom 条目的 `id`，与站内公告 URL 一致
- 项目联系 URL：<https://github.com/IffyZh/astrocareer-observatory>

服务器提供 `ETag` 或 `Last-Modified` 时，应使用条件请求。

## 6. 证据保存与发布

- 完整响应：可以暂存用于解析；当前数据库层不会写入原始字节
- 公开测试夹具：只能使用合成内容
- 招聘全文：不得发布或提交
- 短证据摘录：只有必要且经过单独审查时才可保存
- 规范化事实：标题、机构、地点、日期、类别、聘用条件、来源 URL 和观察元数据可以在署名后保存
- 来源 URL 与哈希：可以发布
- 必要署名：标明 Planetary Research Jobs 并链接原始公告
- 删除或更正：审查请求期间停止发布有争议记录；使用内部溯源事件保留历史，而不是静默改写

Feed 中的“Inquiries”联系人信息和“Posted by”ORCID 标识会被主动丢弃。可以将外部官方公告 URL 保存为来源信息，但跟随这些链接需要另行完成来源审查。

## 7. 个人数据评估

Feed 内容可能包含联系人姓名、邮箱、ORCID 标识，以及正文中的人名。这些都不是初版市场数据库所必需的。采集器只解析非联系人摘要字段白名单，不得把完整正文复制到规范化记录。

## 8. 故障与监控

- 明确空结果：具有正确身份元数据、结构有效且不含条目的 Atom feed
- 预期数量：零条或更多当前公告；正常范围在首批监控运行后确定
- 失败条件：根节点或命名空间错误、feed 身份错误、XML 损坏、响应超过 2 MB、媒体类型异常、不安全重定向，或所有条目均损坏
- 部分结果：保留有效条目，并为损坏或重复条目生成结构化错误
- 自动停用条件：政策变化、重复结构故障、意外要求登录，或域名/路径变化
- 人工关闭方式：在 `data/sources.toml` 中设置 `enabled = false`

## 9. 审批清单

- [x] 已选择侵入性最低的受支持访问方式。
- [x] 已审查并链接 robots、FAQ 和隐私政策。
- [x] 访问决定明确。
- [x] 已记录允许域名、路径、请求数量和间隔。
- [x] 已记录保存及再发布规则。
- [x] 已记录个人数据处理方式。
- [x] 正常、空结果、损坏和结构变化夹具通过测试。
- [x] 不需要凭据。
- [x] 在实现审查完成前来源保持禁用。
- [x] 已配置公开项目联系 URL。

## 10. 最终说明

本审查批准访问 feed，不批准重新发布 feed 内容，也不批准抓取雇主官方链接。扩大采集字段或请求范围前必须重新审查。

实现审查结果（2026-11-01）：采集器已通过正常、空结果、XML 损坏、部分损坏、不安全 XML、外部域名和结构变化等合成测试。一次临时真实 feed 快照成功解析出 125 条记录且没有解析问题。该快照只保存在 `/tmp`，没有进入仓库或数据库。

启用结果（2026-11-02）：公开仓库 <https://github.com/IffyZh/astrocareer-observatory> 已提供所需的项目联系 URL。该来源现按上述六小时最小间隔、单请求采集边界和 2 MB 响应上限启用。

首次启用后的真实干运行（2026-11-02）：单次请求返回 131 条记录、0 个解析问题和 131 个规范化候选。没有保存响应快照、来源记录或候选；本地只保留最小化访问审计时间，确保 dry-run 不能绕过六小时间隔。
