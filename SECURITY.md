# Security Policy

[简体中文](SECURITY.zh-CN.md)

## Supported versions

The project is in early development and has not made a stable release. Security fixes are applied to the latest revision of the `main` branch only.

## Reporting a vulnerability

Do not disclose exploitable details, credentials, personal data, or private source material in a public issue, discussion, pull request, or commit.

Once the GitHub repository enables private vulnerability reporting, use its **Security → Report a vulnerability** form. Until that private channel exists, open a public issue containing only the sentence “Private security contact requested.” A maintainer can then arrange a private channel. Do not include technical details in that issue.

Please include privately, when available:

- the affected revision and component;
- the expected and observed behavior;
- minimal reproduction steps or a proof of concept;
- the likely impact and any known exposure;
- suggested mitigations, if known.

Maintainers will handle reports on a best-effort basis. As a volunteer project, AstroCareer Observatory does not promise a fixed response or remediation time. Reporters will be credited when appropriate and when they consent, after a fix or coordinated disclosure.

## Scope

Relevant reports include, but are not limited to:

- SSRF, DNS rebinding, redirect, or host-allowlist bypasses in collectors;
- credential, cookie, token, or private configuration exposure;
- arbitrary file access, unsafe deserialization, injection, or database corruption;
- malicious source content crossing a trust boundary;
- unauthorized publication of applicant or maintainer personal data;
- vulnerable dependencies, CI workflows, or release artifacts;
- ways to bypass the source-review and collection-safety controls.

Ordinary parsing errors, stale records, source classification disagreements, and feature requests are not security vulnerabilities unless they create a confidentiality, integrity, or availability risk. Report those through the normal issue tracker without including sensitive personal data.

## Data safety

This repository is for public, source-supported market observations. Do not submit real applicants' names, contact details, application histories, immigration documents, credentials, or other private career records. Personal profiles and notes belong in a separate private storage layer and must not be committed to this repository.

Never test a suspected vulnerability against a third-party service without authorization. Use local fixtures and the smallest non-destructive proof necessary.
