# KMS Firewall Whitelist

A dedicated Webmin module for safely exposing a controlled KMS firewall whitelist API.

## Architecture

```text
Laravel Panel
     │
     │ HTTPS / Webmin Session
     ▼
Webmin
     │
     ▼
KMS Firewall Whitelist Module
     │
     ▼
nftables
     │
     ▼
inet KMS-Firewall
     └── kms_whitelist
```

## Current Status

### Phase 1 — Basic Webmin Module

Implemented:

- Webmin module structure
- Module information
- Basic module page
- Configuration files
- Module ACL structure
- Documentation

### Phase 2 — Read-only API

Implemented:

- `api.cgi`
- GET-only API
- `status` action
- JSON responses
- HTTP method validation
- Query parameter validation
- No firewall modification
- No shell execution
- No nftables execution

Example:

```text
GET /kmsfirewall/api.cgi?action=status
```

Successful response:

```json
{
    "success": true,
    "module": "kmsfirewall",
    "version": "1.0",
    "status": "ok"
}
```

### Phase 3 — Webmin Authentication and ACL

Implemented:

- Webmin session authentication
- Dedicated `kms-api` Webmin user
- First-level Webmin module ACL
- Module-level `api_access` ACL
- API authorization
- No bearer tokens
- No generic Webmin RPC
- No shell execution
- No nftables modification

The API is restricted to the dedicated Webmin user:

```text
kms-api
```

The Webmin ACL must contain:

```text
kms-api: kmsfirewall
```

## Security Model

The API does not implement its own username/password authentication.

Authentication is delegated to Webmin.

```text
Client
  │
  ▼
Webmin Session Authentication
  │
  ▼
kms-api
  │
  ▼
Webmin Module ACL
  │
  ▼
Module API ACL
  │
  ▼
api.cgi
```

### Dedicated API User

The recommended Webmin user is:

```text
Username: kms-api
```

The account should:

- Have a strong unique password
- Have access only to the `kmsfirewall` module
- Have API access enabled
- Not have configuration editing permissions
- Not have unrestricted Webmin access
- Not have generic Webmin RPC access

## Webmin ACL

The first-level module ACL is stored in:

```text
/data/webmin/config/webmin.acl
```

The required entry is:

```text
kms-api: kmsfirewall
```

This grants the `kms-api` account access to the KMS Firewall Whitelist module.

This ACL is separate from the module-specific ACL.

## Module ACL

The module-specific ACL is implemented by:

```text
acl_security.pl
```

The current module-level permission is:

```text
api_access
```

The intended configuration for the API user is:

```text
api_access = 1
```

Configuration editing should remain disabled for the API user.

## Installation

### 1. Install dependencies

On Alpine Linux:

```bash
apk update && apk add git perl curl
```

### 2. Clone the repository

```bash
cd /tmp
rm -rf kmsfirewall
git clone https://github.com/aminnajmi/kmsfirewall.git kmsfirewall
```

### 3. Deploy the module

```bash
cp -a /tmp/kmsfirewall/. /data/webmin/kmsfirewall/
```

### 4. Set ownership

```bash
chown -R root:root /data/webmin/kmsfirewall
```

### 5. Set permissions

```bash
chmod 0600 /data/webmin/kmsfirewall/config
chmod 0755 /data/webmin/kmsfirewall/index.cgi
chmod 0755 /data/webmin/kmsfirewall/api.cgi
```

### 6. Clear Webmin module cache

```bash
rm -f /data/webmin/config/module.infos.cache
```

## Perl Syntax Verification

Run:

```bash
perl -c /data/webmin/kmsfirewall/acl_security.pl
```

```bash
perl -I/data/webmin -c /data/webmin/kmsfirewall/kmsfirewall-lib.pl
```

```bash
perl -I/data/webmin -c /data/webmin/kmsfirewall/auth-lib.pl
```

```bash
perl -I/data/webmin -c /data/webmin/kmsfirewall/api.cgi
```

All files should return:

```text
syntax OK
```

## Configure the Webmin User

Create the user:

```text
kms-api
```

Then grant the user access to:

```text
KMS Firewall Whitelist
```

Enable:

```text
API access
```

Disable:

```text
Configuration editing
```

Do not enable generic Webmin RPC.

## Configure First-Level Module Access

Check:

```bash
grep '^kms-api:' /data/webmin/config/webmin.acl
```

Required result:

```text
kms-api: kmsfirewall
```

If the entry is empty:

```bash
sed -i 's/^kms-api:.*/kms-api: kmsfirewall/' /data/webmin/config/webmin.acl
```

Then clear the module cache:

```bash
rm -f /data/webmin/config/module.infos.cache
```

Verify again:

```bash
grep '^kms-api:' /data/webmin/config/webmin.acl
```

