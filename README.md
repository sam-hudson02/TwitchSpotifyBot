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
- A [Spotify](https://developer.spotify.com/dashboard/login) app for its client ID and secret ([guide](https://medium.com/@maxtingle/getting-started-with-spotifys-api-spotipy-197c3dc6353b)). In the app's settings, add a redirect URI:
  - Running with Docker or the web server: `http://<host>:5000/callback` (e.g. `http://192.168.1.10:5000/callback`, or `http://localhost:5000/callback` when testing on the same machine).
- A Twitch account for the bot to post as (your own account works fine)
- Twitch OAuth credentials for that account. Recommended to use [twitchtokengenerator.com](https://twitchtokengenerator.com/): select the **Bot Chat Token** option and authorize, which gives you a **client id**, an **access token** and a **refresh token** with the `chat:read`/`chat:edit` scopes the bot needs. 

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
