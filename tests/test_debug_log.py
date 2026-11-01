import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'debug_log.py'


class TestDebugLog(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'debug.log'
        self.state = self.root / 'state.json'
        self.out = self.root / 'delta.json'

    def run_cli(self, action, *extra, expected=0):
        args = [sys.executable, str(SCRIPT), action, str(self.log),
                '--state', str(self.state)]
        if action == 'delta':
            args += ['--out', str(self.out)]
        result = subprocess.run(args + list(extra), capture_output=True, text=True)
        self.assertEqual(result.returncode, expected, result.stderr)
        return result

    def read_delta(self, *extra):
        result = self.run_cli('delta', *extra)
        return json.loads(self.out.read_text()), result

    def test_only_appended_entries_and_stack_trace_are_captured(self):
        self.log.write_text('old unrelated warning\n')
        self.run_cli('baseline')
        state_before = self.state.read_bytes()
        with self.log.open('a') as handle:
            handle.write('PHP Fatal error: private-token\nStack trace:\n#0 plugin.php(42)\n')
        report, result = self.read_delta()
        self.assertEqual(report['status'], 'appended')
        self.assertTrue(report['boundary_preserved'])
        self.assertFalse(report['truncated'])
        self.assertEqual(report['text'], 'PHP Fatal error: private-token\nStack trace:\n#0 plugin.php(42)\n')
        self.assertNotIn('private-token', result.stdout)
        self.assertEqual(self.state.read_bytes(), state_before)
        self.assertIn('old unrelated warning', self.log.read_text())

    def test_missing_log_then_creation_is_captured(self):
        self.run_cli('baseline')
        missing, _ = self.read_delta()
        self.assertEqual(missing['status'], 'missing')
        self.log.write_text('activation warning\n')
        report, _ = self.read_delta()
        self.assertEqual(report['status'], 'created')
        self.assertEqual(report['text'], 'activation warning\n')

    def test_unchanged_log_produces_no_historical_entries(self):
        self.log.write_text('old warning\n')
        self.run_cli('baseline')
        report, _ = self.read_delta()
        self.assertEqual(report['status'], 'unchanged')
        self.assertEqual(report['text'], '')

    def test_rotation_and_same_inode_rewrite_invalidate_boundary(self):
        for rotation in (False, True):
            with self.subTest(rotation=rotation):
                self.log.write_text('old warning\n')
                self.run_cli('baseline')
                if rotation:
                    self.log.rename(self.root / 'rotated.log')
                self.log.write_text('new warning after rewrite, longer than baseline\n')
                report, _ = self.read_delta()
                self.assertEqual(report['status'], 'replaced_or_rewritten')
                self.assertFalse(report['boundary_preserved'])
                self.assertIn('new warning', report['text'])

    def test_deleted_log_is_not_reported_as_clean(self):
        self.log.write_text('old warning\n')
        self.run_cli('baseline')
        self.log.unlink()
        report, _ = self.read_delta()
        self.assertEqual(report['status'], 'removed')
        self.assertFalse(report['boundary_preserved'])

    def test_capture_limit_is_explicit_and_utf8_is_supported(self):
        self.run_cli('baseline')
        self.log.write_text('warning café\nsecond line\n')
        report, _ = self.read_delta('--max-bytes', '14')
        self.assertTrue(report['truncated'])
        self.assertEqual(report['captured_bytes'], 14)
        self.assertGreater(report['remaining_bytes'], 0)
        self.assertEqual(report['text'], 'warning café\n')

    def test_state_cannot_be_used_with_another_log(self):
        self.run_cli('baseline')
        self.log = self.root / 'other.log'
        self.run_cli('delta', expected=2)
        self.assertFalse(self.out.exists())

    def test_artifacts_cannot_overwrite_log_or_state(self):
        self.log.write_text('preserve this\n')
        self.run_cli('baseline', '--state', str(self.log), expected=2)
        self.assertEqual(self.log.read_text(), 'preserve this\n')
        self.run_cli('baseline')
        state_before = self.state.read_bytes()
        for target in (self.log, self.state):
            self.run_cli('delta', '--out', str(target), expected=2)
        self.assertEqual(self.log.read_text(), 'preserve this\n')
        self.assertEqual(self.state.read_bytes(), state_before)

    def test_invalid_state_or_unreadable_log_is_an_error(self):
        for content in ('not json', '{}', '{"version": 999}'):
            with self.subTest(content=content):
                self.state.write_text(content)
                self.run_cli('delta', expected=2)
        self.log.mkdir()
        self.run_cli('baseline', expected=2)


if __name__ == '__main__':
    unittest.main()
