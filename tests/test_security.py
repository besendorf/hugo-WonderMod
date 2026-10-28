import base64
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_security import audit_site, parse_policy


class SecurityAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'app.js').write_text('console.log("local");')
        self.digest = base64.b64encode(hashlib.sha256((self.root / 'app.js').read_bytes()).digest()).decode()

    def audit(self, body, head='', **kwargs):
        (self.root / 'index.html').write_text(f'<html><head>{head}</head><body>{body}</body></html>')
        return audit_site(self.root, 'https://example.org', **kwargs)

    def test_local_scripts_and_non_executable_json_ld_are_allowed(self):
        self.assertEqual([], self.audit(f'<script src="/app.js" integrity="sha256-{self.digest}"></script><script type="application/ld+json">{{"name":"&lt;script&gt;"}}</script>'))

    def test_inline_code_and_styles_are_rejected(self):
        for html in ('<script>alert(1)</script>', '<img src="/app.js" onerror="alert(1)">', '<style>body{}</style>', '<p style="color:red">text</p>', '<a href="java&#10;script:alert(1)">link</a>', '<iframe srcdoc="hi"></iframe>'):
            with self.subTest(html=html):
                self.assertTrue(self.audit(html))

    def test_external_and_missing_resources_are_rejected(self):
        for html in ('<script src="https://evil.example/a.js"></script>', '<img src="//evil.example/a.png">', '<link rel="preconnect" href="https://evil.example">', '<img srcset="/app.js 1x, https://evil.example/a.png 2x">', '<script src="/missing.js"></script>'):
            with self.subTest(html=html):
                self.assertTrue(self.audit(html))

    def test_missing_or_wrong_integrity_is_rejected(self):
        for integrity in ('', ' integrity="sha256-wrong"'):
            self.assertTrue(self.audit(f'<script src="/app.js"{integrity}></script>'))

    def test_invalid_json_ld_is_rejected(self):
        self.assertTrue(self.audit('<script type="application/ld+json">{bad}</script>'))

    def test_css_can_not_import_external_resources(self):
        for css in ('@import "https://evil.example/style.css";', 'a{background:url(//evil.example/x.png)}', 'a{background:url(data:image/svg+xml,bad)}'):
            (self.root / 'style.css').write_text(css)
            with self.subTest(css=css):
                self.assertTrue(self.audit(''))

    def test_required_policy_is_early_and_exact(self):
        policy = parse_policy("default-src 'none'; script-src 'self'")
        meta = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'">'
        script = f'<script src="/app.js" integrity="sha256-{self.digest}"></script>'
        self.assertEqual([], self.audit(script, head=meta, required_policy=policy))
        self.assertTrue(self.audit('', required_policy=policy))
        self.assertTrue(self.audit('', head=script + meta, required_policy=policy))
        self.assertTrue(self.audit('', head=meta.replace("'self'", "'unsafe-inline'"), required_policy=policy))

    def test_duplicate_policy_directives_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_policy("script-src 'self'; script-src *")


if __name__ == '__main__':
    unittest.main()
