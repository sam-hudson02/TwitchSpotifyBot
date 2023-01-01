from twitchio.ext import commands
from utils.errors import *
from utils import Settings, DB, Log, Perms
import datetime


class OfflineCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings: Settings = bot.settings
        self.check_user = bot.check_user
        self.log: Log = bot.log
        self.db: DB = bot.db

    @commands.command(name='help')
    async def help(self, ctx: commands.Context):
        await ctx.send('A list of commands can be found here: https://github.com/sam-hudson02/TwitchSpotifyBot/blob/main/Commands.md')

    @commands.command(name='sp-status')
    async def sp_status(self, ctx: commands.Context):
        if self.settings.active:
            if self.bot.is_live:
                resp = self.get_perm_resp()
            else:
                resp = f"Song request are turned on but won't be taken till {self.bot.channel_name} is live."
        else:
            resp = f'Song request are turned off.'

        await ctx.reply(resp)
        self.log.resp(resp)

    def get_perm_resp(self):
        if self.settings.permission is Perms.ALL:
            return 'Song request are turned on!'
        elif self.settings.permission is Perms.FOLLOWERS:
            return 'Song request are turned on for followers only!'
        elif self.settings.permission is Perms.SUBS:
            return 'Song request are turned on for subs only!'
        elif self.settings.permission is Perms.PRIVILEGED:
            return 'Song request are turned on for privileged users only!'

    @commands.command(name='sp-leader')
    async def leader(self, ctx: commands.Context):
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

        stats = self.db.get_user_stats(user)
        resp = f"Your position is {stats['pos']} with {stats['rates']} rates from {stats['requests']} requests and {stats['rates given']} rates given!"

        await ctx.reply(resp)
        self.log.resp(resp)

    @commands.command(name='sp-ping')
    async def ping(self, ctx: commands.Context):
        created_at = ctx.message.timestamp.timestamp()
        now = datetime.datetime.now().timestamp()
        received_time = round(now - created_at, 2)
        resp = f'Pong! Received in {received_time} seconds.'
        await ctx.reply(resp)
        self.log.resp(resp)
