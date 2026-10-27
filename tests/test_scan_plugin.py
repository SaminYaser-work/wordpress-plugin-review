import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SKILL_DIR = Path(__file__).resolve().parents[1]
SCANNER = SKILL_DIR / 'scripts' / 'scan_plugin.py'
spec = importlib.util.spec_from_file_location('scan_plugin', SCANNER)
scan = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = scan
spec.loader.exec_module(scan)

FIXTURE = {
    'demo-plugin.php': """<?php
/*
Plugin Name: Demo Plugin
Text Domain: wrong-domain
*/
if (!defined('ABSPATH')) exit;
function demo_is_pro_feature() { return false; }
include ABSPATH . 'wp-admin/includes/plugin-install.php';
register_rest_route('demo/v1', '/private', array('methods'=>'GET', 'permission_callback'=>'__return_true', 'callback'=>'demo_private'));
register_rest_route('demo/v1', '/missing', array('methods'=>'POST', 'callback'=>'demo_save'));
$raw = wp_unslash($_POST['builder_data']);
$decoded = json_decode($raw, true);
echo $decoded['title'];
if ( ! current_user_can( 'manage_options' ) ) { return; }
activate_plugin('woocommerce/woocommerce.php');
$uploads = wp_upload_dir();
$pdf_filename = $uploads['basedir'] . '/invoice-123.pdf';
// Review note: do not flag the raw input.
""",
    'readme.txt': """=== Demo Plugin ===
Description: Free cart and shipping rules.
""",
    'assets/js/demo-admin.js': """fetch('https://inside.examplehost.test/api/analytics');
const lib = 'https://cdn.jsdelivr.net/npm/driver.js@latest/dist/driver.js.iife.js';
const message = __('Premium service', 'wrong-domain');
const review = '440+ Trustpilot Reviews';
""",
    'assets/css/demo-admin.css': """:root { --demo: 1; }
img { max-width: 100%; }
""",
    'includes/class-db.php': """<?php
$sql = 'CREATE TABLE IF NOT EXISTS demo_records (id bigint(20))';
dbDelta($sql);
""",
    'templates/checkout.php': """<?php
echo $order_total;
""",
    'vendor/tmp/sample with space .json': '{}',
    'vendor/bin/build-phar.sh': '#!/bin/sh\necho hi\n',
}

class TestScanner(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.src = self.root / 'demo-plugin'
        self.src.mkdir()
        for name, text in FIXTURE.items():
            p = self.src / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding='utf-8')
        self.zippath = self.root / 'demo-plugin.zip'
        with zipfile.ZipFile(self.zippath, 'w') as z:
            for name in FIXTURE:
                z.write(self.src / name, arcname='demo-plugin/' + name)

    def test_directory_and_zip_find_equivalent_flags(self):
        d, errs, r = scan.read_files(self.src)
        z, zerrs, ziproot = scan.read_files(self.zippath)
        self.assertEqual(ziproot, 'demo-plugin')
        self.assertEqual(set(d), set(z))
        a, urls, meta, readme = scan.review(d, 'demo-plugin')
        b, urls2, meta2, readme2 = scan.review(z, 'demo-plugin')
        self.assertEqual([(i.check, i.path, i.line) for i in a], [(i.check, i.path, i.line) for i in b])
        codes = {h.check for h in a}
        for expected in ['TRIALWARE_GATE','REMOTE_ASSET','OUTBOUND_TELEMETRY',
                         'REST_PUBLIC','REST_MISSING_PERMISSION','UNDISCLOSED_SERVICE','I18N_MISMATCH',
                         'CORE_INCLUDE','PLUGIN_ACTIVATION','DBDELTA_INVALID',
                         'PDF_PUBLIC','DIRECT_PHP','FILENAME_PORTABILITY',
                         'PACKAGING_FILE','CSS_GLOBAL','REVIEWER_COMMENT',
                         'RATING_BRANDING','ECHO_UNESCAPED','INPUT_TO_SINK']:
            self.assertIn(expected, codes, f'Missing code {expected}')
        self.assertIn('inside.examplehost.test', urls)
        self.assertIn('demo-plugin.php', meta['main_plugin'])
        self.assertTrue(readme)
        self.assertEqual(urls, urls2)

    def test_cli_writes_markdown_and_json(self):
        out = self.root / 'review.md'
        inv = self.root / 'hits.json'
        run = subprocess.run([sys.executable, str(SCANNER), str(self.zippath), '--slug', 'demo-plugin', '--out', str(out), '--json', str(inv)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        md = out.read_text(encoding='utf-8')
        self.assertIn('Preliminary static triage only', md)
        self.assertIn('Suggested fix if confirmed:', md)
        self.assertIn('SVN commits, trunk/tags', md)
        self.assertIn('demo-plugin.php', md)
        self.assertGreater(len(json.loads(inv.read_text())['hits']), 10)

    def test_zip_traversal_name_ignored(self):
        zip2 = self.root / 'traversal.zip'
        with zipfile.ZipFile(zip2, 'w') as z:
            z.writestr('../bad.php', 'bad')
            z.writestr('safe.php', '<?php /* Plugin Name: Safe */')
        files, skipped, _ = scan.read_files(zip2)
        self.assertNotIn('../bad.php', files)
        self.assertTrue(any('Unsafe ZIP' in s for s in skipped))

if __name__ == '__main__':
    unittest.main()
