#!/usr/bin/env python3
"""Build the theme without website overrides, then check security and feed/image behavior."""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

THEME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(THEME / 'scripts'))
from check_security import SecurityPage, audit_site

with tempfile.TemporaryDirectory() as output:
    subprocess.run([
        os.environ.get('HUGO_BIN', 'hugo'), '--source', str(THEME / 'tests/fixture'),
        '--themesDir', str(THEME.parent), '--theme', THEME.name,
        '--destination', output, '--minify', '--panicOnWarning',
    ], check=True)
    errors = audit_site(output, 'https://example.org')
    assert not errors, '\n'.join(errors)
    root = Path(output)
    feed = ET.parse(root / 'index.xml')
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    entries = feed.findall('a:entry', ns)
    assert not any(entry.findtext('a:title', namespaces=ns) == 'Hidden from feed' for entry in entries)
    entry = next(entry for entry in entries if 'quoted' in entry.findtext('a:title', namespaces=ns))
    assert ']]&gt;' in entry.findtext('a:content', namespaces=ns), 'Atom HTML content lost escaping'
    page = SecurityPage((root / 'posts/example/index.html').read_text())
    images = [attrs for tag, attrs in page.tags if tag == 'img']
    assert any(attrs.get('src', '').endswith('/posts/example/cover.webp') and attrs.get('width') == '16' for attrs in images)
    assert any(attrs.get('src', '').endswith('/posts/example/cover.png?download=1#pixel') for attrs in images)
    assert not any(tag == 'a' and attrs.get('target') == '_blank' and 'cover.webp' in attrs.get('href', '') for tag, attrs in page.tags)
    assert any(tag == 'details' and attrs.get('id') == 'toc' for tag, attrs in page.tags)
    print('Theme fixture passed: modern templates, escaping, Atom exclusions, local images, WebP and side ToC.')
