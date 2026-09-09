#!/usr/bin/env python3
"""Read-only Phase 4 smoke test using a Webmin session cookie."""

import argparse
import getpass
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar


def request(opener, url, data=None):
    return opener.open(url, data=data, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True,
                        help='Webmin base URL, for example https://server:19193')
    parser.add_argument('--user', default='kms-api')
    parser.add_argument('--add-address',
                        help='Explicitly add one safe test IPv4/CIDR address')
    parser.add_argument('--insecure', action='store_true',
                        help='Allow an untrusted TLS certificate for development only')
    args = parser.parse_args()

    password = getpass.getpass('Webmin password: ')
    base_url = args.url.rstrip('/')
    context = ssl._create_unverified_context() if args.insecure else None
    cookies = CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies),
        urllib.request.HTTPSHandler(context=context),
    )

    # The initial request establishes Webmin's testing cookie in session mode.
    request(opener, base_url + '/session_login.cgi').read()
    form = urllib.parse.urlencode({
        'user': args.user,
        'pass': password,
        'page': '/kmsfirewall/api.cgi',
    }).encode('utf-8')
    request(opener, base_url + '/session_login.cgi', form).read()

    for action in ('status', 'list'):
        url = base_url + '/kmsfirewall/api.cgi?action=' + action
        try:
            with request(opener, url) as response:
                body = response.read().decode('utf-8')
                print(response.status, json.dumps(json.loads(body), sort_keys=True))
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf-8', errors='replace')
            print(error.code, body, file=sys.stderr)
            return 1

    if args.add_address:
        url = base_url + '/kmsfirewall/api.cgi?action=add'
        form = urllib.parse.urlencode({'address': args.add_address}).encode('utf-8')
        try:
            with request(opener, url, form) as response:
                body = response.read().decode('utf-8')
                print(response.status, json.dumps(json.loads(body), sort_keys=True))
        except urllib.error.HTTPError as error:
            body = error.read().decode('utf-8', errors='replace')
            print(error.code, body, file=sys.stderr)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
