# Commands

Commands are prefixed with `!` by default. The prefix is configurable through
the `PREFIX` key in `data/commands.yml`, which takes a list, so more than one
prefix can be active at once.

Every keyword below is also configurable: each command in `data/commands.yml`
has its own `keywords` list and an `enabled` flag, so commands can be renamed,
given aliases or turned off. The names here are the defaults.

## Everyone

`!sr`, `!song`, `!next`, `!rm`, `!like` and `!veto` only work while song requests are turned on and the channel is live. Who can use `!sr` depends on the current permission setting (see the moderator commands below); moderators and the broadcaster can always request, whatever the mode.

| Command       | Description                                                                        | Example                                                                              |
| ------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `!sr`         | Add a song to the queue by name or Spotify link.                                   | `!sr Africa TOTO` / `!sr https://open.spotify.com/track/2374M0fQpWi3dLnB54qaLX`       |
| `!song`       | Show the current song's name, artist and requester.                                | `!song`                                                                               |
| `!next`       | Show the next song in the queue.                                                    | `!next`                                                                               |
| `!rm`         | Remove your most recent request from the queue.                                    | `!rm`                                                                                 |
| `!like`       | Like the current song, crediting the user who requested it. Once per song, and not your own request. | `!like`                                                          |
| `!veto`       | Vote to skip the current song; it's skipped once enough chatters vote.             | `!veto`                                                                               |
| `!stats`      | Show your leaderboard position, rates received, requests made and rates given.     | `!stats`                                                                              |
| `!leader`     | Show the user with the most rates.                                                 | `!leader`                                                                             |
| `!sr-status`  | Show whether song requests are on/off and who is allowed to request.               | `!sr-status`                                                                          |
| `!help`       | Link to this command list.                                                         | `!help`                                                                               |

`!stats`, `!leader`, `!sr-status` and `!help` work whether or not the channel is live.

## Moderators

Everything below needs the broadcaster, a Twitch moderator of the channel, or a bot admin. Twitch mod status is read from the chatter's badge, so modding someone in your channel is enough; there is no separate bot-side mod role.

### Requests and moderation

| Command            | Description                                                          | Example           |
| ------------------ | -------------------------------------------------------------------- | ----------------- |
| `!skip`            | Skip the current song.                                               | `!skip`           |
| `!ban`             | Ban a user from making song requests (bot admins can't be banned).   | `!ban @user`      |
| `!unban`           | Unban a user from making song requests.                              | `!unban @user`    |
| `!all`             | Open song requests to everyone.                                      | `!all`            |
| `!followers-only`  | Restrict song requests to followers.                                 | `!followers-only` |
| `!subs-only`       | Restrict song requests to subscribers.                               | `!subs-only`      |
| `!priv-only`       | Restrict song requests to privileged users (DJs, subs, VIPs, mods).  | `!priv-only`      |
| `!djs-only`        | Restrict song requests to DJs.                                       | `!djs-only`       |

### Bot settings

| Command       | Description                                                        | Example         |
| ------------- | ----------------------------------------------------------------- | --------------- |
| `!sr-on`      | Turn song requests on.                                            | `!sr-on`        |
| `!sr-off`     | Turn song requests off.                                           | `!sr-off`       |
| `!sr-dj`      | Give a user the DJ role.                                          | `!sr-dj @user`  |
| `!sr-undj`    | Remove a user's DJ role.                                          | `!sr-undj @user` |
| `!set-veto`   | Set the number of votes needed to veto a song (minimum 2).       | `!set-veto 5`   |
| `!sr-reset`   | Reset the leaderboard (clears everyone's rates and requests).    | `!sr-reset`     |
| `!clear`      | Clear the song-request queue.                                    | `!clear`        |
| `!dev-on`     | Turn on dev mode (treats the channel as live, for testing).     | `!dev-on`       |
| `!dev-off`    | Turn off dev mode.                                               | `!dev-off`      |

## Roles

The bot tracks two roles of its own, both stored per user in its database:

- **DJ**: a song-request privilege only. DJs count as privileged under `!priv-only` and are the only chatters who can request under `!djs-only`. Granted with `!sr-dj`, or through `PUT /users/{username}/dj` on the API.
- **Admin**: treated as a moderator by the bot even without a Twitch mod badge, and cannot be banned with `!ban`. The broadcaster is made an admin when the bot starts; there is no chat command to grant it.

Twitch's own roles still matter: `!followers-only` and `!subs-only` check the chatter's follow and subscription status, and `!priv-only` accepts subscribers, VIPs and Twitch moderators alongside DJs.
