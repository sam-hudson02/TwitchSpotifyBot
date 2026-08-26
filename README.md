# TwitchSpotifyBot

TwitchSpotifyBot is a self-hosted Spotify song-request bot for Twitch, with optional Discord integration for posting the live queue and a channel song-request leaderboard.

A full list of commands can be found [here](https://github.com/sam-hudson02/TwitchSpotifyBot/blob/main/Commands.md).

## Features

- **Chat song requests**: viewers request songs by name or Spotify link with `!sr`, and the track is added straight to your Spotify queue.
- **Rating & leaderboard**: viewers rate the requester of the current song (`!rate` / `!like`), with per-user stats (`!stats`), a top-requester leaderboard (`!leader`), and optional automatic weekly or monthly resets.
- **Veto voting**: chat can vote to skip the current song (`!veto`); a configurable number of votes skips it.
- **Request permissions**: limit requests to everyone, followers, subscribers, or privileged users (subs/VIPs/mods), toggled live by moderators.
- **Moderation**: ban or timeout users from requesting, mod/unmod users, and clear the queue.
- **Live-aware**: only takes requests while the channel is live.
- **Discord integration (optional)**: posts a live-updating queue and leaderboard to Discord through webhooks.

## Prerequisites

- A Spotify Premium account
- A [Spotify](https://developer.spotify.com/dashboard/login) app for its client ID and secret ([guide](https://medium.com/@maxtingle/getting-started-with-spotifys-api-spotipy-197c3dc6353b)). In the app's settings, add a redirect URI. Spotify requires a loopback IP or HTTPS — plain `localhost` is [no longer accepted](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri):
  - **Local machine:** add `http://127.0.0.1:5000/callback`, and open the bot at `http://127.0.0.1:5000` (use the IP, not `localhost`).
  - **Remote host (e.g. a Raspberry Pi on your LAN):** Spotify requires HTTPS for non-loopback addresses. Either put the bot behind an HTTPS reverse proxy / tunnel (Caddy, Cloudflare Tunnel, Tailscale…) and register that `https://…/callback` URL, or do the one-time Spotify login on your local machine at `http://127.0.0.1:5000` and copy the generated `secret/.cache-<spotify-username>` file over to the host — the bot refreshes the token automatically from then on.
- A Twitch account for the bot to post as (your own account works fine)
- Twitch OAuth credentials (a client id, an access token and a refresh token) for that account, with the scopes `chat:read`, `chat:edit`, `user:read:chat` and `moderator:read:followers`. Recommended to use [this twitchtokengenerator.com link](https://twitchtokengenerator.com/?scope=chat:read+chat:edit+user:read:chat+moderator:read:followers), which pre-fills the required scopes: click **Custom Scope Token**, then scroll to the bottom and click **Generate Token** to authorize.

### Optional

- A Discord [webhook URL](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks) for the channel where you want the queue and/or leaderboard posted. You can use one webhook for the queue and another for the leaderboard.

## Credentials

However you run the bot, it reads its configuration from `./secret/conf.env`. A template lives at [`examples/conf.env.example`](examples/conf.env.example).

The file looks like this:

```env
SPOTIFY_CLIENT_ID=your spotify client id
SPOTIFY_SECRET=your spotify secret
SPOTIFY_USERNAME=your spotify username
TWITCH_CLIENT_ID=your twitch app client id
TWITCH_ACCESS_TOKEN=your twitch access token
TWITCH_REFRESH_TOKEN=your twitch refresh token
TWITCH_CLIENT_SECRET=          # only for confidential apps; blank for a public client
TWITCH_CHANNEL=the channel the bot joins
TWITCH_BOT_NAME=the twitch account the bot posts as

# Optional Discord integration (webhook URLs)
DISCORD_QUEUE_WEBHOOK=
DISCORD_LEADERBOARD_WEBHOOK=
```

`TWITCH_CHANNEL` is the channel the bot listens in; `TWITCH_BOT_NAME` is the account it speaks as (often the same account). Leave the Discord lines blank if you don't want Discord integration.


## Configuring commands

Every command's keyword(s) and response messages are configurable. On first run the bot writes `data/commands.yml` (under the mounted `./data` folder when running in Docker); edit it and restart to apply changes. Each entry looks like:

```yaml
SONG_REQUEST:
  keywords: [sr, songrequest]   # chat triggers, used as !sr / !songrequest
  enabled: true                 # set false to disable the command
  messages:
    added: "{song} by {artist} has been added to the queue!"
    not_found: "Sorry, I could not find that song!"
```

- `keywords` — one or more aliases (chat prefixes them with `!`).
- `enabled` — set `false` to turn a command off.
- `messages` — response templates. `{placeholders}` such as `{song}`, `{artist}`, `{user}`, `{requester}` and `{votes}` are filled in by the bot; unknown placeholders are left as-is.

Anything you leave out falls back to the defaults, so you only need to include the commands and messages you want to change. The full default set is in [`src/utils/default_commands.yml`](src/utils/default_commands.yml).

## Running with Docker (recommended)

1. Create a deployment directory:

   ```bash
   mkdir -p sbotify/secret sbotify/data && cd sbotify
   ```
  
2. Fill out credentials (see above).

3. Add a `docker-compose.yml` — it only needs the published image and two mounts:

   ```yaml
   services:
     sbotify:
       image: samhudson02/sbotify:latest
       container_name: sbotify
       restart: unless-stopped
       ports:
         - "5000:5000"
       volumes:
         - ./secret:/Sbotify/secret   # conf.env and the cached Spotify token
         - ./data:/Sbotify/data       # sqlite database, logs and settings.json
   ```

4. Start it, then visit `http://<host>:5000` and log in to Spotify. Once authenticated the bot connects to Twitch and starts taking requests.

   ```bash
   docker compose up -d
   ```

5. Mod the bot in Twitch chat (if running the bot as a different account)

## Running locally

The project uses [uv](https://docs.astral.sh/uv/). With uv installed:

```bash
uv sync                 # create the venv and install dependencies (Python 3.14)
uv run prisma generate  # generate the Prisma client (needs Node.js on PATH)
uv run prisma db push   # create ./data/db.sqlite3 from the schema
uv run python src/server.py
```

Then open `http://localhost:5000` and log in to Spotify.

`prisma generate` shells out to the Node-based Prisma CLI, so you need Node.js available when running locally. The Docker image installs it for you.
