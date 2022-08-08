import contextlib
import html
import time
import git
import requests
from io import BytesIO
from telegram import Chat, MessageEntity, ParseMode, User
from subprocess import Popen, PIPE
import re
import os
import importlib
from typing import List

from psutil import cpu_percent, virtual_memory, disk_usage, boot_time
from platform import python_version
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.tl.types import InputMessagesFilterContacts, InputMessagesFilterDocument, InputMessagesFilterGeo, InputMessagesFilterGif, InputMessagesFilterMusic, InputMessagesFilterPhotos, InputMessagesFilterRoundVideo, InputMessagesFilterUrl, InputMessagesFilterVideo

from telethon import events

from pyrogram import filters
from pyrogram.errors import PeerIdInvalid
from pyrogram.types import Message, User

from telegram import MAX_MESSAGE_LENGTH, Update, MessageEntity, __version__ as ptbver, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackContext, CallbackQueryHandler, CommandHandler,
                          Filters, MessageHandler)
from telegram.ext.dispatcher import run_async
from telegram.error import BadRequest
from telegram.utils.helpers import escape_markdown, mention_html

from tg_bot import (
    dispatcher,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    DEV_USERS,
    SARDEGNA_USERS,
    WHITELIST_USERS,
    INFOPIC,
    sw,
    StartTime,
    pgram
)

SUPPORT_CHAT = "AsukaSupport"

from tg_bot.__main__ import STATS, USER_INFO, TOKEN
from tg_bot.modules.sql import SESSION
from tg_bot.modules.helper_funcs.chat_status import user_admin, sudo_plus
from tg_bot.modules.helper_funcs.extraction import extract_user
import tg_bot.modules.sql.users_sql as sql
from tg_bot.modules.users import __user_info__ as chat_count
from tg_bot.modules.language import gs
import datetime
import platform
from platform import python_version
from tg_bot.modules.helper_funcs.decorators import kigcmd, kigcallback
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.sql.antispam_sql import is_user_gbanned
from tg_bot.modules.redis.afk_redis import is_user_afk, afk_reason
from tg_bot.modules.sql.users_sql import get_user_num_chats
from tg_bot import telethn


MARKDOWN_HELP = f"""
Markdown is a very powerful formatting tool supported by telegram. {dispatcher.bot.first_name} has some enhancements, to make sure that \
saved messages are correctly parsed, and to allow you to create buttons.

- <code>_italic_</code>: wrapping text with '_' will produce italic text
- <code>*bold*</code>: wrapping text with '*' will produce bold text
- <code>`code`</code>: wrapping text with '`' will produce monospaced text, also known as 'code'
- <code>[sometext](someURL)</code>: this will create a link - the message will just show <code>sometext</code>, \
and tapping on it will open the page at <code>someURL</code>.
EG: <code>[test](example.com)</code>

- <code>[buttontext](buttonurl:someURL)</code>: this is a special enhancement to allow users to have telegram \
buttons in their markdown. <code>buttontext</code> will be what is displayed on the button, and <code>someurl</code> \
will be the url which is opened.
EG: <code>[This is a button](buttonurl:example.com)</code>

If you want multiple buttons on the same line, use :same, as such:
<code>[one](buttonurl://example.com)
[two](buttonurl://google.com:same)</code>
This will create two buttons on a single line, instead of one button per line.

Keep in mind that your message <b>MUST</b> contain some text other than just a button!
"""

