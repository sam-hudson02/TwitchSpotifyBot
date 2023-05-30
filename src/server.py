import json
from utils import Log, Creds, init_dirs, Settings
import asyncio
import os
from spotipy.oauth2 import CacheFileHandler
from spotipy import SpotifyOAuth
import flask
from flask import Flask, request
from main import start_twitch_bot, start_discord_hook
from AudioController.audio_controller import Context
import threading as th

static_folder = os.path.abspath('./src/static')
app = Flask(__name__)
bot_running_page = f'{static_folder}/bot_running.html'

app.static_folder = static_folder


class Server:
    def __init__(self):
        init_dirs()
        self.log = Log('server', './data/server.log')
        self.creds = Creds(self.log)
        self.user = self.creds.spotify.username
        self.cache_path = f'./secret/.cache-{self.user}'
        self.spotify_connected = False
        self.cache_dict = self.load_cache()
        self.cache_handler = CacheFileHandler(cache_path=self.cache_path,
                                              username=self.user)
        self.spot_oath = None
        self.settings = Settings()
        self.audio_context = Context()
        self.bot_running = False
        self.loop = asyncio.new_event_loop()
        if self.spotify_connected:
            self.start_twitch()
            self.start_discord()

    def load_cache(self) -> None | dict:
        if not os.path.exists(self.cache_path):
            with open(self.cache_path, 'w') as f:
                self.log.info('Cache file does not exist, creating')
                json.dump({}, f)
            return None
        data = None
        with open(self.cache_path, 'r') as f:
            self.log.info('Loading cache file')
            data = json.load(f)
            token = data.get('token')
            refresh = data.get('refresh')
            self.spotify_connected = True

        if token is None or refresh is None:
            return None

        return data

    def redirect(self):
        redirect_uri = request.base_url + 'callback'
        self.spot_oath = SpotifyOAuth(client_id=self.creds.spotify.client_id,
                                      client_secret=self.creds.spotify.client_secret,
                                      redirect_uri=redirect_uri,
                                      scope=self.creds.spotify.scopes,
                                      cache_handler=self.cache_handler)
        auth_url = self.spot_oath.get_authorize_url()
        return flask.redirect(auth_url)

    def spotify_callback(self):
        self.log.info('Spotify callback')
        if self.spot_oath is None:
            self.log.error('Cache dict or spot oath is None')
            return '', 500

        self.log.info('Getting access token')
        code = self.spot_oath.parse_response_code(request.url)
        self.spot_oath.get_access_token(code, as_dict=False, check_cache=False)
        self.spotify_connected = True
        self.log.info('running start bot')
        self.start_twitch()
        self.start_discord()
        return 'Bot is running', 200

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
        if not self.bot_running:
            self.start_twitch()
            self.start_discord()
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
