import os
import sys
from collections import Counter
from datetime import datetime
from shutil import copyfile

import aiohttp
import discord
from dateutil.relativedelta import relativedelta
from discord.ext import commands

from firetail.lib import ESI, db
from firetail.utils import ExitCodes

# Lets check the config file exists before we continue..
if os.getenv("CONFIG") is not None:
    if not os.path.exists(os.getenv("CONFIG") + "/config.py"):
        print("Copying example_config.py to " + os.getenv("CONFIG") + "/config.py")
        copyfile("/firetail/firetail/example_config.py", "/config/config.py") # for some reason os.getcwd() doesn't work inside a container ??
        sys.exit(1)

if os.getenv("CONFIG") is not None:
    sys.path.insert(0, os.getenv("CONFIG"))
    import config
else:
    from firetail import config


async def prefix_manager(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(bot.default_prefix)(bot, message)

    prefix = bot.prefixes.get(message.guild.id) or bot.default_prefix
    return commands.when_mentioned_or(prefix)(bot, message)


class Firetail(commands.Bot):
    def __init__(self, **kwargs):
        self.default_prefix = config.bot_prefix
        self.owner = config.bot_master
        self._shutdown_mode = ExitCodes.CRITICAL
        self.counter = Counter()
        self.core_dir = os.path.dirname(os.path.realpath(__file__))
        self.config = config
        self.default_prefix = config.bot_prefix[0]
        self.prefixes = {}
        self.bot_users = []
        self.repeat_offender = []
        self.last_command = None
        self.token = config.bot_token
        self.req_perms = discord.Permissions(config.bot_permissions)
        self.co_owners = config.bot_coowners
        self.preload_ext = config.preload_extensions
        kwargs["command_prefix"] = prefix_manager
        kwargs["pm_help"] = True
        # kwargs["command_prefix"] = self.db.prefix_manager
        kwargs["owner_id"] = self.owner
        super().__init__(**kwargs)
        self.session = aiohttp.ClientSession(loop=self.loop)
        self.esi_data = ESI(self.session)
        self.loop.create_task(self.load_db())

    async def load_db(self):
        await db.create_tables()
        data = await db.select("SELECT * FROM prefixes")
        self.prefixes = dict(data)

    async def send_cmd_help(self, ctx):
        if ctx.invoked_subcommand:
            pages = await self.formatter.format_help_for(
                ctx, ctx.invoked_subcommand)
            for page in pages:
                await ctx.author.send(page)
        else:
            pages = await self.formatter.format_help_for(
                ctx, ctx.command)
            for page in pages:
                await ctx.author.send(page)

    async def shutdown(self, *, restart=False):
        """Shutdown the bot.
        Safely ends the bot connection while passing the exit code based
        on if the intention was to restart or close.
        """
        if not restart:
            self._shutdown_mode = ExitCodes.SHUTDOWN
        else:
            self._shutdown_mode = ExitCodes.RESTART
        await self.logout()

    @discord.utils.cached_property
    def invite_url(self):
        invite_url = discord.utils.oauth_url(self.user.id,
                                             permissions=self.req_perms)
        return invite_url

    @property
    def uptime(self):
        return relativedelta(datetime.utcnow(), self.launch_time)

    @property
    def uptime_str(self):
        uptime = self.uptime
        year_str, month_str, day_str, hour_str = ('',)*4
        if uptime.years >= 1:
            year_str = "{0}y ".format(uptime.years)
        if uptime.months >= 1 or year_str:
            month_str = "{0}m ".format(uptime.months)
        if uptime.days >= 1 or month_str:
            d_unit = 'd' if month_str else ' days'
            day_str = "{0}{1} ".format(uptime.days, d_unit)
        if uptime.hours >= 1 or day_str:
            h_unit = ':' if month_str else ' hrs'
            hour_str = "{0}{1}".format(uptime.hours, h_unit)
        m_unit = '' if month_str else ' mins'
        mins = uptime.minutes if month_str else ' {0}'.format(uptime.minutes)
        secs = '' if day_str else ' {0} secs'.format(uptime.seconds)
        min_str = "{0}{1}{2}".format(mins, m_unit, secs)

        uptime_str = ''.join((year_str, month_str, day_str, hour_str, min_str))

        return uptime_str

    @property
    def command_count(self):
        return self.counter["processed_commands"]

    @property
    def message_count(self):
        return self.counter["messages_read"]

    @property
    def resumed_count(self):
        return self.counter["sessions_resumed"]
