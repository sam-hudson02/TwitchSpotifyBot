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

### POST /discord/start

Starts the Discord hook.

- `200 ControlResponse` on success (or if already running).
- `409` if no Discord webhooks are configured.
- `502` if the hook failed to start.

### POST /discord/stop

Stops the Discord hook. Always `200 ControlResponse` (`running: false`).

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
