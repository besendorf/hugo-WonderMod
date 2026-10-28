#!/usr/bin/env python3
"""Audit generated HTML/CSS for WonderMod's hardening contract (stdlib only)."""
import argparse
import base64
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


def parse_policy(value):
    policy = {}
    for part in value.split(';'):
        tokens = part.split()
        if tokens:
            if tokens[0] in policy:
                raise ValueError(f'duplicate CSP directive: {tokens[0]}')
            policy[tokens[0]] = tokens[1:]
    return policy


class SecurityPage(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.scripts = []
        self.current_script = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'script':
            self.current_script = [dict(attrs), '']
            self.scripts.append(self.current_script)

    def handle_data(self, text):
        if self.current_script is not None:
            self.current_script[1] += text

    def handle_endtag(self, tag):
        if tag == 'script':
            self.current_script = None


def audit_site(root, origin, required_policy=None):
    root = Path(root).resolve()
    expected_origin = urlsplit(origin)
    errors = []

    def fail(path, message):
        errors.append(f'{path.relative_to(root)}: {message}')

    def local_resource(path, value):
        url = urlsplit(urljoin(origin.rstrip('/') + '/', value))
        if (url.scheme, url.netloc) != (expected_origin.scheme, expected_origin.netloc):
            fail(path, f'external resource: {value}')
            return None
        target = (root / unquote(url.path).lstrip('/')).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            fail(path, f'missing local resource: {value}')
            return None
        return target

    def integrity(path, attrs, target):
        if target is None:
            return
        for token in (attrs.get('integrity') or '').split():
            algorithm, _, digest = token.partition('-')
            if algorithm in ('sha256', 'sha384', 'sha512'):
                actual = base64.b64encode(hashlib.new(algorithm, target.read_bytes()).digest()).decode()
                if digest == actual:
                    return
        fail(path, f'missing or incorrect integrity hash: {target.name}')

    pages = list(root.rglob('*.html'))
    if not pages:
        errors.append('No HTML pages found')
    for path in pages:
        page = SecurityPage(path.read_text())
        policies = []
        seen_resource = False
        for tag, attrs in page.tags:
            if tag == 'meta' and attrs.get('http-equiv', '').lower() == 'content-security-policy':
                if seen_resource:
                    fail(path, 'CSP appears after a resource')
                try:
                    policies.append(parse_policy(attrs.get('content', '')))
                except ValueError as error:
                    fail(path, str(error))
            if tag == 'style' or 'style' in attrs:
                fail(path, 'inline style')
            if any(name.startswith('on') for name in attrs):
                fail(path, 'inline event handler')
            if tag in ('base', 'object', 'embed', 'iframe') or 'srcdoc' in attrs:
                fail(path, f'forbidden active element: {tag}')
            for attr in ('href', 'src', 'xlink:href', 'action', 'formaction'):
                value = re.sub(r'[\x00-\x20]', '', attrs.get(attr) or '')
                if urlsplit(value).scheme.lower() in ('javascript', 'vbscript', 'data'):
                    fail(path, f'unsafe URL in {attr}')

            resources = []
            rel = set((attrs.get('rel') or '').split())
            if tag == 'link' and rel & {'stylesheet', 'preload', 'modulepreload', 'preconnect', 'dns-prefetch', 'icon', 'apple-touch-icon', 'mask-icon', 'manifest'}:
                resources.append(attrs.get('href'))
            if tag in ('script', 'img', 'audio', 'video', 'source', 'track', 'input'):
                resources.append(attrs.get('src'))
            if tag in ('image', 'use'):
                resources.extend((attrs.get('href'), attrs.get('xlink:href')))
            if tag == 'video':
                resources.append(attrs.get('poster'))
            if tag in ('img', 'source') and attrs.get('srcset'):
                resources.extend(item.strip().split()[0] for item in attrs['srcset'].split(',') if item.strip())
            for value in filter(None, resources):
                if value.startswith('#'):
                    continue
                seen_resource = True
                target = local_resource(path, urljoin('/' + str(path.relative_to(root)), value))
                if tag == 'script' or (tag == 'link' and 'stylesheet' in rel):
                    integrity(path, attrs, target)

        for attrs, source in page.scripts:
            if not attrs.get('src'):
                if attrs.get('type', '').lower() != 'application/ld+json':
                    fail(path, 'inline executable script')
                else:
                    try:
                        json.loads(source)
                    except ValueError:
                        fail(path, 'invalid JSON-LD')
            elif source.strip():
                fail(path, 'inline content in external script tag')
        if required_policy is not None and policies != [required_policy]:
            fail(path, 'missing or changed Content Security Policy')

    for path in root.rglob('*.css'):
        css = path.read_text()
        for match in re.finditer(r'url\(\s*[\'"]?([^\s\)\'\"]+)|@import\s+[\'"]([^\'"]+)', css, re.I):
            value = match.group(1) or match.group(2)
            if not value.startswith('#'):
                local_resource(path, urljoin('/' + str(path.relative_to(root)), value))
    return errors


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--origin', required=True)
    args = parser.parse_args()
    errors = audit_site(args.root, args.origin)
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Validated local resources, integrity hashes, JSON-LD and absence of inline code/styles.')
