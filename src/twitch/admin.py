import random
import string
import time
from twitchio.ext import commands
from utils.errors import *

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log
        self.db = bot.db
        self.ac = bot.ac
        self.settings = bot.settings
        self.channel_name = bot.channel_name
    
    async def cog_check(self, ctx: commands.Context) -> bool:
        if not self.db.is_user_admin(ctx.author.name.lower()):
            raise NotAuthorized('admin')
        return True

    @commands.command(name='sp-set-veto-pass')
    async def set_veto_pass(self, ctx: commands.Context):
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

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
        self.bot.is_live = live
        self.ac.context.live = live
    
    @commands.command(name='sp-random')
    async def queue_random_song(self, ctx: commands.Context):
        user = ctx.author.name.lower()
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        if not self.settings.get_dev_mode():
            resp = f'Random song queueing is currently disabled (not in dev mode)'
            await ctx.reply(resp)
            self.log.resp(resp)
            return

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

    @commands.command(name='sp-mod')
    async def add_mod(self, ctx: commands.Context):
        com = str(ctx.prefix + ctx.command.name + ' ')
        request = ctx.message.content
        request = request.replace(com, '')

        target = self.target_finder(request)

        self.db.mod_user(target)
        resp = f'@{target} is now a mod! Type !sp-help to see all the available commands!'
        await ctx.reply(resp)
        self.log.resp(resp)
    
    @commands.command(name='sp-unmod')
    async def remove_mod(self, ctx: commands.Context):
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))

        target = self.target_finder(request)

        self.db.mod_user(target)
        resp = f'@{target} is no longer a mod.'
        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-on')
    async def sp_on(self, ctx: commands.Context):
        if not self.settings.get_active():
            self.set_active(True)
            resp = 'Song request have been turned on!'
            await ctx.reply(resp)
            self.log.resp(resp)
        elif self.bot.is_live:
            resp = f"Song request are already turned on but won't be taken till {self.channel_name} is live."
            await ctx.reply(resp)
            self.log.resp(resp)
        else:
            resp = f'Song request are already turned on.'
            await ctx.reply(resp)
            self.log.resp(resp)

    @commands.command(name='sp-off')
    async def sp_off(self, ctx: commands.Context):
        if self.settings.get_active():
            self.set_active(False)
            resp = 'Song request have been turned off!'
            await ctx.reply(resp)
            self.log.resp(resp)
        else:
            resp = f'Song request are already turned off.'
            await ctx.reply(resp)
            self.log.resp(resp)
    
    @commands.command(name='sp-dev-on')
    async def dev_mode_off(self, ctx: commands.Context):
        self.settings.set_dev_mode(True)

        resp = f'Dev mode is now on!'
        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-dev-off')
    async def dev_mode_on(self, ctx: commands.Context):     
        self.settings.set_dev_mode(False)

        resp = f'Dev mode is now off!'
        await ctx.reply(resp)
        self.log.resp(resp)

    def set_active(self, active: bool):
        self.settings.set_active(active)
        self.ac.context.active = active

    @commands.command(name='sp-lb-reset')
    async def leaderboard_reset(self, ctx: commands.Context):
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        request = request.strip(' ')

        self.settings.set_leaderboard_reset(request)
        resp = f'Leaderboard reset period has been set to {request}.'
        await ctx.reply(resp)
        self.log.resp(resp)
    
    @commands.command(name='sp-lb-rewards')
    async def leaderboard_reset_rewards(self, ctx: commands.Context):
        request = ctx.message.content.strip(str(ctx.prefix + ctx.command.name))
        args = request.split(' ')

        self.settings.set_leaderboard_reset_rewards(args)
        resp = f'Leaderboard reset rewards has been set to {args.join(", ")}.'
        await ctx.reply(resp)
        self.log.resp(resp)