@kigcmd(command='id', pass_args=True)
def get_id(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    chat = update.effective_chat
    msg = update.effective_message
    if user_id := extract_user(msg, args):
        if msg.reply_to_message and msg.reply_to_message.forward_from:

            user1 = message.reply_to_message.from_user
            user2 = message.reply_to_message.forward_from

            msg.reply_text(
                f"<b>Telegram ID:</b>,"
                f"• {html.escape(user2.first_name)} - <code>{user2.id}</code>.\n"
                f"• {html.escape(user1.first_name)} - <code>{user1.id}</code>.",
                parse_mode=ParseMode.HTML,
            )

        else:

            user = bot.get_chat(user_id)
            msg.reply_text(
                f"{html.escape(user.first_name)}'s id is <code>{user.id}</code>.",
                parse_mode=ParseMode.HTML,
            )

    elif chat.type == "private":
        msg.reply_text(
            f"Your id is <code>{chat.id}</code>.", parse_mode=ParseMode.HTML
        )

    else:
        msg.reply_text(
            f"This group's id is <code>{chat.id}</code>.", parse_mode=ParseMode.HTML
        )

@kigcmd(command='gifid')
def gifid(update: Update, _):
    msg = update.effective_message
    if msg.reply_to_message and msg.reply_to_message.animation:
        update.effective_message.reply_text(
            f"Gif ID:\n<code>{msg.reply_to_message.animation.file_id}</code>",
            parse_mode=ParseMode.HTML,
        )
    else:
        update.effective_message.reply_text("Please reply to a gif to get its ID.")

def no_by_per(totalhp, percentage):
    """
    rtype: num of `percentage` from total
    eg: 1000, 10 -> 10% of 1000 (100)
    """
    return totalhp * percentage / 100


def get_percentage(totalhp, earnedhp):
    """
    rtype: percentage of `totalhp` num
    eg: (1000, 100) will return 10%
    """

    matched_less = totalhp - earnedhp
    per_of_totalhp = 100 - matched_less * 100.0 / totalhp
    per_of_totalhp = str(int(per_of_totalhp))
    return per_of_totalhp        

def hpmanager(user):
    total_hp = (get_user_num_chats(user.id) + 10) * 10

    if not is_user_gbanned(user.id):

        # Assign new var `new_hp` since we need `total_hp` in
        # end to calculate percentage.
        new_hp = total_hp

        # if no username decrease 25% of hp.
        if not user.username:
            new_hp -= no_by_per(total_hp, 25)
        try:
            dispatcher.bot.get_user_profile_photos(user.id).photos[0][-1]
        except IndexError:
            # no profile photo ==> -25% of hp
            new_hp -= no_by_per(total_hp, 25)
        # if no /setme exist ==> -20% of hp
        if not sql.get_user_me_info(user.id):
            new_hp -= no_by_per(total_hp, 20)
        # if no bio exsit ==> -10% of hp
        if not sql.get_user_bio(user.id):
            new_hp -= no_by_per(total_hp, 10)

        if is_user_afk(user.id):
            afkst = afk_reason(user.id)
            # if user is afk and no reason then decrease 7%
            # else if reason exist decrease 5%
            new_hp -= no_by_per(total_hp, 7) if not afkst else no_by_per(total_hp, 5)
            # fbanned users will have (2*number of fbans) less from max HP
            # Example: if HP is 100 but user has 5 diff fbans
            # Available HP is (2*5) = 10% less than Max HP
            # So.. 10% of 100HP = 90HP

    else:
        new_hp = no_by_per(total_hp, 5)

    return {
        "earnedhp": int(new_hp),
        "totalhp": int(total_hp),
        "percentage": get_percentage(total_hp, new_hp),
    }


def make_bar(per):
    done = min(round(per / 10), 10)
    return "■" * done + "□" * (10 - done)
                
@kigcmd(command='info', pass_args=True)
def info(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    message = update.effective_message
    chat = update.effective_chat
    buttons = [
    [
                        InlineKeyboardButton(
                             text="Health",
                             url="https://t.me/AsukaUpdates/4"),
                       InlineKeyboardButton(
                             text="Disasters",
                             url="https://t.me/AsukaUpdates/5"),
                    ],
    ]
    user_id = extract_user(update.effective_message, args)

    if user_id:
        user = bot.get_chat(user_id)

    elif not message.reply_to_message and not args:
        user = message.from_user

    elif not message.reply_to_message and (
        not args
        or (
            len(args) >= 1
            and not args[0].startswith("@")
            and not args[0].isdigit()
            and not message.parse_entities([MessageEntity.TEXT_MENTION])
        )
    ):
        message.reply_text("I can't extract a user from this.")
        return

    else:
        return

    rep = message.reply_text("<code>Appraising...</code>", parse_mode=ParseMode.HTML)

    text = (
        f"╒═══「<b>• Appraisal Results •</b> 」\n\n"
        f"• ID: <code>{user.id}</code>\n"
        f"• First Name: {html.escape(user.first_name)}"
    )

    if user.last_name:
        text += f"\n• Last Name: {html.escape(user.last_name)}"

    if user.username:
        text += f"\n• Username: @{html.escape(user.username)}"

    text += f"\n• Userlink: {mention_html(user.id, 'link')}"

    if chat.type != "private" and user_id != bot.id:
        _stext = "\n• Presence: <code>{}</code>"

        afk_st = is_user_afk(user.id)
        if afk_st:
            text += _stext.format("AFK")
        else:
            status = status = bot.get_chat_member(chat.id, user.id).status
            if status:
                if status in {"left", "kicked"}:
                    text += _stext.format("Not here")
                elif status == "member":
                    text += _stext.format("Detected")
                elif status in {"administrator", "creator"}:
                    text += _stext.format("Admin")
    if user_id not in [bot.id, 777000, 1087968824]:
        userhp = hpmanager(user)
        text += f"\n\n<b>• Health:</b> <code>{userhp['earnedhp']}/{userhp['totalhp']}</code>\n[<i>{make_bar(int(userhp['percentage']))} </i>{userhp['percentage']}%]"

    try:
        spamwtc = sw.get_ban(int(user.id))
        if spamwtc:
            text += "\n\n<b>This person is Spamwatched!</b>"
            text += f"\nReason: <pre>{spamwtc.reason}</pre>"
            text += "\nAppeal at @SpamWatchSupport"
    except:
        pass  # don't crash if api is down somehow...

    disaster_level_present = False

    if user.id == OWNER_ID:
        text += "\n\n• Disaster Level: God"
        disaster_level_present = True
    elif user.id in DEV_USERS:
        text += "\n\n• Disaster Level: Evangelion Master"
        disaster_level_present = True
    elif user.id in SUDO_USERS:
        text += "\n\n• Disaster Level: Evangelion Pilot"
        disaster_level_present = True
    elif user.id in SUPPORT_USERS:
        text += "\n\n• Disaster Level: Evangelion 3.0"
        disaster_level_present = True
    elif user.id in SERDEGNA_USERS:
        text += "\n\n• Disaster Level: Evangelion 2.0"
        disaster_level_present = True
    elif user.id in WHITELIST_USERS:
        text += "\n\n• Disaster Level: Evengalion 1.0"
        disaster_level_present = True
    try:
        user_member = chat.get_member(user.id)
        if user_member.status == "administrator":
            result = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={chat.id}&user_id={user.id}",
            )
            result = result.json()["result"]
            if "custom_title" in result.keys():
                custom_title = result["custom_title"]
                text += f"\n\n• Title: <b>{custom_title}</b>"
        
    except BadRequest:
        pass
      
    for mod in USER_INFO:
        try:
            mod_info = mod.__user_info__(user.id).strip()
        except TypeError:
            mod_info = mod.__user_info__(user.id, chat.id).strip()
        if mod_info:
            text += "\n\n" + mod_info

    if INFOPIC:
        try:
            profile = context.bot.get_user_profile_photos(user.id).photos[0][-1]
            context.bot.sendChatAction(chat.id, "upload_photo")
            context.bot.send_photo(
            chat.id,
            photo=profile,
            caption=(text),
            reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML,            
        )
        # Incase user don't have profile pic, send normal text
        except IndexError:
            message.reply_text(
            text,
        reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML,            
                   )

    else:
        message.reply_text(
            text,
        reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.HTML,            
                   )

    rep.delete()

"""
def get_user_info(chat: Chat, user: User) -> str:
    bot = dispatcher.bot
    text = (
        f"<b>General:</b>\n"
        f"ID: <code>{user.id}</code>\n"
        f"First Name: {html.escape(user.first_name)}"
    )
    if user.last_name:
        text += f"\nLast Name: {html.escape(user.last_name)}"
    if user.username:
        text += f"\nUsername: @{html.escape(user.username)}"
    text += f"\nPermanent user link: {mention_html(user.id, 'link')}"
    with contextlib.suppress(Exception):
        if spamwtc := sw.get_ban(int(user.id)):
            text += "<b>\n\nSpamWatch:\n</b>"
            text += "<b>This person is banned in Spamwatch!</b>"
            text += f"\nReason: <pre>{spamwtc.reason}</pre>"
            text += "\nAppeal at @SpamWatchSupport"
        else:
            text += "<b>\n\nSpamWatch:</b>\n Not banned"
    Nation_level_present = False
    num_chats = sql.get_user_num_chats(user.id)
    text += f"\n<b>Chat count</b>: <code>{num_chats}</code>"
    with contextlib.suppress(BadRequest):
        user_member = chat.get_member(user.id)
        if user_member.status == "administrator":
            result = bot.get_chat_member(chat.id, user.id)
            if result.custom_title:
                text += f"\nThis user holds the title <b>{result.custom_title}</b> here."
    if user.id == OWNER_ID:
        text += '\nThis person is my owner'
        Nation_level_present = True
    elif user.id in DEV_USERS:
        text += '\nThis Person is a part of Eagle Union'
        Nation_level_present = True
    elif user.id in SUDO_USERS:
        text += '\nThe Nation level of this person is Royal'
        Nation_level_present = True
    elif user.id in SUPPORT_USERS:
        text += '\nThe Nation level of this person is Sakura'
        Nation_level_present = True
    elif user.id in SARDEGNA_USERS:
        text += '\nThe Nation level of this person is Sardegna'
        Nation_level_present = True
    elif user.id in WHITELIST_USERS:
        text += '\nThe Nation level of this person is Neptunia'
        Nation_level_present = True
    if Nation_level_present:
        text += f' [<a href="https://t.me/{bot.username}?start=nations">?</a>]'
    text += "\n"
    for mod in USER_INFO:
        if mod.__mod_name__ == "Users":
            continue

        try:
            mod_info = mod.__user_info__(user.id)
        except TypeError:
            mod_info = mod.__user_info__(user.id, chat.id)
        if mod_info:
            text += "\n" + mod_info
    return text
"""

def get_chat_info(user):
    text = (
        f"<b>Chat Info:</b>\n"
        f"<b>Title:</b> {user.title}"
    )
    if user.username:
        text += f"\n<b>Username:</b> @{html.escape(user.username)}"
    text += f"\n<b>Chat ID:</b> <code>{user.id}</code>"
    text += f"\n<b>Chat Type:</b> {user.type.capitalize()}"
    text += "\n" + chat_count(user.id)

    return text


@kigcmd(command='echo', pass_args=True, filters=Filters.chat_type.groups)
@user_admin
def echo(update: Update, _):
    args = update.effective_message.text.split(None, 1)
    message = update.effective_message

    if message.reply_to_message:
        message.reply_to_message.reply_text(args[1])
    else:
        message.reply_text(args[1], quote=False)

    message.delete()


def shell(command):
    process = Popen(command, stdout=PIPE, shell=True, stderr=PIPE)
    stdout, stderr = process.communicate()
    return (stdout, stderr)

@kigcmd(command='markdownhelp', filters=Filters.chat_type.private)
def markdown_help(update: Update, _):
    chat = update.effective_chat
    update.effective_message.reply_text((gs(chat.id, "markdown_help_text")), parse_mode=ParseMode.HTML)
    update.effective_message.reply_text(
        "Try forwarding the following message to me, and you'll see!"
    )
    update.effective_message.reply_text(
        "/save test This is a markdown test. _italics_, *bold*, `code`, "
        "[URL](example.com) [button](buttonurl:github.com) "
        "[button2](buttonurl://google.com:same)"
    )

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += f'{time_list.pop()}, '

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

stats_str = '''
'''
@kigcmd(command='stats', can_disable=False)
@sudo_plus
def stats(update, context):
    db_size = SESSION.execute("SELECT pg_size_pretty(pg_database_size(current_database()))").scalar_one_or_none()
    uptime = datetime.datetime.fromtimestamp(boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    botuptime = get_readable_time((time.time() - StartTime))
    status = "*╒═══「 System statistics: 」*\n\n"
    status += f"*• System Start time:* {str(uptime)}" + "\n"
    uname = platform.uname()
    status += f"*• System:* {str(uname.system)}" + "\n"
    status += f"*• Node name:* {escape_markdown(str(uname.node))}" + "\n"
    status += f"*• Release:* {escape_markdown(str(uname.release))}" + "\n"
    status += f"*• Machine:* {escape_markdown(str(uname.machine))}" + "\n"

    mem = virtual_memory()
    cpu = cpu_percent()
    disk = disk_usage("/")
    status += f"*• CPU:* {str(cpu)}" + " %\n"
    status += f"*• RAM:* {str(mem[2])}" + " %\n"
    status += f"*• Storage:* {str(disk[3])}" + " %\n\n"
    status += f"*• Python version:* {python_version()}" + "\n"
    status += f"*• python-telegram-bot:* {str(ptbver)}" + "\n"
    status += f"*• Uptime:* {str(botuptime)}" + "\n"
    status += f"*• Database size:* {str(db_size)}" + "\n"
    kb = [
          [
           InlineKeyboardButton('Ping', callback_data='pingCB')
          ]
    ]
    try:
        repo = git.Repo(search_parent_directories=True)
        sha = repo.head.object.hexsha
        status += f"*• Commit*: `{sha[:9]}`\n"
    except Exception as e:
        status += f"*• Commit*: `{str(e)}`\\n"

    try:
        update.effective_message.reply_text(status +
            "\n*Bot statistics*:\n"
            + "\n".join([mod.__stats__() for mod in STATS]) +
            "\n\n[⍙ GitHub](https://github.com/Dank-del/EnterpriseALRobot) | [⍚ GitLab](https://gitlab.com/Dank-del/EnterpriseALRobot)\n\n" +
            "╘══「 by [Dank-del](github.com/Dank-del) 」\n",
        parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(kb), disable_web_page_preview=True)
    except BaseException:
        update.effective_message.reply_text(
            (
                (
                    (
                        "\n*Bot statistics*:\n"
                        + "\n".join(mod.__stats__() for mod in STATS)
                    )
                    + "\n\n⍙ [GitHub](https://github.com/Dank-del/EnterpriseALRobot) | ⍚ [GitLab](https://gitlab.com/Dank-del/EnterpriseALRobot)\n\n"
                )
                + "╘══「 by [Dank-del](github.com/Dank-del) 」\n"
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(kb),
            disable_web_page_preview=True,
        )

@kigcmd(command='ping')
def ping(update: Update, _):
    msg = update.effective_message
    start_time = time.time()
    message = msg.reply_text("Pinging...")
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 3)
    message.edit_text(
        "*Pong!!!*\n`{}ms`".format(ping_time), parse_mode=ParseMode.MARKDOWN
    )


@kigcallback(pattern=r'^pingCB')
def pingCallback(update: Update, context: CallbackContext):
    query = update.callback_query
    start_time = time.time()
    requests.get('https://api.telegram.org')
    end_time = time.time()
    ping_time = round((end_time - start_time) * 1000, 3)
    query.answer(f'Pong! {ping_time}ms')


def get_help(chat):
    return gs(chat, "misc_help")



__mod_name__ = "Misc"
