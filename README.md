# KMS Firewall Webmin module

`kmsfirewall` is a dedicated Webmin module for managing the `kms_whitelist`
set in `inet KMS-Firewall`. It is intended to provide a narrow, authenticated
JSON API to a Laravel management panel; the panel will never be given shell or
SSH access for firewall administration.

## Phase 2 scope

This release implements the installable Webmin module shell, its status-only
GUI page, and a public, read-only JSON health endpoint. It does **not** call
`nft`, inspect the active ruleset, alter firewall state, authenticate API
requests, store an API key, or create audit records. The displayed target is
configuration only.

The deliberately fixed defaults are:

| Setting | Default |
| --- | --- |
| nftables family/table | `inet KMS-Firewall` |
| nftables set | `kms_whitelist` |
| API enabled | `1` |

No client-controlled request exists in this release, so no arbitrary table,
set, chain, rule, command, or path can be supplied.

## Install on Alpine/Webmin

Copy the module directory to the Webmin installation. Run as root on the
server:

```sh
install -d -m 0755 /data/webmin/kmsfirewall
cp -a ./kmsfirewall/. /data/webmin/kmsfirewall/
chown -R root:root /data/webmin/kmsfirewall
find /data/webmin/kmsfirewall -type d -exec chmod 0755 {} \;
find /data/webmin/kmsfirewall -type f -exec chmod 0644 {} \;
chmod 0600 /data/webmin/kmsfirewall/config
chmod 0755 /data/webmin/kmsfirewall/index.cgi
chmod 0755 /data/webmin/kmsfirewall/api.cgi
/data/webmin/restart
```

If this project is copied to the server first, run the commands from its
parent directory. No Perl modules or package installation are required.

Sign in to Webmin at `https://SERVER:19193/`, then open **Networking → KMS
Firewall Whitelist**. Module placement may vary if the Webmin theme or module
categories are customized.

## Web UI result

The status page identifies module version `1.0`, reports the configured
target as `inet KMS-Firewall / kms_whitelist`, reports whether `nft` is on
Webmin's PATH, and states that API configuration is enabled by default. It
does not prove that the table/set exists and does not alter nftables.

For a basic server-side syntax check:

```sh
perl -c /data/webmin/kmsfirewall/acl_security.pl
perl -I/data/webmin -c /data/webmin/kmsfirewall/kmsfirewall-lib.pl
perl -I/data/webmin -c /data/webmin/kmsfirewall/api.cgi
```

`index.cgi` needs Webmin's runtime environment and should be tested by opening
the module in Webmin rather than executing it directly in a shell.

## Phase 2 JSON health API

The only API endpoint in this release is `GET /kmsfirewall/api.cgi`. `action`
may be omitted or be exactly `status`. All other methods, actions, duplicate
parameters, malformed percent encodings, and parameters other than `action`
are rejected. Request bodies are never read or acted upon.

The endpoint is intentionally unauthenticated only until Phase 3. Do not
expose it to untrusted networks during this interim phase.

```sh
# Substitute Webmin credentials if the Webmin server requires login. This is
# Webmin's existing access control, not the Bearer-key authentication planned
# for Phase 3.

# 1. GET without an action: HTTP 200
curl -k -i --user 'WEBMIN_USER:WEBMIN_PASSWORD' "https://SERVER:19193/kmsfirewall/api.cgi"

# 2. GET status: HTTP 200
curl -k -i --user 'WEBMIN_USER:WEBMIN_PASSWORD' "https://SERVER:19193/kmsfirewall/api.cgi?action=status"

# 3. Unsupported action: HTTP 404
curl -k -i --user 'WEBMIN_USER:WEBMIN_PASSWORD' "https://SERVER:19193/kmsfirewall/api.cgi?action=list"

# 4. POST: HTTP 405
curl -k -i --user 'WEBMIN_USER:WEBMIN_PASSWORD' -X POST "https://SERVER:19193/kmsfirewall/api.cgi?action=status"

# 5. Unknown parameter: HTTP 400
curl -k -i --user 'WEBMIN_USER:WEBMIN_PASSWORD' "https://SERVER:19193/kmsfirewall/api.cgi?debug=1"

# 5. Malformed query encoding: HTTP 400
curl -k -i --user 'WEBMIN_USER:WEBMIN_PASSWORD' "https://SERVER:19193/kmsfirewall/api.cgi?action=%ZZ"
```

Successful requests return:

```json
{"success":true,"module":"kmsfirewall","version":"1.0","status":"ok"}
```

An unsupported action returns HTTP 404:

```json
{"success":false,"error":{"code":"INVALID_ACTION","message":"Unsupported API action"}}
```

The response header is `Content-Type: application/json; charset=UTF-8`; it
also disables content sniffing and caching. Webmin HTTP authentication may
still be required by the surrounding Webmin server configuration.

## Planned security model

Phase 3 will require `Authorization: Bearer <API_KEY>`, use a key stored
through module configuration, compare it in constant time, and never log or
return it. The only planned operations are status, list, check, add, and
remove for validated individual IPv4 addresses. There will be no generic shell
or nftables endpoint.

## Persistence

Live whitelist changes are intentionally not implemented in Phase 1. Before
any write support is added, the installed Webmin nftables module must be
inspected on the target system to determine its saved-rules representation and
apply workflow. The synchronization adapter will be isolated and documented;
no implementation will knowingly permit a subsequent Webmin Apply Changes to
discard whitelist entries.

## Laravel integration

Laravel may use the Phase 2 endpoint only as a connectivity health check. Do
not use it for firewall management until later phases, including authentication,
have been implemented and tested.

## Troubleshooting

If the module is absent, confirm `/data/webmin/kmsfirewall/module.info` is
readable by root and restart Webmin. If it opens but `nft` is not found, check
the PATH of the Webmin service; this is informational in Phase 1 only.
