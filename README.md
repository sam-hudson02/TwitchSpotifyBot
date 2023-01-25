# TwitchSpotifyBot

TwitchSpotifyBot is a self hosted spotify song request bot for twitch with discord integration, like command and channel sr leaderboard.

A full list of commands can be found [here](https://github.com/sam-hudson02/TwitchSpotifyBot/blob/main/Commands.md).

# Installation

## Prerequisites

- A spotify premium account
- [Spotify](https://developer.spotify.com/dashboard/login) client id and secret keys ([Guide](https://medium.com/@maxtingle/getting-started-with-spotifys-api-spotipy-197c3dc6353b))
  - **If you're running locally make sure to set your redirect url to "https://open.spotify.com/"**
  - **If you're running from docker make sure to set your redirect url to the address of the host, followed by /spotify-redirect.** e.g. (http://192.168.1.1:5000/spotify-redirect)
- A twitch account for the bot (can be your regular twitch account)
- A twitch api token (you can generate a token [here](https://twitchtokengenerator.com/))
- python3 installed on your system if you plan to run the bots locally

### Optional

- A [discord](https://discord.com/developers/applications) bot application ([Guide](https://youtu.be/b61kcgfOm_4?t=35))

## Docker installation

- Pull the docker image using:

```bash
docker pull samhudson02/sbotify:latest
```

- Or if you're running on a raspberry pi, use:

```bash
docker pull samhudson02/sbotify:latest-arm
```

- Example compose file:

```yaml
version: "3.9"

services:
  sbotify:
    image: samhudson02/sbotify
    restart: always
    ports:
      - "5000:5000"
    volumes:
      - /path/to/your/file:/Sbotify/data
    environment:
      - SPOTIFY_CLIENT_ID=Your spotify client ID here
      - SPOTIFY_SECRET=Your spotify secret here
      - SPOTIFY_USERNAME=Your spotify username here
      - TWITCH_TOKEN=Your twitch token here
      - TWITCH_CHANNEL=Your twitch channel here
      - DISCORD_TOKEN=Optional discord token here
      - DISCORD_LEADERBOARD_CHANNEL_ID=Optional leaderboard ID here
      - DISCORD_QUEUE_CHANNEL_ID=Optional queue ID here
```

- Go to your host address and you should be redirected to login to spotify

## Local installation

- Install dependencies using:

```
pip install -r requirements.txt
```

- Create folder called 'secret' in 'TwitchSpotifyBot' directory
- In the 'secret' folder create a file called 'conf.env'
- Open conf.env and enter the following information:

```
SPOTIFY_CLIENT_ID="YOUR SPOTIFY CLIENT ID HERE"
SPOTIFY_SECRET="YOUR SPOTIFY SECRET HERE"
SPOTIFY_USERNAME="YOUR SPOTIFY USERNAME HERE"
TWITCH_TOKEN="YOUR TWITCH TOKEN HERE"
TWITCH_CHANNEL="YOUR TWITCH CHANNEL HERE"
DISCORD_TOKEN="OPTIONAL DISCORD TOKEN HERE"
DISCORD_LEADERBOARD_CHANNEL_ID="OPTIONAL DISCORD LEADERBOARD CHANNEL ID HERE"
DISCORD_QUEUE_CHANNEL_ID="OPTIONAL DISCORD QUEUE CHANNEL ID HERE"
```

- Run src/main.py
- Follow instructions to authenticate spotify account
