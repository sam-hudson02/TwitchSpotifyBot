from flask import Flask, request
import flask
import spotipy
import os
import threading as th
import sys
path_src = os.path.abspath('./src')
sys.path.insert(1, path_src)
import main as bot
from utils import Log, Creds
from subprocess import Popen
import json

static_folder = os.path.abspath('./src/site/static')
app = Flask(__name__)

class Server:
    def __init__(self):
        if not os.path.exists('./data'):
            os.mkdir('./data')
        if not os.path.exists('./data/sbotify.log'):
            with open('./data/sbotify.log', 'w') as f:
                f.close()
        if not os.path.exists('./data/server.log'):
            with open('./data/server.log', 'w') as f:
                f.close()
        self.log = Log('Server', log_active=True, file='./data/server.log')
        self.creds = Creds(self.log)
        self.user = self.creds.spotify.username
        self.cache_path = os.path.abspath(f'./secret/.cache-{self.user}')
        self.proc = None
        if not os.path.exists(self.cache_path):
            with open(self.cache_path, 'w') as f:
                json.dump({}, f)
                self.spot_creds_cached = False
                f.close()
        else:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
                token = data.get('access_token')
                refresh = data.get('refresh_token')
                if token is not None and refresh is not None:
                    self.spot_creds_cached = True
                else:
                    self.spot_creds_cached = False
                del data
                del token
                del refresh
                f.close()

        self.cache = spotipy.oauth2.CacheFileHandler(cache_path=self.cache_path, username=self.user)
        self.scopes = 'user-modify-playback-state user-read-playback-state user-read-currently-playing ' \
                      'user-read-playback-position user-read-recently-played streaming'
        self.spot_oath = None
        self.process = None

    def redirect_to_spotify(self):
        self.log.info("Checking if bot is running...")
        if self.bot_running():
            self.log.info("Bot is running, redirecting to bot running page.")
            return flask.render_template("bot_running.html")
        elif self.spot_creds_cached:
            self.log.info("Bot is not running, but spotify creds are cached, starting bot...")
            th.Timer(1, self.start_bots).start()
            return flask.render_template("bot_running.html")
        else:
            self.log.info("Bot is not running, redirecting to spotify login.")
            redirect = request.base_url + "spotify-redirect"
            self.spot_oath = spotipy.SpotifyOAuth(client_id=self.creds.spotify.client_id, client_secret=self.creds.spotify.client_secret, 
                                                  redirect_uri=redirect, open_browser=False, scope=self.scopes, cache_handler=self.cache)
            return flask.redirect(self.spot_oath.get_authorize_url())
    
    def spotify_callback(self):
        if self.bot_running():
            return flask.redirect("/")
        self.log.info("Spotify callback received.")
        code = self.spot_oath.parse_response_code(request.url)
        self.spot_oath.get_access_token(code)
        self.log.info("Spotify login successful, starting bot.")
        if not self.bot_running():
            th.Timer(1, self.start_bots).start()
        return flask.render_template("bot_running.html")
    
    def start_bots(self):
        # check if running on windows or linux
        if self.bot_running():
            return
        if os.name == 'nt':
            self.log.info("Windows detected, starting bot with python")
            self.proc = Popen(["python", "src/main.py"])
        else:
            self.log.info("Linux detected, starting bot with python3")
            self.proc = Popen(["python3", "src/main.py"])

    def bot_running(self):
        if self.proc is None:
            return False
        return self.proc.poll() is None

    def bot_check(self):
        if self.bot_running():
            return "", 200
        else:
            return "", 503

    def terminate_bot(self):
        if self.bot_running():
            self.proc.terminate()
            self.proc = None
            return "", 200
        else:
            return "", 503

    def restart_bot(self):
        self.log.info("Restarting bot...")
        if self.bot_running():
            self.proc.terminate()
            self.proc = None
            th.Timer(1, self.start_bots).start()
            return "", 200
        else:
            return "", 503
    
    def run(self):
        app.run(host='0.0.0.0', port=5000)


if __name__ == "__main__":
    server = Server()
    @app.route("/", methods=["GET"])
    def route_index():
        return server.redirect_to_spotify()
    @app.route("/spotify-redirect", methods=["GET"])
    def route_spotify_redirect():
        return server.spotify_callback()
    @app.route("/bot-check", methods=["GET"])
    def route_bot_check():
        return server.bot_check()
    @app.route("/terminate-bot", methods=["GET"])
    def route_terminate_bot():
        return server.terminate_bot()
    @app.route("/restart-bot", methods=["GET"])
    def route_restart_bot():
        return server.restart_bot()
    @app.route("/static/style.css", methods=["GET"])
    def route_style():
        return flask.send_from_directory(static_folder, "style.css")
    server.run()

    

