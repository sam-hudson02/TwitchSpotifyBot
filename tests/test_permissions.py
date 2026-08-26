import unittest
from utils.twitch_utils import check_permission, is_privileged
from utils.settings import Perms
from utils.errors import BadPerms


class FakeChatter:
    def __init__(self, broadcaster=False, sub=False, vip=False, mod=False,
                 follower=False):
        self.is_broadcaster = broadcaster
        self._sub = sub
        self._vip = vip
        self._mod = mod
        self._follower = follower

    async def is_subscriber(self):
        return self._sub

    async def is_vip(self):
        return self._vip

    async def is_mod(self):
        return self._mod

    async def is_follower(self):
        return self._follower


class FakeUser:
    def __init__(self, mod=False, admin=False):
        self.mod = mod
        self.admin = admin


class FakeSettings:
    def __init__(self, permission):
        self.permission = permission


class TestCheckPermission(unittest.IsolatedAsyncioTestCase):
    async def check(self, perm, chatter, user):
        await check_permission(FakeSettings(perm), chatter, user)

    async def test_broadcaster_bypasses(self):
        await self.check(Perms.SUBS, FakeChatter(broadcaster=True), FakeUser())

    async def test_subs_only_blocks_non_sub(self):
        with self.assertRaises(BadPerms):
            await self.check(Perms.SUBS, FakeChatter(sub=False), FakeUser())

    async def test_subs_only_allows_sub(self):
        await self.check(Perms.SUBS, FakeChatter(sub=True), FakeUser())

    async def test_followers_only_blocks_non_follower(self):
        with self.assertRaises(BadPerms):
            await self.check(Perms.FOLLOWERS, FakeChatter(follower=False),
                             FakeUser())

    async def test_followers_only_allows_follower(self):
        await self.check(Perms.FOLLOWERS, FakeChatter(follower=True),
                         FakeUser())

    async def test_privileged_blocks_regular(self):
        with self.assertRaises(BadPerms):
            await self.check(Perms.PRIVILEGED, FakeChatter(), FakeUser())

    async def test_privileged_allows_vip(self):
        await self.check(Perms.PRIVILEGED, FakeChatter(vip=True), FakeUser())

    async def test_privileged_allows_db_mod(self):
        await self.check(Perms.PRIVILEGED, FakeChatter(), FakeUser(mod=True))

    async def test_all_allows_everyone(self):
        await self.check(Perms.ALL, FakeChatter(), FakeUser())


class TestIsPrivileged(unittest.IsolatedAsyncioTestCase):
    async def test_db_admin(self):
        self.assertTrue(await is_privileged(FakeChatter(), FakeUser(admin=True)))

    async def test_vip(self):
        self.assertTrue(await is_privileged(FakeChatter(vip=True), FakeUser()))

    async def test_regular_denied(self):
        self.assertFalse(await is_privileged(FakeChatter(), FakeUser()))


if __name__ == '__main__':
    unittest.main()
