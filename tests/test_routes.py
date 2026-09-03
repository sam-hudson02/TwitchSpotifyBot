import unittest
from types import SimpleNamespace

from fastapi.testclient import TestClient

import server.app as A
from server.deps import get_state
from server.state import AppState
from utils.logger import Log
from utils.errors import SettingsError
from mocks.mock_services import (mock_services, mock_creds, MockQueueDB,
                                 queue_row, MockTwitchBot)

AUTH = {'Authorization': 'Bearer secret'}


class FakeSettings:
    def __init__(self):
        self._active = True
        self._dev = False
        self._perm = SimpleNamespace(value='all')
        self._veto = 5

    @property
    def active(self):
        return self._active

    @property
    def dev_mode(self):
        return self._dev

    @property
    def permission(self):
        return self._perm

    @property
    def veto_pass(self):
        return self._veto

    def set_active(self, a):
        self._active = a

    def set_dev_mode(self, d):
        self._dev = d

    def set_permission(self, p):
        self._perm = SimpleNamespace(value=p)

    def set_veto_pass(self, v):
        if v <= 1:
            raise SettingsError('Veto pass must be greater than 1.')
        self._veto = v


class TestRoutes(unittest.TestCase):
    def setUp(self):
        services = mock_services(creds=mock_creds(server_token='secret'),
                                 db=MockQueueDB([queue_row(1, 1.0)]))
        services.settings = FakeSettings()
        services.context = SimpleNamespace(active=True)
        self.state = AppState(log=Log('test'), services=services,
                              twitch_factory=MockTwitchBot,
                              discord_factory=MockTwitchBot)
        A.app.dependency_overrides[get_state] = lambda: self.state
        self.client = TestClient(A.app)  # no `with`: skip lifespan/startup

    def tearDown(self):
        A.app.dependency_overrides.clear()

    def test_setup_reports_config(self):
        body = self.client.get('/setup').json()
        self.assertEqual(body['channel'], 'chan')
        self.assertTrue(body['twitch_configured'])
        self.assertTrue(body['spotify_configured'])
        self.assertTrue(body['spotify_connected'])
        self.assertTrue(body['discord_queue_webhook'])
        self.assertFalse(body['discord_leaderboard_webhook'])
        self.assertTrue(body['server_token_set'])

    def test_get_settings(self):
        body = self.client.get('/settings').json()
        self.assertEqual(body, {'active': True, 'dev_mode': False,
                                'sr_permission': 'all', 'veto_pass': 5})

    def test_put_settings_partial(self):
        r = self.client.put('/settings',
                            json={'sr_permission': 'djs', 'veto_pass': 8},
                            headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['sr_permission'], 'djs')
        self.assertEqual(r.json()['veto_pass'], 8)
        self.assertTrue(r.json()['active'])  # untouched

    def test_put_settings_requires_auth(self):
        self.assertEqual(self.client.put('/settings',
                                        json={'active': False}).status_code, 401)

    def test_put_settings_validation_error(self):
        r = self.client.put('/settings', json={'veto_pass': 1}, headers=AUTH)
        self.assertEqual(r.status_code, 400)

    def test_put_twitch_active(self):
        r = self.client.put('/twitch/active', json={'active': False},
                            headers=AUTH)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['active'])
        self.assertFalse(self.state.services.context.active)


if __name__ == '__main__':
    unittest.main()
