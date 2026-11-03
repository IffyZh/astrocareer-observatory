# 采集运行器

[English](runner.md)

运行器是从采集器进入来源记录和规范化候选数据库的唯一正式路径。

## 处理流程

```text
核对来源与采集器身份
→ 检查启用状态和最小访问间隔
→ 恢复最近一次checkpoint
→ 通过Transport执行采集
→ 规范化有效来源记录
→ 在一个事务中保存批次和待审核候选
→ 返回结构化报告
```

运行器不会将候选自动接受到正式岗位表。

## 安全门槛

- 采集器ID必须与来源登记ID一致。
- 默认禁止运行未启用来源。
- 根据已保存的运行历史执行来源级最小访问间隔。
- 失败批次不能包含来源记录或规范化候选。
- 批次持久化与候选持久化共享同一事务。
- 运行时间必须包含时区。
- 仅用于fixture的安全覆盖必须明确指定，不能成为生产默认值。

## 离线干运行

当前命令行可以使用本地fixture测试虚构采集器：

```bash
PYTHONPATH=src python3 -m astrocareer collect-fixture \
  demo-html-source tests/fixtures/demo_source/normal.html \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

干运行会解析并规范化记录，但不会创建采集运行、快照、来源记录观察或候选数据库记录。

去掉 `--dry-run` 会保存离线fixture结果。该命令仍然使用只读取指定本地文件、无法访问网络的 `FixtureTransport`。

## 生产边界

可以在不写入数据的情况下采集经过审查的 Planetary Research Jobs feed：

```bash
PYTHONPATH=src python3 -m astrocareer collect \
  planetary-research-jobs-feed \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

生产命令使用受限的 `HTTPTransport`，不提供 fixture 专用的“允许禁用来源”覆盖参数，并执行来源登记中保存的最小访问间隔。网络干运行只会写入同步后的来源登记和最小化访问审计时间，因此不能通过重复 dry-run 绕过访问间隔；它不会保存响应快照、来源记录或规范化候选。只有在检查真实干运行成功后才应去掉 `--dry-run`；持久化运行只保存溯源信息和待人工审核的规范化候选，不会自动接受为公开岗位记录。

## 本地捕获与离线重放

在一次正常网络采集中保存响应：

```bash
PYTHONPATH=src python3 -m astrocareer collect \
  planetary-research-jobs-feed \
  --database data/local/astrocareer.sqlite3 \
  --registry data/sources.toml \
  --capture-local data/local/captures/planetary-2026-11-03.capture.zip
```

捕获文件是不可变的 ZIP，其中包含响应字节，以及记录 URL、观察时间、HTTP 元数据和 SHA-256 摘要的小型清单。已有捕获绝不会被覆盖。捕获可能含有第三方文本或个人信息，因此应保存在被 Git 忽略的 `data/local/` 下；未经单独的数据权利审查不得发布。

可以无限次离线重放该响应，不访问网络，也不计入来源冷却：

```bash
PYTHONPATH=src python3 -m astrocareer replay-capture \
  planetary-research-jobs-feed \
  data/local/captures/planetary-2026-11-03.capture.zip \
  --database data/local/replay.sqlite3 \
  --registry data/sources.toml \
  --dry-run
```

只有确实需要保存离线重放结果时才去掉 `--dry-run`。解析器实验应优先使用单独的重放数据库，以免与主要观察历史混在一起。

如果只修改了规范化规则，可以直接用已保存的来源观察记录重建候选项，无需重放或再次请求 feed：

```bash
PYTHONPATH=src python3 -m astrocareer db renormalize-source \
  data/local/astrocareer.sqlite3 planetary-research-jobs-feed
```

同一规范化版本重复执行不会产生重复记录。命令不会修改来源观察记录；旧版待审核候选会标为 `superseded`，当前版本候选以 `pending` 状态等待审核。

## 定时采集

`.github/workflows/collect.yml` 每天两次运行经过审查的 Planetary Research Jobs feed 采集器，也支持手动触发。并发组保证同一时刻最多只有一个采集任务。每次成功运行会恢复最近的 `collector-state` artifact，追加一组不可变的观察记录和规范化候选，检查 SQLite 完整性，再把更新后的数据库保存 14 天，供下一次运行延续历史。

数据库 artifact 包含快照元数据和采集器白名单允许的来源记录，但不包含原始 HTTP 响应字节或完整招聘描述。它是运行状态，并不是带版本的公开数据集发布。如果找不到可用的旧 artifact，工作流会新建数据库，并在运行摘要中明确说明。官方公告链接继续只作为数据保存，本工作流不会请求这些链接。
