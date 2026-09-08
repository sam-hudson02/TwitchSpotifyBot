import unittest

from server.routes.ws import token_from_subprotocols


class TestWsToken(unittest.TestCase):
    def test_bearer_pair_returns_token(self):
        self.assertEqual(token_from_subprotocols(['bearer', 'tok']), 'tok')

    def test_missing_or_malformed_returns_none(self):
        self.assertIsNone(token_from_subprotocols([]))
        self.assertIsNone(token_from_subprotocols(['tok']))
        self.assertIsNone(token_from_subprotocols(['other', 'tok']))


if __name__ == '__main__':
    unittest.main()
