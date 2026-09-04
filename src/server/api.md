# Sbotify server API

FastAPI app (`server.app:app`), served by uvicorn on port 5000. Interactive docs
at `/docs`, schema at `/openapi.json`.

Twitch and Discord run independently: either can be started or stopped without
affecting the other. Spotify is the auth gate for the Twitch bot only (the audio
controller needs a Spotify session); Discord does not depend on it.

## Authentication

Mutating endpoints (POST) require a bearer token; read-only endpoints (GET) are
open. Send the token configured as `SERVER_API_TOKEN`:

```
Authorization: Bearer <SERVER_API_TOKEN>
```

- `401` if the header is missing.
- `403` if the token is wrong.
- `503` if the server has no `SERVER_API_TOKEN` configured. It fails closed: the
  route is refused rather than left open.

### CORS

For a browser dashboard on a different origin, set `SERVER_CORS_ORIGINS` to a
comma-separated list of allowed origins. Left unset, any origin is allowed
(mutations are still guarded by the token, so this is safe). CORS covers the
HTTP routes; the WebSocket is guarded by its `?token=` query param instead.

---

## Spotify auth

### GET /

Entry point. If Spotify is not yet connected, redirects (302) to the Spotify
authorization page. If it is connected, starts the Twitch bot and returns
`200 "Bot is running"`. Returns `503` if Spotify could not be initialised.

### GET /callback

Spotify OAuth redirect target. Exchanges the code, verifies the token, then
starts the Twitch bot.

- `200 "Bot is running"` on success.
- `400` if the token could not be verified.
- `503` if Spotify is unavailable.

---

## Status

### GET /spotify/status

```json
{ "connected": true, "working": true, "user": "spotify-username" }
```

```typescript
type SpotifyStatus = {
  connected: boolean;   // a cached token was accepted at startup
  working: boolean;     // a live API call just succeeded
  user: string;
};
```

### GET /twitch/status

```json
{
  "running": true,
  "channel": "channelname",
  "bot_name": "botname",
  "live": false,
  "active": true
}
```

When the bot is stopped, only `running` and `channel` are populated; the rest are
`null`.

```typescript
type TwitchStatus = {
  running: boolean;
  channel: string;
  bot_name: string | null;
  live: boolean | null;    // is the channel live (bot's tracked state)
  active: boolean | null;  // are song requests enabled
};
```

### GET /discord/status

```json
{ "connected": true, "queue_webhook": true, "leaderboard_webhook": false }
```

```typescript
type DiscordStatus = {
  connected: boolean;            // the hook is running
  queue_webhook: boolean;        // a queue webhook is configured
  leaderboard_webhook: boolean;  // a leaderboard webhook is configured
};
```

---

## Control (POST)

Each returns a `ControlResponse`:

```typescript
type ControlResponse = {
  service: 'twitch' | 'discord';
  running: boolean;
  message: string;   // "started" | "stopped" | "already running" | "not running"
};
```

### POST /twitch/start

Starts the Twitch bot.

- `200 ControlResponse` on success (or if already running).
- `409` if Spotify is not connected (authorize Spotify first).
- `502` if the bot failed to start (e.g. bad token, upstream/web error).

### POST /twitch/stop

Stops the Twitch bot. Always `200 ControlResponse` (`running: false`).

### PUT /twitch/active

Enables or disables song requests, keeping the audio context in step (the same
toggle as the `!sr-on` / `!sr-off` chat commands). Body `{ "active": bool }`,
returns `{ "active": bool }`.

### POST /discord/start

Starts the Discord hook.

- `200 ControlResponse` on success (or if already running).
- `409` if no Discord webhooks are configured.
- `502` if the hook failed to start.

### POST /discord/stop

Stops the Discord hook. Always `200 ControlResponse` (`running: false`).

---

## Setup and settings

### GET /setup

One call a dashboard can render a setup screen from. Reports which pieces are
configured and whether Spotify is connected, without ever returning secret
values.

```json
{
  "channel": "channelname",
  "twitch_configured": true,
  "spotify_configured": true,
  "spotify_connected": true,
  "discord_queue_webhook": true,
  "discord_leaderboard_webhook": false,
  "server_token_set": true
}
```

To connect Spotify, open `GET /` (it redirects to the Spotify authorization
page, then back through `GET /callback`).

### GET /settings

The runtime settings.

```json
{ "active": true, "dev_mode": false, "sr_permission": "all", "veto_pass": 5 }
```

```typescript
type Settings = {
  active: boolean;      // are song requests enabled
  dev_mode: boolean;
  sr_permission: 'all' | 'subs' | 'followers' | 'privileged' | 'djs';
  veto_pass: number;    // votes needed to veto (minimum 2)
};
```

### PUT /settings

