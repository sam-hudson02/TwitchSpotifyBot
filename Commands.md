# Commands

All commands are prefixed with `!`.

## Everyone

The song-request commands (`!sr`, `!song`, `!next`, `!rm`, `!rate`, `!veto`) only work while song requests are turned on and the channel is live. Who can use `!sr` depends on the current permission setting (see the moderator commands below).

| Command       | Description                                                                        | Example                                                                              |
| ------------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `!sr`         | Add a song to the queue by name or Spotify link.                                   | `!sr Africa TOTO` / `!sr https://open.spotify.com/track/2374M0fQpWi3dLnB54qaLX`       |
| `!song`       | Show the current song's name, artist and requester.                                | `!song`                                                                               |
| `!next`       | Show the next song in the queue.                                                    | `!next`                                                                               |
| `!rm`         | Remove your most recent request from the queue.                                    | `!rm`                                                                                 |
| `!rate`       | Rate the user who requested the current song.                                      | `!rate`                                                                               |
| `!veto`       | Vote to skip the current song; it's skipped once enough chatters vote.             | `!veto`                                                                               |
| `!stats`      | Show your leaderboard position, rates received, requests made and rates given.     | `!stats`                                                                              |
| `!leader`     | Show the user with the most rates.                                                 | `!leader`                                                                             |
| `!sr-status`  | Show whether song requests are on/off and who is allowed to request.               | `!sr-status`                                                                          |
| `!help`       | Link to this command list.                                                         | `!help`                                                                               |

## Moderators

| Command            | Description                                                       | Example        |
| ------------------ | ---------------------------------------------------------------- | -------------- |
| `!skip`            | Skip the current song.                                           | `!skip`        |
| `!ban`             | Ban a user from making song requests.                            | `!ban @user`   |
| `!unban`           | Unban a user from making song requests.                          | `!unban @user` |
| `!all`             | Open song requests to everyone.                                  | `!all`         |
| `!followers-only`  | Restrict song requests to followers.                            | `!followers-only` |
| `!subs-only`       | Restrict song requests to subscribers.                          | `!subs-only`   |
| `!priv-only`       | Restrict song requests to privileged users (subs, VIPs, mods).  | `!priv-only`   |

## Admins

| Command       | Description                                                        | Example         |
| ------------- | ----------------------------------------------------------------- | --------------- |
| `!sr-on`      | Turn song requests on.                                            | `!sr-on`        |
| `!sr-off`     | Turn song requests off.                                           | `!sr-off`       |
| `!sr-mod`     | Give a user bot-mod permissions.                                 | `!sr-mod @user` |
| `!sr-unmod`   | Remove a user's bot-mod permissions.                            | `!sr-unmod @user` |
| `!set-veto`   | Set the number of votes needed to veto a song (minimum 2).       | `!set-veto 5`   |
| `!sr-reset`   | Reset the leaderboard (clears everyone's rates and requests).    | `!sr-reset`     |
| `!clear`      | Clear the song-request queue.                                    | `!clear`        |
| `!dev-on`     | Turn on dev mode (treats the channel as live, for testing).     | `!dev-on`       |
| `!dev-off`    | Turn off dev mode.                                               | `!dev-off`      |
