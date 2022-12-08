# TwitchSpotifyBot

Twitch Spotify Bot is a bot that listens to your twitch chat for song requests and automatically 
adds them to your spotify queue.

A full list of commands can be found [here](https://pastebin.com/vZ4bNiTn).

# Installation

## Prerequisites 

- A spotify premium account
- [Spotify](https://developer.spotify.com/dashboard/login) client id and secret keys ([Guide](https://medium.com/@maxtingle/getting-started-with-spotifys-api-spotipy-197c3dc6353b))
    - **Make sure to set your redirect url to "https://open.spotify.com/"**
- A twitch account for the bot (can be your regular twitch account)
- A twitch api token (you can generate a token [here](https://twitchtokengenerator.com/))
- python3 installed on your system if you plan to run the bots locally

### Optional

- A [discord](https://discord.com/developers/applications) bot application ([Guide](https://youtu.be/b61kcgfOm_4?t=35))

## Docker installation
- coming soon..

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


