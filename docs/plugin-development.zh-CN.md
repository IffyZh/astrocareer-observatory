# 采集器插件开发

[English](plugin-development.md)

采集器插件负责把一个经过审查的来源适配到稳定的 `SourcePosting` 契约。网络政策、访问频率、本地捕获、规范化编排、数据库事务和审核状态仍由核心系统控制。

## 包结构

外部适配器可以放在独立、可安装的 Python 包中：

```text
astrocareer-collector-example/
├── pyproject.toml
├── src/astrocareer_collector_example/
│   ├── __init__.py
│   ├── collector.py
│   └── plugin.py
├── tests/
│   └── test_collector.py
├── fixtures/
└── SOURCE_REVIEW.md
```

采集器实现统一协议，并且只能通过传入的 `Transport` 发出网络请求：

```python
from astrocareer.collectors import CollectionBatch, RequestSpec, Transport


class ExampleCollector:
    source_id = "example-source"

    def collect(self, transport: Transport, checkpoint=None) -> CollectionBatch:
        snapshot = transport.fetch(
            RequestSpec(
                source_id=self.source_id,
                url="https://jobs.example.org/feed",
                purpose="job_listing_feed",
            )
        )
        return self.parse(snapshot)
```

在 `plugin.py` 中公开一个带版本的描述对象：

```python
from astrocareer.plugins import CollectorPlugin

from .collector import ExampleCollector


plugin = CollectorPlugin(
    source_id=ExampleCollector.source_id,
    collector_factory=ExampleCollector,
    collector_version="example-feed-1",
    normalizer_version="rules-1",
    fixture_content_type="application/atom+xml; charset=utf-8",
    max_response_bytes=2_000_000,
    supports_network=True,
)
```

通过 Python entry point 登记该对象：

```toml
[project.entry-points."astrocareer.collectors"]
example-source = "astrocareer_collector_example.plugin:plugin"
```

Entry-point 名称、描述对象的 `source_id`、采集器的 `source_id` 和经过审查的 `sources.toml` ID 必须完全一致。重复 ID、API 版本不符或身份不符都会安全失败。

## 来源政策仍然独立

安装插件并不代表已经授权采集。必须另行添加并审查同 ID 的来源定义，包括允许访问的域名和路径、访问状态、最小间隔及再发布说明。只有插件设置 `supports_network=True`，并且来源定义已经启用和批准时，核心系统才允许生产 HTTP 访问。

插件接收核心系统提供的受限 `Transport`；不能直接调用 `urllib`、`requests`、socket、浏览器自动化或子进程。Python 插件是可执行代码，并不处于沙箱中，因此自动化环境只能安装经过审查并锁定版本的包。

## 版本与测试

- 当提取行为的变化会影响保存的来源记录时，递增 `collector_version`。
- 只有选择的规范化规则发生变化时才修改 `normalizer_version`。
- Fixture 应尽量精简，去掉不必要的个人信息和受版权保护文本。
- 测试正常响应、明确空响应、异常记录、重复来源 ID 和页面布局变化。
- 同一个不可变快照必须始终产生相同批次。
- 测试不能访问网络。

可以检查已安装的登记项：

```bash
PYTHONPATH=src python3 -m astrocareer plugins list
PYTHONPATH=src python3 -m astrocareer plugins inspect example-source
```

`plugins list` 只发现 entry-point 名称，不导入外部插件模块。`plugins inspect`、采集和重放只加载指定的插件。