Updates any subset of the settings; omitted fields are left unchanged. Body is a
partial `Settings`. Returns the full `Settings` after the change.

- `200 Settings` on success.
- `400` if a value is invalid (e.g. `veto_pass` below 2, or an unknown
  `sr_permission`).

---

## Playback

### GET /now-playing

The bot's current playback context. The Twitch bot's update loop keeps this
fresh while it runs; the values are last-known when it is stopped.

```json
{
  "track": "song title",
  "artist": "artist name",
  "requester": "username",
  "album_art": "https://...",
  "progress": 42000,
  "duration": 210000,
  "paused": false,
  "playing_queue": true,
  "live": true
}
```

```typescript
type NowPlaying = {
  track: string | null;
  artist: string | null;
  requester: string | null;   // null for playlist songs or before it resolves
  album_art: string | null;
  progress: number | null;    // milliseconds
  duration: number | null;    // milliseconds
  paused: boolean;
  playing_queue: boolean;     // playing a requested song rather than the playlist
  live: boolean;
};
```

### POST /skip

Skips the current song, playing the next queued one if there is one. Goes
through the bot's audio controller, so the Twitch bot must be running.

- `200 ControlResponse` (`service: "playback"`, `message: "skipped"`).
- `409` if the Twitch bot is not running.

---

## Data

### GET /queue

Current song-request queue, ordered by position.

```json
[
  {
    "id": 12,
    "position": 1.0,
    "name": "song title",
    "artist": "artist name",
    "requester": "username",
    "url": "https://open.spotify.com/track/..."
  }
]
```

```typescript
type QueueItem = {
  id: number;
  position: number;   // fractional rank; lower plays sooner
  name: string;
  artist: string;
  requester: string;
  url: string;
};
```

The three mutations below are the REST counterpart of the WebSocket editor.
Each is protected, broadcasts the new queue to any WebSocket clients, and
returns the updated queue as `QueueItem[]`.

### POST /queue

Adds a song by search term or Spotify link, credited to the broadcaster. Goes
through the bot's audio controller, so the Twitch bot must be running. Body:

```json
{ "query": "never gonna give you up" }
```

- `200 QueueItem[]` (the new queue).
- `409` if the Twitch bot is not running, or the song is already queued.
- `404` if no matching song was found.
- `400` for a YouTube link or any non-Spotify link.

### PUT /queue/{id}

Moves a queue entry, using the same fractional-position rule as the WebSocket
`move`. Body `{ "after": <id> | null }`; `after: null` moves it to the front.

- `200 QueueItem[]`.
- `404` if the entry (or the `after` target) does not exist.

### DELETE /queue/{id}

Removes one entry. `200 QueueItem[]`.

### DELETE /queue

Clears the queue. `200 QueueItem[]` (empty).

### GET /leaderboard

Users ordered by rates received, descending.

```json
[
  { "position": 1, "username": "user", "rates": 5, "requests": 12 }
]
```

```typescript
type LeaderboardEntry = {
  position: number;
  username: string;
  rates: number;
  requests: number;
};
```

---

## Users

Every route here requires the bearer token, including the `GET`. Unlike the
public queue and leaderboard, this exposes ban and role flags, so it is treated
as admin data. Each returns the updated (or listed) user.

```typescript
type User = {
  username: string;
  ban: boolean;
  dj: boolean;
  admin: boolean;
  requests: number;
  rates: number;
};
```

### GET /users

Lists all known users with their roles and ban state. `200 User[]`.

### PUT /users/{username}/ban and /unban

Bans or unbans a user (a banned user cannot request songs). The user row is
created first if it does not exist yet. `200 User`.

### PUT /users/{username}/dj and /undj

Grants or revokes the dj role (used by the "DJs only" request mode). `200 User`.

## WebSocket for live queue editing

### WS /ws/queue

Protected. Browsers can't set headers on a WebSocket, so pass the token as a
query param: `ws://host:5000/ws/queue?token=<SERVER_API_TOKEN>`. A missing/wrong
token (or none configured) closes the socket with code `1008`.

On connect, and after every change (including songs the Twitch bot adds, picked
up by a 2s poll while clients are connected), the server pushes the full queue:

```json
{ "queue": [ { "id": 12, "position": 1.0, "name": "...", "artist": "...",
              "requester": "...", "url": "..." } ] }
```

Client -> server commands (JSON):

```typescript
type QueueCommand =
  | { op: 'move'; id: number; after: number | null }  // after=null -> front
  | { op: 'remove'; id: number }
  | { op: 'clear' };
```

`move` assigns a fractional position between the new neighbours (single-row
update, no renumbering). A bad command is answered on that socket with
`{ "error": "..." }` and does not drop the connection.

## Static

`GET /static/*` serves the files under `src/static/` (e.g. `/static/style.css`).
