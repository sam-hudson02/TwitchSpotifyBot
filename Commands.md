| Command | Description | Example |
| --- | ---| --- |
| `!sr`   | Adds a song to the spotify queue with song name or link. | '!sr Africa TOTO' / '!sr https://open.spotify.com/track/2374M0fQpWi3dLnB54qaLX?si=5b6f3814ab6f455a' |
| `!song` | Shows the name, artist and requester of the current song.                         | '!song' |
| `!rate` / `!like` | Adds rate / like to the user that requested the current song. | '!rate' / '!like' |
| `!veto` | Used to vote to skip the current song. | '!veto' |
| `!stats` | Shows your place in the leaderboard and number of rates you've recieved. | '!stats' |
| `!leader` | Shows user with the most rates / likes. | '!leader' |
| `!sp-status` | Shows the current status (on/off) of song requests. | '!sp-status' |
| `!skip` | Skips the current song. | '!skip'
| `!sp-timeout` | (mod only) Bans user from making song requests for specified period.  seconds (s), minutes (m), hours (h) and days(d) are all valid units. | '!sp-timeout @user 5m' |
| `!sp-ban` | (mod only) Bans user from making song requests. | '!sp-ban @user' |
| `!sp-unban` | (mod only) Unbans user from making song requests. | '!sp-unban @user' |
| `!sp-mod` | (admin only) Mods a user. | '!sp-mod @user |
| `!sp-unmod` | (admin only) Unmods a user. | '!sp-unmod @user |
| `!sp-set-veto-pass` | (admin only) Sets veto pass number. | '!sp-set-veto-pass 5' |
| `!sp-lb-reset` | (admin only) Sets automatic reset period of leaderboard. 'weekly', 'monthly' or 'off' are valid inputs. | '!sp-lb-reset weekly'
| `!sp-dev-on` | (admin only) Turns dev mode on. |  '!sp-dev-on' |
| `!sp-dev-on` | (admin only) Turns dev mode off. |  '!sp-dev-off' |
| `!sp-random` | (admin only / dev mode only) Adds specified number of random songs to queue. | '!sp-random  5' |
