# Changelog

## Unreleased — Phase 2

- Added the Phase 2 GET-only JSON health endpoint at `api.cgi`.
- Added JSON-only responses for invalid actions, invalid parameters, and
  unsupported HTTP methods.
- Confirmed Phase 2 performs no nftables or other system operations.

## 1.0 - 2026-09-09

- Added the Phase 1 installable Webmin module skeleton.
- Added a status-only Webmin page with no nftables operations.
- Added fixed default configuration for the intended nftables table and set.
- Documented installation, testing, security boundaries, and future
  persistence requirements.
