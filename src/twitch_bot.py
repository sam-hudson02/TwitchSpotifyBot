import json
import traceback
import sys
import asyncio
import threading as th
import twitchio
import random
import string
import time
from twitchio.ext import commands, routines
from logger import Log
from db_handler import DB
from errors import *
from audio_controller import AudioController


class TwitchBot(commands.Bot):
    def __init__(self, token, twitch_channel, log: Log, db: DB, ac: AudioController):
        super().__init__(token, prefix='!', initial_channels=[twitch_channel])
        self.ac = ac
        self.db = db
        self.veto_votes = {'track': '', 'artist': '', 'votes': []}
        self.current_rates = {'track': '', 'artist': '', 'raters': []}
        self.units_full = {'s': 'seconds',
                           'm': 'minutes', 'h': 'hours', 'd': 'days'}
        self.units = {'s': 1, 'm': 60, 'h': 3600, 'd': 8}
        self.is_live = False
        self.settings = self.pull_settings()
        if self.settings is None:
            self.active = True
        else:
            self.active = bool(self.settings['active'])
        self.ac.context.active = self.active
        self.log = log
        self.channel_name = twitch_channel
        self.channel_obj = None
        self.user_cache = self.db.get_all_users()

    @routines.routine(seconds=3)
    async def update_song_context(self):
        if self.settings is None:
            self.settings = self.pull_settings()
            return
        if not self.is_live:
            return
        if not self.active:
            return
        await self.ac.update_context()

    def pull_settings(self):
        with open('./data/settings.json') as s_file:
            try:
                return json.load(s_file)
            except json.decoder.JSONDecodeError:
                self.log.error('Error loading settings.json')
                return {}

    def check_user(self, user):
        if user in self.user_cache:
            return None
        else:
            self.db.check_user_exists(user)
            self.user_cache.append(user)
            return None

    # creates routine to check if channel is live every 15 seconds
    @routines.routine(seconds=15)
    async def check_live(self):
        if self.settings is None:
            self.settings = self.pull_settings()
            return

        if self.channel_obj is None:
            return

        if bool(self.settings['dev mode']):
            self.set_live(True)
            return

        data = await self.fetch_streams([self.channel_obj.name])
        if len(data) == 0:
            self.set_live(False)
        else:
            self.set_live(True)

    def dump_settings(self):
        with open('./data/settings.json', 'w') as s:
            json.dump(self.settings, s)
            s.close()

    # method for finding a mentioned user
    def target_finder(self, request):
        words = request.split(' ')
        for word in words:
            if word.startswith('@'):
                target = word
                target = target.strip('@')
                target = target.strip('\n')
                target = target.strip('\r')
                target = target.strip(' ')
                self.db.check_user_exists(target)
                return target
        raise TargetNotFound

    # method for finding time duration (in seconds) in word containing numbers and unit
    # e.g. 5m would be return {'time': 360, 'unit': m}
    def time_finder(self, time_):
        for unit in self.units.keys():
            if unit in time_:
                time_ = time_.strip(unit)
                try:
                    time_ = int(time_)
                except ValueError:
                    raise TimeNotFound
                return {'time': time_, 'unit': unit}
        unit = 'm'
        time_ = time_.strip(unit)
        try:
            time_ = int(time_)
        except ValueError:
            raise TimeNotFound
        return {'time': time_, 'unit': unit}

    async def event_ready(self):
        self.log.info('Bot is ready')

    async def event_channel_joined(self, channel: twitchio.Channel):
        await channel.send(f'Sbotify is now online!')
        self.log.info(f'Bot joined {channel.name}')
        self.channel_obj = channel
        try:
            self.update_song_context.start()
        except RuntimeError:
            self.update_song_context.restart()
        try:
            self.check_live.start()
        except RuntimeError:
            self.check_live.restart()
       
    async def event_error(self, error: Exception, data: str = None):
        self.log.error(str(error))

    async def event_command_error(self, context: commands.Context, error: Exception) -> None:
        if isinstance(error, commands.errors.CommandOnCooldown):
            resp = str(error)
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, TrackAlreadyInQueue):
            resp = f'{error.track} by {error.artist} is already in the queue!'
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, NotAuthorized):
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)
            self.log.error(str(error.__traceback__))
            resp = f'Sorry, you must be a {error.clearance} to use the {context.command.name} command!'
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, TargetNotFound):
            resp = f'Could not find target.'
            await context.reply(resp)
            self.log.error(resp)

        elif isinstance(error, UserAlreadyRole):
            if error.has_role:
                resp = f'User is already {error.role}'
            else:
                resp = f'User is not {error.role}'
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, NotActive):
            resp = f'Song request are currently turned off.'
            if not self.is_live:
                resp = resp + f'({self.channel_name} not live)'
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, TrackRecentlyPlayed):
            resp = f'{error.track} by {error.artist} has been recently played.'
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, TimeNotFound):
            resp = f'Could not find time period.'
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, UserBanned):
            self.log.resp(
                f'User: {context.author.name} is banned, not responding.')

        elif isinstance(error, YoutubeLink):
            resp = "Youtube support is coming soon!"
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, UnsupportedLink):
            resp = "Please only use spotify links!"
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, DBError):
            resp = "A db error occurred during handling of request"
            await context.reply(resp)
            self.log.resp(resp)

        elif isinstance(error, asyncio.exceptions.TimeoutError):
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)
            self.log.error(error)
            if len(self.connected_channels) < 1:
                await asyncio.sleep(20)
                await self.join_channels(self.channel_name)
        else:
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr)
            self.log.error(error)

    # song request command
    @commands.cooldown(1, 10, commands.Bucket.channel)
    @commands.command(name='sr')
    async def sr(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        self.log.req(user, request, ctx.command.name)

        if not self.active:
            raise NotActive
        
        if not self.is_live:
            resp = f'Song request are currently turned off. ({self.channel_name} not live)'
            await ctx.reply(resp)
            self.log.resp(resp)
            return False
        
        if self.db.is_user_banned(user):
            raise UserBanned

        track, artist = self.ac.add_to_queue(request, user)

        if track is None:
            resp = f'Your request could not be found on spotify'
            await ctx.reply(resp)
            self.log.resp(resp)
            return False
        else:
            resp = f'{track} by {artist} has been added to the queue!'
            await ctx.reply(resp)
            self.log.resp(resp)
            self.db.add_requests(user)
            return True

    @commands.command(name='skip')
    async def skip(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        if not self.active:
            raise NotActive
        if not self.is_live:
            resp = f'Song request are currently turned off. ({self.channel_name} not live)'
            await ctx.reply(resp)
            self.log.resp(resp)
            return False
        
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        self.log.req(user, request, str(ctx.command.name))
        if self.db.is_user_privileged(user):
            await self.ac.play_next(skipped=True)
            resp = f'Skipping current track!'
            await ctx.reply(resp)
            self.log.resp(resp)
        else:
            raise NotAuthorized('mod')

    @commands.command(name='sp-mod')
    async def add_mod(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)
        com = str(ctx.prefix + ctx.command.name + ' ')
        request = ctx.message.content
        request = request.replace(com, '')

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

        if self.db.is_user_admin(user):
            self.db.mod_user(target)
            resp = f'@{target} is now a mod! Type !sp-help to see all the available commands!'
            await ctx.reply(resp)
            self.log.resp(resp)
        else:
            raise NotAuthorized('admin')

    @commands.command(name='sp-unmod')
    async def remove_mod(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

        if self.db.is_user_admin(user):
            self.db.mod_user(target)
            resp = f'@{target} is no longer a mod.'
            await ctx.reply(resp)
            self.log.resp(resp)
            return None
        else:
            raise NotAuthorized('admin')

    @commands.command(name='sp-ban')
    async def ban_command(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

        if self.ban(user, target):
            resp = f'@{target} has been banned!'
            await ctx.reply(resp)
            self.log.resp(resp)

    def ban(self, user, target):
        # if the user is an admin ban the target even if they're a mod
        if self.db.is_user_admin(user):
            self.db.ban_user(target)
            return True

        # if the user is a mod and the target isn't a mod or admin then ban the target
        elif self.db.is_user_mod(user) and not self.db.is_user_privileged(target):
            self.db.ban_user(target)
            return True

        else:
            raise NotAuthorized('mod/admin')

    @commands.command(name='sp-unban')
    async def unban_command(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

        if self.unban(user, target):
            resp = f'@{target} has been unbanned!'
            await ctx.reply(resp)
            self.log.resp(resp)

    def unban(self, user, target):
        # if user is a mod or admin and target is banned then unban them
        if self.db.is_user_privileged(user):
            self.db.unban_user(target)
            return True
        else:
            raise NotAuthorized('mod/admin')

    @commands.command(name='sp-timeout')
    async def timeout(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        com = str(ctx.prefix + ctx.command.name + ' ')
        request = ctx.message.content
        request = request.replace(com, '')

        self.log.req(user, request, ctx.command.name)

        target = self.target_finder(request)

        time_ = request.replace(f'@{target} ', '')
        time_ = time_.strip(' ')


        try:
            time_returned = self.time_finder(time_)
            if self.ban(user, target):
                resp = f'@{target} has been timed out for {time_returned["time"]} ' \
                       f'{self.units_full[time_returned["unit"]]}.'
                await ctx.reply(resp)
                self.log.resp(resp)
                time_secs = time_returned['time'] * \
                    self.units[time_returned['unit']]
                try:
                    th.Timer(time_secs, self.unban, [user, target])
                except UserAlreadyRole:
                    self.log.info(
                        f'Timeout ended for {target}, user already unbanned.')
        except ValueError:
            raise TimeNotFound

    @commands.command(name='sp-on')
    async def sp_on(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        if not self.active:
            if self.db.is_user_privileged(user):
                self.set_active(True)
                resp = 'Song request have been turned on!'
                await ctx.reply(resp)
                self.log.resp(resp)
            else:
                raise NotAuthorized('mod/admin')
        elif self.is_live:
            resp = f"Song request are already turned on but won't be taken till {self.channel_name} is live."
            await ctx.reply(resp)
            self.log.resp(resp)
        else:
            resp = f'Song request are already turned on.'
            await ctx.reply(resp)
            self.log.resp(resp)

    @commands.command(name='sp-off')
    async def sp_off(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        if self.active:
            if self.db.is_user_privileged(user):
                self.set_active(False)
                resp = 'Song request have been turned off!'
                await ctx.reply(resp)
                self.log.resp(resp)
            else:
                raise NotAuthorized('mod/admin')
        else:
            resp = f'Song request are already turned off.'
            await ctx.reply(resp)
            self.log.resp(resp)

    @commands.command(name='sp-status')
    async def sp_status(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        if bool(self.settings['active']):
            if self.is_live:
                resp = 'Song request are turned on!'
            else:
                resp = f"Song request are turned on but won't be taken till {self.channel_name} is live."
        else:
            resp = f'Song request are turned off.'

        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='song', aliases=['song-info'])
    async def song_info(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)
        if self.ac.context.track is None or self.ac.context.paused:
            resp = "No song currently playing!"

        elif self.ac.context.playing_queue:
            resp = f"Currently playing {self.ac.context.track} by {self.ac.context.artist} as requested by "\
                   f"@{self.ac.context.requester} !"
        else:
            resp = f"Currently playing {self.ac.context.track} by {self.ac.context.artist}!"
        await ctx.reply(resp)
        self.log.resp(resp)
        return None

    @commands.command(name='veto', aliases=['vote-skip'])
    async def veto(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        song_context = self.ac.context.get_context()

        resp, skip = self.add_veto(song_context, user)
        await ctx.reply(resp)
        self.log.resp(resp)
        if skip:
            self.ac.skip()

    def add_veto(self, song_context, user):
        if song_context is None:
            return None
            
        if (song_context['track'], song_context['artist']) != (self.veto_votes['track'], self.veto_votes['artist']):
            self.veto_votes['track'] = song_context['track']
            self.veto_votes['artist'] = song_context['artist']
            self.veto_votes['votes'] = []

        if user not in self.veto_votes['votes']:
            self.veto_votes['votes'].append(user)
        else:
            return f'You have already voted to veto the current song!', False

        votes = len(self.veto_votes['votes'])
        if votes >= self.settings['veto pass']:
            return f'{song_context["track"]} by {song_context["artist"]} has been vetoed by chat LUL', True
        else:
            return f'{votes} out of {self.settings["veto pass"]} chatters have voted to skip the current song!', False

    @commands.command(name='rate', aliases=['like'])
    async def rate(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        song_context = self.ac.context.get_context()

        resp = self.add_rate(song_context, user)
        if resp is not None:
            await ctx.reply(resp)
            self.log.resp(resp)

    def add_rate(self, song_context, rater):
        if song_context is None:
            return None

        if not song_context['playing_queue']:
            return None

        # keeps record what user have rated current track so users can't rate current more than once
        if (song_context['track'], song_context['artist']) != (self.current_rates['track'],
                                                               self.current_rates['artist']):
            self.current_rates['track'] = song_context['track']
            self.current_rates['artist'] = song_context['artist']
            self.current_rates['raters'] = []

        if rater in self.current_rates['raters']:
            return None

        if song_context['requester'] == rater:
            return "Sorry, you can't rate your own requests LUL"
        else:
            self.db.add_rate(receiver=song_context['requester'], giver=rater)
            self.current_rates['raters'].append(rater)
            return f"@{rater} liked @{song_context['requester']}'s song request!"

    @commands.command(name='sp-help')
    async def help(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)
        resp = "Here is a full list of commands: https://pastebin.com/vZ4bNiTn"
        await ctx.reply(resp)
        self.log.resp(resp)
    
    @commands.command(name='sp-set-veto-pass')
    async def set_veto_pass(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        if not self.db.is_user_privileged(user):
            raise NotAuthorized('mod/admin')

        try:
            new_veto_pass = int(request)
            if new_veto_pass < 2:
                resp = f'Veto pass must be at least 2'
            else:
                self.settings['veto pass'] = int(request)
                self.dump_settings()
                resp = f'Veto pass has been set to {new_veto_pass}'
        except ValueError:
            resp = f'Could not find a number in your command'
        await ctx.reply(resp)
        self.log.resp(resp)
    
    def set_active(self, active: bool):
        self.active = active
        self.ac.context.active = active

    def set_live(self, live: bool):
        self.is_live = live
        self.ac.context.live = live

    # TODO: add pause and resume commands
    # get random song from spotify
    @commands.command(name='sp-random')
    async def queue_random_song(self, ctx: commands.Context):

        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        self.log.req(user, request, ctx.command.name)

        if not self.settings['dev mode']:
            resp = f'Random song queueing is currently disabled (not in dev mode)'

        elif not self.db.is_user_admin(user):
            raise NotAuthorized('admin')

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        if request == '':
            num = 1
        else:
            try:
                num = int(request)
                if num > 25:
                    num = 25
            except ValueError:
                num = 1

        letter = random.choice(string.ascii_lowercase)
        results = self.ac.spot.sp.search(q=letter, type='playlist', limit=50)
        playlist = random.choice(results['playlists']['items'])

        # get random song from playlist
        results = self.ac.spot.sp.playlist_items(playlist['uri'], limit=100)
        

        resp = f'Adding {num} random tracks to the queue...!'
        await ctx.reply(resp)
        self.log.resp(resp)
        await self.add_randoms_to_queue(num, results, user)
        return

        

    async def add_randoms_to_queue(self, num, results, user):

        numbers = list(range(len(results['items'])))

        if num == 1:
            # select random songs from playlist
            song = random.choice(results['items'])
            self.ac.add_to_queue(song['track']['uri'], user=user)
        else:
            for _ in range(num):
                time.sleep(10)
                song_index = random.choice(numbers)
                song = results['items'][song_index]
                numbers.remove(song_index)

                self.ac.add_to_queue(song['track']['uri'], user=user)
