# Contributing

Contributions must preserve ccm-console’s tenant isolation, payload-blind evidence
boundary, deterministic tests, and explicit separation of technical coordination from
authorization, audit, certification, retention, and remediation execution.

Do not add cloud collectors, credentials, raw evidence payloads, source attachments,
identity-provider secrets, a production database, automatic escalation, background
workers, browser-side authorization decisions, unbounded list APIs, or cross-tenant
queries. Do not represent a workbench update as a casework approval, exception decision,
closure verification, or risk acceptance.

Run `make fixtures quality package-check` before a pull request. Include backend and
frontend tests for authorization-sensitive changes, regenerate public artifacts where
applicable, and never commit `.env` values, PostgreSQL URLs, real tokens, customer data,
or screenshots of sensitive evidence.
