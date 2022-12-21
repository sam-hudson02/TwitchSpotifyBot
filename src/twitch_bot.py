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

class Settings:
    def __init__(self, log: Log):
        self.log = log
        self.__active = False
        self.__dev_mode = False
        self.__veto_pass = 5
        self.__leaderboard_reset = None
        self.__leaderboard_rewards = []
        self.__leaderboard_announce = False
        self.__discord_bot = False
        self.__log = False
        self.set_settings()
    
    def save_settings(self):
        settings = {
            'active': int(self.__active),
            'dev mode': int(self.__dev_mode),
            'veto pass': self.__veto_pass,
            'leaderboard reset': self.__leaderboard_reset,
            'leaderboard rewards': self.__leaderboard_rewards,
            'leaderboard announce': int(self.__leaderboard_announce),
            'discord bot': int(self.__discord_bot),
            'log': self.__log
        }
        with open('./data/settings.json', 'w') as s_file:
            json.dump(settings, s_file, indent=4)

    def setter(func):
        def wrapper(self, *args, **kwargs):
            func(self, *args, **kwargs)
            if kwargs.get('save', True):
                self.save_settings()
        return wrapper

    def pull_settings(self, try_count=0):
        with open('./data/settings.json') as s_file:
            try:
                return json.load(s_file)
            except json.decoder.JSONDecodeError as e:
                if try_count > 3:
                    self.log.error('Error loading settings.json, too many tries.')
                    raise e
                self.log.error('Error loading settings.json, trying again in 5 seconds.')
                time.sleep(5)
                return self.pull_settings(try_count + 1)
            
    
    def set_settings(self):
        settings = self.pull_settings()
        self.set_active(bool(settings.get('active', False)), save=False)
        self.set_discord_bot(bool(settings.get('discord bot', False)), save=False)
        self.set_log(bool(settings.get('log', False)), save=False)
        self.set_dev_mode(bool(settings.get('dev_mode', False)), save=False)
        self.set_veto_pass(int(settings.get('veto_pass', 5)), save=False)
        self.set_leaderboard_reset(settings.get('leaderboard reset', 'off'), save=False)
        self.set_leaderboard_rewards(settings.get('leaderboard rewards', []), save=False)
        self.set_leaderboard_announce(bool(settings.get('leaderboard announce', False)), save=False)

    @setter
    def set_active(self, active, save=True):
        if type(active) is not bool:
            raise SettingsError('Active must be a boolean.')
        self.__active = active
    
    @setter
    def set_dev_mode(self, dev_mode, save=True):
        if type(dev_mode) is not bool:
            raise SettingsError('Dev mode must be a boolean.')
        self.__dev_mode = dev_mode
    
    @setter
    def set_veto_pass(self, veto_pass, save=True):
        if type(veto_pass) is not int:
            raise SettingsError('Veto pass must be an integer.')
        elif veto_pass < 2:
            raise SettingsError('Veto pass must be greater than 1.')
        self.__veto_pass = veto_pass
    
    @setter
    def set_leaderboard_reset(self, leaderboard_reset, save=True):
        if type(leaderboard_reset) is not str:
            raise SettingsError('Leaderboard reset must be a string.')

        leaderboard_reset = leaderboard_reset.lower()

        if leaderboard_reset == 'weekly':
            self.__leaderboard_reset = 'weekly'
        elif leaderboard_reset == 'monthly':
            self.__leaderboard_reset = 'monthly'
        elif leaderboard_reset == 'off':
            self.__leaderboard_reset = None
        else:
            raise SettingsError("Leaderboard reset must be either 'weekly', 'monthly' or 'off'")
    
    @setter
    def set_leaderboard_rewards(self, leaderboard_rewards, save=True):
        if type(leaderboard_rewards) is not list:
            raise SettingsError('Leaderboard rewards must be a list.')
        for item in leaderboard_rewards:
            if item not in ['vip', 'sp_mod']:
                raise SettingsError('Leaderboard rewards must only contain "vip" or "sp_mod".')
        self.__leaderboard_rewards = leaderboard_rewards

    @setter
    def set_leaderboard_announce(self, leaderboard_announce, save=True):
        if type(leaderboard_announce) is not bool:
            raise SettingsError('Leaderboard announce must be a boolean.')
        self.__leaderboard_announce = leaderboard_announce

    @setter
    def set_discord_bot(self, discord_bot, save=True):
        if type(discord_bot) is not bool:
            raise SettingsError('Discord bot must be a boolean.')
        self.__discord_bot = discord_bot

    @setter
    def set_log(self, log, save=True):
        if type(log) is not bool:
            raise SettingsError('Log must be a boolean.')
        self.__log = log

    def get_active(self):
        return self.__active
    
    def get_dev_mode(self):
        return self.__dev_mode
    
    def get_veto_pass(self):
        return self.__veto_pass
    
    def get_leaderboard_reset(self):
        return self.__leaderboard_reset
    
    def get_leaderboard_rewards(self):
        return self.__leaderboard_rewards
    
    def get_leaderboard_announce(self):
        return self.__leaderboard_announce

    def __str__(self) -> str:
        return f'Active: {self.__active}, Dev mode: {self.__dev_mode}, Veto pass: {self.__veto_pass}, Leaderboard reset: {self.__leaderboard_reset}, \
                Leaderboard rewards: {self.__leaderboard_rewards}, Leaderboard announce: {self.__leaderboard_announce}'


