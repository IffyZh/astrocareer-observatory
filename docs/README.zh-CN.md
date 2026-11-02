# 项目文档

[English](README.md)

AstroCareer Observatory 的文档将随项目实现逐步完善。计划包含：

- 数据模型与数据字典；
- 来源与证据记录规则；
- 数据源审查与采集器开发；
- 数据采集伦理、版权和隐私；
- 本地使用方式和公开数据导出；
- 分析方法、覆盖范围和已知限制。

仓库根目录的[中文 README](../README.zh-CN.md)是当前的项目契约。

适用于整个项目的治理文件位于仓库根目录：

- [安全政策](../SECURITY.zh-CN.md)
- [数据权利与发布政策](../DATA_RIGHTS.zh-CN.md)
- [Apache License 2.0](../LICENSE)

## 当前设计文档

- [数据模型 v0.1](data-model.zh-CN.md)
- [采集器契约](collectors.zh-CN.md)
- [规范化与审核](normalization.zh-CN.md)
- [采集运行器](runner.zh-CN.md)
- [受限HTTP传输层](http-transport.zh-CN.md)
- [来源审查模板](source-review-template.zh-CN.md)

## 已审查的真实来源

- [AAS Job Register](source-reviews/aas-job-register.zh-CN.md)——需要许可，禁止自动访问
- [Planetary Research Jobs Atom feed](source-reviews/planetary-research-jobs.zh-CN.md)——feed 适配器已验证，等待项目联系 URL 后启用
- [Research Organization Registry 数据快照](source-reviews/ror-data-dump.zh-CN.md)——已批准并实现 CC0 机构目录离线导入
