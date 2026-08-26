import json
from utils import Log, Creds, init_dirs, Settings
import asyncio
import os
from spotipy.oauth2 import CacheFileHandler
from spotipy import Spotify, SpotifyOAuth
import flask
from flask import Flask, request
from main import start_twitch_bot, start_discord_hook
from AudioController.audio_controller import Context
import threading as th
from pathlib import Path

static_folder = str(Path(__file__).resolve().parent / 'static')
app = Flask(__name__)
bot_running_page = f'{static_folder}/bot_running.html'

app.static_folder = static_folder


class Server:
    def __init__(self):
        init_dirs()
        self.log = Log('server', file='./data/server.log')
        self.creds = Creds(self.log)
        self.user = self.creds.spotify.username
        self.cache_path = f'./secret/.cache-{self.user}'
        self.cache_handler = CacheFileHandler(cache_path=self.cache_path)
        self.spot_oath = None
        self.spotify_connected = self.validate_cache()
        self.settings = Settings()
        self.audio_context = Context()
        self.bot_running = False
        self.loop = asyncio.new_event_loop()
        if self.spotify_connected:
            self.start_bots()

    def validate_cache(self) -> bool:
        self.log.info('Validating cached Spotify token')
        if not os.path.exists(self.cache_path):
            self.log.info('No cached Spotify token found')
            return False
        with open(self.cache_path, 'r') as f:
            cache_data = json.load(f)
        

        if cache_data.get('access_token') is None \
            and cache_data.get('refresh_token') is None:
            if not self.test_spotify():
                self.log.error('Cached Spotify token is invalid')
                with open(self.cache_path, 'w') as f:
                    json.dump({}, f)
                return False
        return True

    def redirect(self):
        redirect_uri = request.base_url + 'callback'
        # Spotify no longer accepts "localhost" as a redirect host; the loopback
        # IP literal is required, so rewrite it transparently if the user
        # browsed to localhost instead of 127.0.0.1.
        redirect_uri = redirect_uri.replace('://localhost:', '://127.0.0.1:')
        self.spot_oath = self.spotify_oauth(redirect_uri)
        auth_url = self.spot_oath.get_authorize_url()
        return flask.redirect(auth_url)

    def spotify_callback(self):
        self.log.info('Spotify callback')
        if self.spot_oath is None:
            self.log.error('Cache dict or spot oath is None')
            return '', 500

        try:
            self.log.info('Getting access token')
            code = self.spot_oath.parse_response_code(request.url)
            self.spot_oath.get_access_token(code, as_dict=False,
                                            check_cache=False)
        except Exception as e:
            self.log.error(f'Failed to get Spotify access token: {e}')
            return 'Spotify authentication failed, please try again.', 400

        # verify the credentials actually work before confirming the connection
        # and starting the bots
        if not self.test_spotify():
            return ('Connected to Spotify but the credentials could not be '
                    'verified. Check your Spotify app settings and try '
                    'again.'), 400

        self.spotify_connected = True
        self.log.info('running start bot')
        self.start_bots()
        return 'Bot is running', 200

    def spotify_oauth(self, redirect_uri: str = 'https://open.spotify.com/'):
        return SpotifyOAuth(client_id=self.creds.spotify.client_id,
                            client_secret=self.creds.spotify.client_secret,
                            redirect_uri=redirect_uri,
                            scope=self.creds.spotify.scopes,
                            cache_handler=self.cache_handler)

    def test_spotify(self) -> bool:
        """Confirm the cached Spotify token works by making a real API call.

        Builds an OAuth manager around the cache handler so it works both after
        the interactive login and on startup from a cached token; spotipy
        refreshes an expired access token using the cached refresh token."""
        try:
            sp = Spotify(auth_manager=self.spotify_oauth())
            sp.current_user()
            self.log.info('Spotify credentials verified')
            return True
        except Exception as e:
            self.log.error(f'Spotify credential check failed: {e}')
            return False

    def start_bots(self):
        if self.bot_running:
            return
        self.bot_running = True
        self.start_twitch()
        self.start_discord()

    def start_twitch(self):
        self.log.info('Starting bot')
        self.loop.create_task(start_twitch_bot(self.creds, self.settings,
                                               self.audio_context, self.log,
                                               self.loop))

    def start_discord(self):
        self.log.info('Starting discord')
        self.loop.create_task(start_discord_hook(self.creds, self.settings,
                                                 self.loop))
        th.Thread(target=self.loop.run_forever).start()

    def index(self):
        if not self.spotify_connected:
            return self.redirect()
        self.start_bots()
        return 'Bot is running', 200

    def run(self):
        app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == "__main__":
    server = Server()

    @app.route("/", methods=["GET"])
    def route_index():
        return server.index()

    @app.route("/callback", methods=["GET"])
    def callback():
        return server.spotify_callback()

    @app.route("/static/style.css", methods=["GET"])
    def route_style():
        return flask.send_from_directory(static_folder, "style.css")

    server.run()
