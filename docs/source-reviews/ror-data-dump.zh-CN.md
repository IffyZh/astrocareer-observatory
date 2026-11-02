# 来源审查：Research Organization Registry 数据快照

[English](ror-data-dump.md)

## 1. 身份与用途

- 来源 ID：`ror-data-dump`
- 公开名称：Research Organization Registry（ROR）数据快照
- 所属项目：Research Organization Registry
- 机构库：<https://ror.org/registry>
- 数据快照文档：<https://ror.readme.io/docs/data-dump>
- 预期用途：为科研机构建立稳定身份、名称、域名、机构类型和地点种子数据
- 审查日期：2026-11-01
- 下次强制审查：2027-05-01，或采用新的 ROR 主版本 schema 之前

## 2. 支持的访问方式

ROR 通过 Zenodo 发布带版本号的完整 JSON 数据快照，并提供用于单条查询的 REST API。ROR 文档明确建议需要完整机构库时使用数据快照。AstroCareer Observatory 初版只导入使用者已经下载并解压的本地 JSON；自动下载不在本次批准范围内。

## 3. 权利与条款

- ROR 条款：<https://ror.org/about/terms/>
- Schema 字段：<https://ror.readme.io/docs/fields>
- 审查日期：2026-11-01

ROR ID 和机构库元数据采用 CC0 1.0 公共领域贡献。ROR 网站正文和 Logo 使用不同条款；导入器不会采集 Logo，也不会复制网站说明文字。

## 4. 明确决定

- [x] `approved`
- [ ] `manual_only`
- [ ] `api_only`
- [ ] `permission_required`
- [ ] `prohibited`
- [ ] `pending_review`

批准范围：离线导入官方 ROR Schema 2.x JSON 数据快照。导入必须记录数据集版本和 SHA-256 哈希。本决定不授权抓取 ROR 中列出的机构网站。

## 5. 导入字段

- ROR ID 和记录状态；
- 显示名称、标签、别名和缩写；
- 官方域名与网站链接；
- 机构类型；
- 成立年份；
- 基于 GeoNames 的地点元数据；
- ROR 记录创建与修改日期。

第一版暂不导入机构关系和外部标识符。没有导入这些字段，不代表 ROR 中不存在这些信息。

## 6. 安全与更新行为

- 只接受 Schema 2.x 记录。
- 导入具有原子性：一条记录无效会回滚整个快照。
- 重复 ROR ID 会使导入失败。
- 完全相同的文件再次导入时复用已有导入记录。
- 消失的旧域名保留为非活动历史，而不是直接删除。
- 不会因为某条记录没有出现在后续输入文件中就将其标为停用；只信任 ROR 明确给出的状态。
- `import` 类型来源被禁止使用 HTTP 传输层。

## 7. 个人数据

ROR 描述机构而不是申请者。当前选择的字段不包含申请者档案或联系人信息，也不导入邮箱和具名联系人。

## 8. 实现结果

导入器已通过合成 Schema 2.1 夹具验证，包括首次导入、重复导入、记录更新、旧域名停用和原子回滚。目前尚未下载或导入完整的官方 ROR 数据快照。
