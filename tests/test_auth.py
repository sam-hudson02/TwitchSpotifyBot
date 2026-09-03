import unittest
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from server.auth import check_token
from server.deps import require_auth


def state_with(token):
    return SimpleNamespace(creds=SimpleNamespace(server_token=token))


def bearer(token):
    return HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)


class TestAuth(unittest.TestCase):
    def test_check_token(self):
        self.assertTrue(check_token('abc', 'abc'))
        self.assertFalse(check_token('abc', 'abd'))
        self.assertFalse(check_token(None, 'abc'))
        self.assertFalse(check_token('abc', None))
        self.assertFalse(check_token('abc', ''))

    def test_require_auth_valid(self):
        self.assertIsNone(
            require_auth(state=state_with('secret'),
                         credentials=bearer('secret')))

    def test_require_auth_bad_token(self):
        with self.assertRaises(HTTPException) as cm:
            require_auth(state=state_with('secret'), credentials=bearer('nope'))
        self.assertEqual(cm.exception.status_code, 403)

    def test_require_auth_missing_credentials(self):
        with self.assertRaises(HTTPException) as cm:
            require_auth(state=state_with('secret'), credentials=None)
        self.assertEqual(cm.exception.status_code, 401)

    def test_require_auth_not_configured(self):
        with self.assertRaises(HTTPException) as cm:
            require_auth(state=state_with(None), credentials=bearer('x'))
        self.assertEqual(cm.exception.status_code, 503)


if __name__ == '__main__':
    unittest.main()