class TwitchBot(commands.Bot):
    def __init__(self, token: str, twitch_channel: str, log: Log, db: DB, ac: AudioController):
        super().__init__(token, prefix='!', initial_channels=[twitch_channel])
        self.ac = ac
        self.db = db
        self.veto_votes = {'track': '', 'artist': '', 'votes': []}
        self.current_rates = {'track': '', 'artist': '', 'raters': []}
        self.units_full = {'s': 'seconds',
                           'm': 'minutes', 'h': 'hours', 'd': 'days'}
        self.units = {'s': 1, 'm': 60, 'h': 3600, 'd': 8}
        self.is_live = False
        self.settings = Settings(log)
        self.ac.context.active = self.settings.get_active()
        self.log = log
        self.channel_name = twitch_channel
        self.channel_obj = None
        self.user_cache = self.db.get_all_users()

    @routines.routine(seconds=3)
    async def update_song_context(self):
        if not self.is_live:
            return
        if not self.settings.get_active():
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
        if self.channel_obj is None:
            return

        if self.settings.get_dev_mode():
            self.set_live(True)
            return

        data = await self.fetch_streams([self.channel_obj.id])
        if len(data) == 0:
            self.set_live(False)
        else:
            self.set_live(True)

    @routines.routine(hours=1)
    async def check_reset_leaderboard(self):
        period = self.settings.get_leaderboard_reset()
        if period is None:
            return

        last = self.db.get_last_reset()
        leader = self.db.get_leader()

        if leader is None:
            return

        if last is None:
            rewards = self.give_rewards(leader)
            self.db.reset_leaderboard(leader, period=period, rewards=rewards)
            return

        # checks if leaderboard reset is due by comparing reset time to current time
        if not int(time.time()) > last[3]:
            return

        if period == 'weekly':
            rewards = self.give_rewards(leader)
            self.db.reset_leaderboard(leader, period=period, rewards=rewards)
        elif period == 'monthly':
            rewards = self.give_rewards(leader)
            self.db.reset_leaderboard(leader, period=period, rewards=rewards)
        if bool(last[5]):
            self.remove_rewards(last[0])
            self.db.remove_active_lb(last[0])
        

            
            
    def give_rewards(self, leader):
        rewards = self.settings.get_leaderboard_rewards()
        rewards_return = {}

        if self.db.is_user_privileged(leader):
            pass
        elif 'sp_mod' in rewards:
            self.db.mod_user(leader)
            rewards_return['sp_mod'] = 1
        
        return rewards_return

    def remove_rewards(self, last):
        if bool(last[4]):
            self.db.remove_privilege_user(last[1])    
    
    @update_song_context.error
    async def context_error(self, error):
        self.log.error(str(error))
        await self.init_routines()

    @check_live.error
    async def live_error(self, error):
        self.log.error(str(error))
        await self.init_routines()

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

    async def routine_init(self):
        self.log.info('Starting routines')
        try:
            self.update_song_context.start()
        except RuntimeError:
            self.update_song_context.restart()
        try:
            self.check_live.start()
        except RuntimeError:
            self.check_live.restart()

    async def event_ready(self):
        self.log.info('Bot is ready')

    async def event_reconnect(self):
        self.log.info('Bot reconnected')
        self.log.info('Restarting routines')
        await self.routine_init()

    async def event_channel_joined(self, channel: twitchio.Channel):
        await channel.send(f'Sbotify is now online!')
        self.log.info(f'Bot joined {channel.name}')
        self.channel_obj = await channel.user()
        await self.routine_init()

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

        elif isinstance(error, SettingsError):
            await context.reply(error.message)
            self.log.resp(error.message)
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

        if not self.settings.get_active():
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

        if not self.settings.get_active():
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

        if not self.settings.get_active():
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

        if self.settings.get_active():
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

        if self.settings.get_active():
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
        if self.ac.context.track is None or self.ac.context.paused or not self.is_live:
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
        if votes >= self.settings.get_veto_pass():
            return f'{song_context["track"]} by {song_context["artist"]} has been vetoed by chat LUL', True
        else:
            return f'{votes} out of {self.settings.get_veto_pass()} chatters have voted to skip the current song!', False

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

    @commands.command(name='sp-leader')
    async def leader(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        leader = self.db.get_leader()
        if leader is None:
            resp = "No one has been rated yet!"
        else:
            resp = f"Current leader is @{leader[0]} with {leader[1]} rates!"

        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-stats')
    async def stats(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        self.check_user(user)

        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        self.log.req(user, request, ctx.command.name)

        stats = self.db.get_user_stats(user)
        resp = f"Your position is {stats['pos']} with {stats['rates']} rates from {stats['requests']} requests and {stats['rates given']} rates given!"

        await ctx.reply(resp)
        self.log.resp(resp)

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
                self.settings.set_veto_pass(int(request))  
                self.dump_settings()
                resp = f'Veto pass has been set to {new_veto_pass}'
        except ValueError:
            resp = f'Could not find a number in your command'
        await ctx.reply(resp)
        self.log.resp(resp)

    def set_active(self, active: bool):
        self.settings.set_active(active)
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

        if not self.settings.get_dev_mode():
            resp = f'Random song queueing is currently disabled (not in dev mode)'
            await ctx.reply(resp)
            self.log.resp(resp)
            return

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

    @commands.command(name='sp-dev-on')
    async def dev_mode_off(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        self.log.req(user, request, ctx.command.name)

        if not self.db.is_user_admin(user):
            raise NotAuthorized('admin')
        
        self.settings.set_dev_mode(True)

        resp = f'Dev mode is now on!'
        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-dev-off')
    async def dev_mode_on(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        self.log.req(user, request, ctx.command.name)

        if not self.db.is_user_admin(user):
            raise NotAuthorized('admin')
        
        self.settings.set_dev_mode(False)

        resp = f'Dev mode is now off!'
        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-lb-reset')
    async def leaderboard_reset(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        request = request.strip(' ')

        self.log.req(user, request, ctx.command.name)

        if not self.db.is_user_admin(user):
            raise NotAuthorized('admin')

        self.settings.set_leaderboard_reset(request)
        resp = f'Leaderboard reset period has been set to {request}.'
        await ctx.reply(resp)
        self.log.resp(resp)
    
    @commands.command(name='sp-lb-rewards')
    async def leaderboard_reset_rewards(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        args = request.split(' ')

        self.log.req(user, request, ctx.command.name)

        if not self.db.is_user_admin(user):
            raise NotAuthorized('admin')

        self.settings.set_leaderboard_reset_rewards(args)
        resp = f'Leaderboard reset rewards has been set to {args.join(", ")}.'
        await ctx.reply(resp)
        self.log.resp(resp)