from __future__ import annotations
from core import Rem
from utils import console
import logging


#----------Commands---------#
from .commands.help import Help
from .commands.general import General
from .commands.automod import Automod
from .commands.welcome import Welcomer
from .commands.fun import Fun
from .commands.Games import Games
from .commands.extra import Extra
from .commands.owner import Owner
from .commands.voice import Voice
from .commands.afk import afk
from .commands.ignore import Ignore
from .commands.Media import Media
from .commands.Invc import Invcrole
from .commands.giveaway import Giveaway
from .commands.Embed import Embed
from .commands.steal import Steal
from .commands.emoji_sync import EmojiSync
from .commands.ship import Ship
from .commands.timer import Timer
from .commands.blacklist import Blacklist
from .commands.block import Block
from .commands.nightmode import Nightmode
from .commands.imagine import AiStuffCog
from .commands.owner import Badges
from .commands.map import Map
from .commands.image import ImageCommands
from .commands.autoresponder import AutoResponder
from .commands.customrole import Customrole
from .commands.autorole import AutoRole
from .commands.ticket import TicketSystem
from .commands.logging import Logging
from .commands.translate import TranslateCog
from .commands.jail import Jail

from .commands.antinuke import Antinuke
from .commands.extraown import Extraowner
from .commands.anti_wl import Whitelist
from .commands.anti_unwl import Unwhitelist
from .commands.slots import Slots
from .commands.blackjack import Blackjack
from .commands.autoreact import AutoReaction
from .commands.stats import Stats
from .commands.emergency import Emergency
from .commands.notify import NotifCommands
from .commands.status import Status
from .commands.np import NoPrefix
from .commands.filters import FilterCog
from .commands.owner2 import Global
from .commands.qr import QR
from .commands.vanityroles import VanityRoles
from .commands.reactionroles import ReactionRoles 
from .commands.InviteTracker import InviteTracker
from .commands.messages import Messages
from .commands.msgpack import Messagespack
from .commands.fastgreet import FastGreet

#from .commands.activity import Activity
#____________ Events _____________

from .events.autoblacklist import AutoBlacklist
from .events.Errors import Errors
from .events.on_guild import Guild
from .events.autorole import Autorole2
from .events.auto import Autorole
from .events.greet2 import greet
from .events.mention import Mention
from .events.react import React
from .events.owner_protection import OwnerProtection
from .events.autoreact import AutoReactListener
########-------HELP-------########
from .rem.antinuke import _antinuke
from .rem.extra import _extra
from .rem.general import _general
from .rem.automod import _automod 
from .rem.moderation import _moderation
from .rem.fun import _fun
from .rem.games import _games
from .rem.ignore import _ignore
from .rem.server import _server
from .rem.voice import _voice 
from .rem.welcome import _welcome 
from .rem.giveaway import _giveaway
from .rem.ticket import _ticket
#from .rem.vanityroles import Vanityroles69999
from .rem.logging import Loggingdrop
from .rem.vanity import _vanity
from .rem.inviteTracker import _inviteTracker


#########ANTINUKE#########

from .antinuke.anti_member_update import AntiMemberUpdate
from .antinuke.antiban import AntiBan
from .antinuke.antibotadd import AntiBotAdd
from .antinuke.antichcr import AntiChannelCreate
from .antinuke.antichdl import AntiChannelDelete
from .antinuke.antichup import AntiChannelUpdate
from .antinuke.antieveryone import AntiEveryone
from .antinuke.antiguild import AntiGuildUpdate
from .antinuke.antiIntegration import AntiIntegration
from .antinuke.antikick import AntiKick
from .antinuke.antiprune import AntiPrune
from .antinuke.antirlcr import AntiRoleCreate
from .antinuke.antirldl import AntiRoleDelete
from .antinuke.antirlup import AntiRoleUpdate
from .antinuke.antiwebhook import AntiWebhookUpdate
from .antinuke.antiwebhookcr import AntiWebhookCreate
from .antinuke.antiwebhookdl import AntiWebhookDelete

