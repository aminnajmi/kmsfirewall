# KMS Firewall Webmin module

`kmsfirewall` is a narrowly scoped Webmin module intended to manage only the
KMS whitelist in a later phase. Laravel must not receive root Webmin or SSH
credentials, and this module never exposes a generic command, file, RPC, or
nftables endpoint.

## Implemented scope: Phase 4

The module has a status-only GUI and one read-only health endpoint:

```text
GET /kmsfirewall/api.cgi
GET /kmsfirewall/api.cgi?action=status
GET /kmsfirewall/api.cgi?action=list
```

`list` is read-only. It executes only the fixed argument-list command
equivalent to `nft -j list set inet KMS-Firewall kms_whitelist`, parses its JSON
with `JSON::PP`, and returns only validated IPv4 addresses or CIDRs. The HTTP
request cannot select an executable, command, table, family, set, or argument.
No nftables state, firewall configuration, chains, or rules are modified.

`add`, `remove`, `delete`, IP checking, and all other write operations remain
unimplemented. There are no API keys, Bearer tokens, generic commands, or RPC
endpoints.

## Authentication and authorization architecture

There are two independent layers:

1. Webmin/miniserv authenticates the HTTP request. With `session=1`, an
   unauthenticated request is rejected by Webmin before `api.cgi` runs. This
   module does not alter `miniserv.conf`, session handling, or global Webmin
   authentication.
2. After `init_config` has accepted the request, `auth-lib.pl` authorizes the
   Webmin identity. Webmin's documented `$remote_user` is compared exactly to
   `api_authorized_user` (default `kms-api`), and the module detailed ACL
   `api_access` must be enabled.

`init_config` also performs Webmin's first-level module ACL check. Webmin
therefore blocks a logged-in user who lacks the `kmsfirewall` module before
module code can emit JSON. A logged-in user who has module access but is not
the configured API user, or has `api_access` disabled, receives this JSON
response from the module:

```json
{"success":false,"error":{"code":"FORBIDDEN","message":"KMS Firewall API access denied"}}
```

## Important Webmin 2.660 API-only limitation

Do **not** enable Webmin's per-user RPC/API-only option for `kms-api`. Webmin
2.650 introduced the option, and subsequent Webmin releases explicitly note
that RPC-only accounts block browser/module access before module ACL checks.
That prevents this custom CGI endpoint from running. More importantly, Webmin
documents that RPC clients can execute commands and access arbitrary files as
root regardless of normal ACL restrictions. This module is intentionally not
an RPC service.

With `session=1`, Laravel needs a restricted Webmin login/session established
programmatically; no browser is required, but a Webmin session is. The native
RPC/API-only mechanism is not a safe substitute for this custom CGI. Do not
weaken `session=1` or grant RPC access to work around this limitation.

## Create the dedicated `kms-api` user

As a Webmin administrator:

1. Open **Webmin → Webmin Users** and choose **Create a new Webmin user**.
2. Set **Username** to `kms-api`; use a unique, high-entropy password stored
   only in Laravel's secret manager. Do not use `root` or `admin`.
3. Under **Available Webmin modules**, select only **KMS Firewall Whitelist**.
   Do not select Webmin Users, Command Shell, File Manager, Custom Commands,
   or any other module.
4. Leave the per-user **RPC/API-only** setting disabled. In **Global ACL**,
   set **Can accept RPC calls?** to **No**.
5. Save the user. Next to `kms-api`, click **KMS Firewall Whitelist** and set
   **Allow access to the KMS Firewall API?** to **Yes**. Set **Can edit module
   configuration?** to **No**.
6. Confirm the module configuration value `api_authorized_user=kms-api`.
   Changing that value is an administrator-only deployment action; it is never
   accepted from an HTTP request.

Do not give Laravel any administrator, root, SSH, or unrestricted RPC
credential. Rotate the `kms-api` password through Webmin and Laravel's secret
manager according to your operational policy.

## Install and deploy

From the project parent directory on the server, run as root:

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

## Tests

Run syntax checks on the Alpine target:

```sh
perl -c /data/webmin/kmsfirewall/acl_security.pl
perl -I/data/webmin -c /data/webmin/kmsfirewall/kmsfirewall-lib.pl
perl -I/data/webmin -c /data/webmin/kmsfirewall/auth-lib.pl
perl -I/data/webmin -c /data/webmin/kmsfirewall/api.cgi
```

On Alpine systems whose curl does not support a cookie jar, run the included
standard-library Python smoke test after deployment. It prompts for the
restricted Webmin password rather than accepting it on the command line:

```sh
python3 /data/webmin/kmsfirewall/tests/phase4_api_test.py --url 'https://SERVER:19193'

# Development only, for an untrusted TLS certificate:
python3 /data/webmin/kmsfirewall/tests/phase4_api_test.py --url 'https://SERVER:19193' --insecure
```

The script performs authenticated `status` and `list` GET requests only. Test
invalid actions, POST, unauthenticated access, and a second module-authorized
but non-API user using your existing Webmin-session test harness; their expected
HTTP statuses remain 404, 405, Webmin-controlled denial, and 403 respectively.

Success response:

```json
{"success":true,"module":"kmsfirewall","version":"1.0","status":"ok"}
```

An empty whitelist response is:

```json
{"success":true,"module":"kmsfirewall","version":"1.0","action":"list","addresses":[]}
```

If nftables is unavailable, fails, emits invalid JSON, or returns an unexpected
set structure or element type, the API returns a sanitized HTTP 500 JSON error.
It never returns raw nftables output or command errors.

The dedicated-user security test is successful only if `kms-api` cannot open
unrelated Webmin modules, cannot accept RPC calls, and cannot use this module
for commands, file access, configuration changes, or any action beyond status.
Verify this after every Webmin ACL or module upgrade.

A user with no `kmsfirewall` module access is rejected by Webmin before this
CGI starts. That response is controlled by Webmin rather than this module and
may not be JSON; this is an unavoidable consequence of using documented
`init_config` module ACL enforcement.

## Future phases

Future phases may add validated IPv4 operations only after explicit approval.
No write support or persistence integration is implemented in Phase 4.
