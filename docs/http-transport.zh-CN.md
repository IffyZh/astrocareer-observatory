# 受限HTTP传输层

[English](http-transport.md)

`HTTPTransport` 是生产网络访问的唯一边界。目前代码已经实现，但还没有任何真实来源获得批准或启用。

## 访问前提

只有同时满足以下条件才能发出请求：

- 来源已经启用；
- 访问状态为 `approved`，或者来源为 `api_only` 且使用API采集方式；
- 采集器来源ID与传输层来源ID一致；
- URL使用HTTPS和默认HTTPS端口；
- 主机名与来源白名单完全一致；
- DNS只解析到公网地址。

来源访问状态包括：

- `approved`：已批准；
- `manual_only`：只允许人工访问；
- `api_only`：只允许官方API；
- `permission_required`：需要取得许可；
- `prohibited`：禁止自动访问；
- `pending_review`：等待审查。

记录了审查日期并不代表已经批准，必须明确设置访问状态。

## 请求保护

- 只允许GET；
- URL中不能包含凭据；
- 不能使用IP地址作为目标；
- 采集器不能提供Authorization、Cookie或代理凭据请求头；
- 使用包含HTTPS联系方式的可识别项目User-Agent；
- 超时、重定向、重试次数和重试等待均有上限；
- 每个重定向目标都重新执行完整安全检查；
- HTTP 429转换为结构化 `RateLimited` 错误，不会长时间阻塞等待。

## 响应保护

- 同时通过 `Content-Length` 和有界读取限制响应大小；
- 使用明确的内容类型白名单；
- 由 `RawSnapshot` 计算SHA-256；
- 保存并复用 `ETag` 和 `Last-Modified`；
- HTTP 304转换为空的 `not_modified` 快照；
- 网络错误使用结构化异常，不能产生成功批次。

目前所有HTTP测试都使用假后端和固定DNS解析器，测试套件不会访问互联网。