#Extra Optional Events 

#from .antinuke.antiemocr import AntiEmojiCreate
#from .antinuke.antiemodl import AntiEmojiDelete
#from .antinuke.antiemoup import AntiEmojiUpdate
#from .antinuke.antisticker import AntiSticker
#from .antinuke.antiunban import AntiUnban

############ AUTOMOD ############
from .automod.antispam import AntiSpam
from .automod.anticaps import AntiCaps
from .automod.antilink import AntiLink
from .automod.anti_invites import AntiInvite
from .automod.anti_mass_mention import AntiMassMention
from .automod.anti_emoji_spam import AntiEmojiSpam
from .automod.protected_users import ProtectedUsers


from .moderation.ban import Ban
from .moderation.unban import Unban
from .moderation.timeout import Mute
from .moderation.unmute import Unmute
from .moderation.lock import Lock
from .moderation.unlock import Unlock
from .moderation.hide import Hide
from .moderation.unhide import Unhide
from .moderation.kick import Kick
from .moderation.warn import Warn
from .moderation.role import Role
from .moderation.message import Message
from .moderation.moderation import Moderation
from .moderation.topcheck import TopCheck
from .moderation.snipe import Snipe


log = logging.getLogger(__name__)


COGS_TO_LOAD = [
    Help, General, Automod, Welcomer, Fun, Games, Extra, Voice, Owner,
    Customrole, afk, Embed, Media, Ignore, Invcrole, Giveaway, Steal, EmojiSync,
    Ship, Timer, Blacklist, Block, Nightmode, Badges, AiStuffCog, InviteTracker,
    Antinuke, Whitelist,
    Unwhitelist, Extraowner, Slots, Blackjack, Stats, Emergency, Status,
    NoPrefix, FilterCog, Global, Map, ImageCommands, TicketSystem, Logging, QR, VanityRoles,
    ReactionRoles, Messages, Messagespack, TranslateCog, FastGreet, Jail,
    _antinuke, _extra, _general, _automod, _moderation, _fun, _games,
    _ignore, _server, _voice, _welcome, _giveaway, _ticket, Loggingdrop,
    _vanity, _inviteTracker,
    AutoBlacklist, Guild, Errors, Autorole2, Autorole, greet, AutoResponder,
    Mention, AutoRole, React, OwnerProtection, AutoReaction, AutoReactListener, NotifCommands,
    AntiMemberUpdate, AntiBan, AntiBotAdd, AntiChannelCreate, AntiChannelDelete,
    AntiChannelUpdate, AntiEveryone, AntiGuildUpdate, AntiIntegration, AntiKick,
    AntiPrune, AntiRoleCreate, AntiRoleDelete, AntiRoleUpdate, AntiWebhookUpdate,
    AntiWebhookCreate, AntiWebhookDelete, AntiSpam, AntiCaps, AntiInvite,
    AntiLink, AntiMassMention, AntiEmojiSpam, ProtectedUsers, Ban, Unban, Mute, Unmute, Lock,
    Unlock, Hide, Unhide, Kick, Warn, Role, Message, Moderation, TopCheck, Snipe,
]


async def setup(bot: Rem):
    loaded_names: set[str] = set()
    timer = console.LoadTimer("COGS")
    total = len(COGS_TO_LOAD)
    console.section(f"Loading cogs ({total})")
    loaded_count = 0

    for cog_cls in COGS_TO_LOAD:
        cog = cog_cls(bot)
        name = cog.qualified_name
        if name in loaded_names or bot.get_cog(name):
            log.warning("Skipping duplicate cog: %s", name)
            console.warn(f"Skipped duplicate cog: {name}")
            continue

        await bot.add_cog(cog)
        loaded_names.add(name)
        loaded_count += 1
        console.cog_progress(name, index=loaded_count, total=total)
        log.debug("Loaded cog: %s", name)

    timer.finish(f"Loaded {loaded_count} cog(s)")
