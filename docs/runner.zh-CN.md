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
