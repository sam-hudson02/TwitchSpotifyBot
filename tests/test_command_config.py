import os
import tempfile
import unittest
from utils.command_config import CommandConfig


class TestCommandConfig(unittest.TestCase):
    def _config(self, user_yaml=None):
        fd, path = tempfile.mkstemp(suffix='.yml')
        os.close(fd)
        if user_yaml is None:
            os.remove(path)
        else:
            with open(path, 'w') as f:
                f.write(user_yaml)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        return CommandConfig(path=path)

    def test_defaults_keywords_and_enabled(self):
        cfg = self._config()
        self.assertEqual(cfg.keywords('SONG_REQUEST'), ['sr'])
        self.assertTrue(cfg.enabled('SONG_REQUEST'))

    def test_message_formatting(self):
        cfg = self._config()
        self.assertEqual(
            cfg.message('SONG_REQUEST', 'added', song='x', artist='y'),
            'x by y has been added to the queue!')

    def test_missing_placeholder_left_literal(self):
        cfg = self._config()
        self.assertEqual(
            cfg.message('SONG_REQUEST', 'added', song='x'),
            'x by {artist} has been added to the queue!')

    def test_unknown_message_key_returns_empty(self):
        cfg = self._config()
        self.assertEqual(cfg.message('SONG_REQUEST', 'nope'), '')

    def test_on_off_keys_are_strings(self):
        # guards against PyYAML parsing unquoted on/off as booleans
        cfg = self._config()
        self.assertEqual(cfg.message('DEV_ON', 'on'),
                         'Dev mode has been turned on!')

    def test_user_override_keywords_and_message(self):
        user = ('SONG_REQUEST:\n'
                '  keywords: [sr, songrequest]\n'
                '  messages:\n'
                '    added: "added {song}"\n')
        cfg = self._config(user)
        self.assertEqual(cfg.keywords('SONG_REQUEST'), ['sr', 'songrequest'])
        self.assertEqual(
            cfg.message('SONG_REQUEST', 'added', song='x', artist='y'),
            'added x')
        # unspecified message falls back to the default
        self.assertEqual(cfg.message('SONG_REQUEST', 'not_found'),
                         'Sorry, I could not find that song!')

    def test_misspelled_placeholder_stays_literal(self):
        cfg = self._config('SONG_REQUEST:\n'
                           '  messages:\n'
                           '    added: "{sng} by {artist} added"\n')
        self.assertEqual(
            cfg.message('SONG_REQUEST', 'added', song='x', artist='y'),
            '{sng} by y added')

    def test_malformed_template_falls_back_to_default(self):
        cfg = self._config('SONG_REQUEST:\n'
                           '  messages:\n'
                           '    added: "{song by {artist}"\n')
        self.assertEqual(
            cfg.message('SONG_REQUEST', 'added', song='x', artist='y'),
            'x by y has been added to the queue!')

    def test_disabled_command(self):
        cfg = self._config('SONG_REQUEST:\n  enabled: false\n')
        self.assertFalse(cfg.enabled('SONG_REQUEST'))
        self.assertEqual(cfg.keywords('SONG_REQUEST'), ['sr'])

    def test_creates_file_when_missing(self):
        fd, path = tempfile.mkstemp(suffix='.yml')
        os.close(fd)
        os.remove(path)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        CommandConfig(path=path)
        self.assertTrue(os.path.exists(path))


if __name__ == '__main__':
    unittest.main()
