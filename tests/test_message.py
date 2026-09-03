import unittest
from types import SimpleNamespace

from twitch.message import Message


def make(raw: str) -> Message:
    # Chatter only touches the api lazily (is_follower), so a stub is enough
    return Message(raw, SimpleNamespace(api=None))


class TestMessageParsing(unittest.TestCase):
    def test_emotes_tag_with_colons(self):
        # the emotes tag value contains ':' which used to truncate the tag
        # block and drop `id`, raising KeyError('id')
        raw = ("@badge-info=;badges=broadcaster/1;display-name=Sam;"
               "emotes=25:0-4,6-10/1902:12-16;id=abc-123;mod=0;room-id=42;"
               "subscriber=0;tmi-sent-ts=1685411550601;user-id=7;user-type= "
               ":sam!sam@sam.tmi.twitch.tv PRIVMSG #chan :Kappa Kappa hello")
        msg = make(raw)
        self.assertEqual(msg.id, 'abc-123')
        self.assertEqual(msg.room_id, '42')
        self.assertEqual(msg.content, 'Kappa Kappa hello')
        self.assertEqual(msg.chatter.name, 'Sam')

    def test_colon_in_message_body(self):
        raw = ("@id=x;room-id=1;tmi-sent-ts=1;display-name=A;badges=;emotes=;"
               "user-id=2;user-type= :a!a@a.tmi.twitch.tv PRIVMSG #chan "
               ":check https://open.spotify.com/track/abc")
        msg = make(raw)
        self.assertEqual(msg.content,
                         'check https://open.spotify.com/track/abc')

    def test_plain_message(self):
        raw = ("@id=y;room-id=1;tmi-sent-ts=1;display-name=B;badges=;emotes=;"
               "user-id=3;user-type= :b!b@b.tmi.twitch.tv PRIVMSG #chan :hi")
        msg = make(raw)
        self.assertEqual(msg.id, 'y')
        self.assertEqual(msg.content, 'hi')


if __name__ == '__main__':
    unittest.main()
