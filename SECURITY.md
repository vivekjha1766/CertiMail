# Security Policy — CertiMail

## Overview & Threat Model

CertiMail is an operational automation platform engineered for event organizers to dispatch personalized certificate packages to participants. Because CertiMail processes recipient rosters, certificates, and SMTP credentials, security and data privacy are core architectural priorities.

CertiMail is designed as a **locally hosted tool (`127.0.0.1`)**, operating under a single-operator model. It is not intended to be exposed directly to the public internet without an authenticating reverse proxy.

---

## Security Architecture & Defenses

### 1. In-Memory Credential Security (Zero Database Persistence)
- **Zero Disk Persistence for Passwords**: SMTP passwords are kept strictly in-memory for the duration of the active backend session. They are **never** persisted to SQLite database tables, audit records, delivery logs, or browser `localStorage`.
- **Sensitive Data Scrubbing**: Delivery failure logs, exception traces, and CSV exports automatically redact passwords, tokens, and authorization parameters.
- **Environment Isolation**: Default credentials can optionally be loaded from a local `.env` file that is strictly ignored by version control.

### 2. File Upload & Archive Sandboxing (Zip Slip Protection)
- **Path Traversal Defense**: All archive decompression routines strictly validate candidate extract paths against canonical base extraction boundaries (`data/extracted/`). Any ZIP member containing `../`, absolute drive prefixes, or symlinks outside the destination boundary is rejected before disk write.
- **Resource Exhaustion Limits**: Hard size barriers are enforced on incoming uploads (default: 200 MB for ZIP archives, 50 MB for Excel spreadsheets) to prevent ZIP bomb vulnerabilities and memory exhaustion.

### 3. Safe Test Mode & Recipient Isolation
- **Recipient Address Override**: Test mode dispatches email payloads exclusively to a designated operator mailbox, ensuring participant email addresses are never contacted during preflight staging.
- **Idempotent Delivery Gate**: Prior to dispatching any message, the delivery engine checks the durable delivery ledger. Recipients with `SMTP_ACCEPTED` status can never be auto-resent, preventing accidental message duplicates.

### 4. Localhost Network Restriction
- The FastAPI backend binds by default strictly to loopback (`127.0.0.1:8000`), preventing incoming connections from external network interfaces.

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | Yes       |

---

## Reporting a Vulnerability

If you discover a security vulnerability or credential exposure risk in CertiMail:

1. **Do not** disclose the vulnerability publicly in open GitHub issues.
2. Please report the issue privately through [GitHub Security Advisories](https://github.com) or contact the project maintainer directly.
3. Include detailed steps to reproduce the issue, sample input payloads, and affected environment information.
4. Security reports will be acknowledged within 48 hours, and patches will be prepared in an isolated branch prior to release.
