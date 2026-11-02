# Restricted HTTP transport

[简体中文](http-transport.zh-CN.md)

`HTTPTransport` is the production network boundary. The reviewed Planetary Research Jobs Atom feed is the first enabled real source.

## Access prerequisites

A request is permitted only when all of the following are true:

- the source is enabled;
- its access status is `approved`, or it is an `api_only` source using the API collection method;
- the collector source ID matches the transport source ID;
- the URL uses HTTPS and the default HTTPS port;
- the hostname exactly matches the source allowlist;
- DNS resolves only to public addresses.

Source access statuses are:

- `approved`;
- `manual_only`;
- `api_only`;
- `permission_required`;
- `prohibited`;
- `pending_review`.

Review dates do not imply approval. Access status must be set explicitly.

## Request safeguards

- GET requests only;
- no credentials in URLs;
- no literal IP-address targets;
- no collector-supplied authorization, cookie, or proxy headers;
- identifiable project User-Agent with an HTTPS contact URL;
- bounded timeout, redirects, retry count, and retry delay;
- every redirect target is fully revalidated;
- HTTP 429 is returned as a structured `RateLimited` error and is not slept through.

## Response safeguards

- configured maximum response size, checked through both `Content-Length` and bounded reading;
- explicit content-type allowlist;
- SHA-256 calculated by `RawSnapshot`;
- `ETag` and `Last-Modified` retained and reused for conditional requests;
- HTTP 304 converted to an empty `not_modified` snapshot;
- network failures use structured exceptions and do not create successful batches.

All current HTTP tests use a fake backend and fixed DNS resolver. The test suite performs no internet requests.