## API

### Status

Endpoint:

```text
/kmsfirewall/api.cgi?action=status
```

Method:

```text
GET
```

Successful response:

```json
{
    "success": true,
    "module": "kmsfirewall",
    "version": "1.0",
    "status": "ok"
}
```

The exact JSON key order is not guaranteed.

## HTTP Behavior

### Successful request

```text
GET /kmsfirewall/api.cgi?action=status
```

Returns:

```text
HTTP 200
Content-Type: application/json; charset=UTF-8
```

### Unsupported action

Example:

```text
GET /kmsfirewall/api.cgi?action=test
```

Returns:

```text
HTTP 404
```

With:

```json
{
    "success": false,
    "error": {
        "code": "INVALID_ACTION",
        "message": "Unsupported API action"
    }
}
```

### POST request

The API is currently GET-only.

Example:

```text
POST /kmsfirewall/api.cgi
```

Returns:

```text
HTTP 405
```

With:

```json
{
    "success": false,
    "error": {
        "code": "METHOD_NOT_ALLOWED",
        "message": "HTTP method not allowed"
    }
}
```

### Unsupported query parameter

Unsupported parameters return:

```text
HTTP 400
```

With:

```json
{
    "success": false,
    "error": {
        "code": "INVALID_PARAMETER",
        "message": "Unsupported query parameter"
    }
}
```

## Testing

The Alpine `curl` build may not provide cookie support.

For testing Webmin session authentication, Python's standard library can be used.

Example:

```bash
python3 test.py
```

The test should authenticate as:

```text
kms-api
```

and then request:

```text
/kmsfirewall/api.cgi?action=status
```

Expected result:

```text
API HTTP: 200
Content-Type: application/json; charset=UTF-8

API Response:
{"version":"1.0","module":"kmsfirewall","status":"ok","success":true}
```

## Webmin Installation Location

This project assumes the custom Webmin installation is:

```text
/data/webmin
```

Webmin configuration:

```text
/data/webmin/config
```

Module:

```text
/data/webmin/kmsfirewall
```

Webmin MiniServ configuration:

```text
/data/webmin/config/miniserv.conf
```

## Webmin Port

The current Webmin installation uses:

```text
19193
```

Example:

```text
http://SERVER_IP:19193/
```

## Starting Webmin

For the current custom installation:

```bash
/usr/bin/perl /data/webmin/miniserv.pl /data/webmin/config/miniserv.conf
```

Verify:

```bash
ps aux | grep '[m]iniserv.pl'
```

Check the listening port:

```bash
ss -lntp | grep ':19193'
```

Test locally:

```bash
curl -k -I http://127.0.0.1:19193/
```

## File Structure

```text
kmsfirewall/
├── module.info
├── config.info
├── config
├── defaultacl
├── acl_security.pl
├── auth-lib.pl
├── kmsfirewall-lib.pl
├── index.cgi
├── api.cgi
├── lang/
│   └── en
├── README.md
└── CHANGELOG.md
```

## Important Security Restrictions

The Phase 3 implementation intentionally does NOT:

- Execute arbitrary shell commands
- Execute arbitrary Perl commands
- Execute arbitrary nftables commands
- Accept arbitrary nftables rules
- Modify arbitrary firewall tables
- Modify arbitrary firewall chains
- Modify arbitrary firewall sets
- Provide generic Webmin RPC
- Accept bearer tokens
- Store API passwords
- Provide unrestricted Webmin access
- Allow arbitrary module access

The current API only provides:

```text
status
```

and does not modify the firewall.

## Firewall Integration

The intended firewall structure is:

```text
inet KMS-Firewall
```

with the whitelist set:

```text
kms_whitelist
```

The intended KMS port is:

```text
1688/tcp
```

The intended firewall logic is:

```text
source IP ∈ kms_whitelist
        │
        ├── YES → ACCEPT TCP/1688
        │
        └── NO  → DROP TCP/1688
```

Firewall modification is intentionally outside the current Phase 3 implementation.

## Future Development

Planned next phase:

### Phase 4 — Read-only nftables integration

The API will first gain the ability to safely read:

```text
inet KMS-Firewall
└── kms_whitelist
```

No firewall changes should be performed until the read-only implementation has been tested.

Future phases may introduce controlled operations such as:

```text
list
add
remove
```

Any write operation should:

1. Validate the requested IP/CIDR
2. Restrict operations to `kms_whitelist`
3. Avoid arbitrary nftables input
4. Validate the existing firewall structure
5. Apply only the intended change
6. Verify the resulting state
7. Return structured JSON
8. Log the operation where appropriate

## Version

Current module version:

```text
1.0
```

Current development phase:

```text
Phase 3
```

Current API:

```text
status
```

Current firewall modification:

```text
Disabled
```
