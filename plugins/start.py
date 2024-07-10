import re
import os
import asyncio
import random
import time
import base64
import string
import logging

from pyrogram import Client, filters, __version__
from pyrogram.enums import ParseMode
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated

from bot import Bot
from config import ADMINS, FORCE_MSG, START_MSG, CUSTOM_CAPTION, DISABLE_CHANNEL_BUTTON, PROTECT_CONTENT, OWNER_ID, SHORTLINK_API_URL, SHORTLINK_API_KEY, USE_PAYMENT, USE_SHORTLINK, VERIFY_EXPIRE, TIME, TUT_VID
from helper_func import get_readable_time, increasepremtime, subscribed, subscribed2, decode, get_messages, get_shortlink, get_verify_status, update_verify_status, get_exp_time
from database.database import add_user, del_user, full_userbase, present_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECONDS = TIME 
TUT_VID = f"{TUT_VID}"
PROTECT_CONTENT = False

WAIT_MSG = "<b>Processing ...</b>"
REPLY_ERROR = "<blockquote><b>Use this command as a reply to any telegram message without any spaces.</b></blockquote>"

async def handle_verification(client, message, id, verify_status):
    if "verify_" in message.text:
        _, token = message.text.split("_", 1)
        if verify_status['verify_token'] != token:
            return await message.reply("<blockquote><b>🔴 Your token verification is invalid or Expired, Hit /start command and try again<b></blockquote>")
        await update_verify_status(id, is_verified=True, verified_time=time.time())
        await message.reply("<blockquote><b>Hooray 🎉, your token verification is successful\n\n Now you can access all files for 24-hrs...</b></blockquote>", protect_content=False, quote=True)

@Bot.on_message(filters.command('start') & filters.private & subscribed & subscribed2)
async def start_command(client: Client, message: Message):
    id = message.from_user.id
    try:
        if not await present_user(id):
            await add_user(id)
    except Exception as e:
        logger.error(f"Error adding user {id}: {e}")
    
    if USE_SHORTLINK and id not in ADMINS:
        try:
            verify_status = await get_verify_status(id)
            if verify_status['is_verified'] and VERIFY_EXPIRE < (time.time() - verify_status['verified_time']):
                await update_verify_status(id, is_verified=False)
            await handle_verification(client, message, id, verify_status)
        except Exception as e:
            logger.error(f"Error handling verification for user {id}: {e}")
    
    if len(message.text) > 7:
        try:
            base64_string = message.text.split(" ", 1)[1]
            decoded_string = await decode(base64_string)
            argument = decoded_string.split("-")
            ids = []
            if len(argument) == 3:
                start, end = int(int(argument[1]) / abs(client.db_channel.id)), int(int(argument[2]) / abs(client.db_channel.id))
                ids = range(start, end + 1) if start <= end else range(end, start + 1)
            elif len(argument) == 2:
                ids = [int(int(argument[1]) / abs(client.db_channel.id))]
            temp_msg = await message.reply("Please wait... 🫷")
            messages = await get_messages(client, ids)
            await temp_msg.delete()
            snt_msgs = []
            for msg in messages:
                caption = CUSTOM_CAPTION.format(previouscaption="" if not msg.caption else msg.caption.html, filename=msg.document.file_name) if CUSTOM_CAPTION and msg.document else (msg.caption.html if msg.caption else "")
                reply_markup = None if DISABLE_CHANNEL_BUTTON else msg.reply_markup
                try:
                    snt_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    snt_msgs.append(snt_msg)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    snt_msg = await msg.copy(chat_id=message.from_user.id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=reply_markup, protect_content=PROTECT_CONTENT)
                    snt_msgs.append(snt_msg)
                except Exception as e:
                    logger.error(f"Error sending message to user {id}: {e}")
                    continue
                
            notification_msg = await message.reply(f"<blockquote><b>🔴 This file will be deleted in {SECONDS // 60} minutes. Please save or forward it to your saved messages before it gets deleted.</b></blockquote>")
            await asyncio.sleep(SECONDS)
            for snt_msg in snt_msgs:
                try:
                    await snt_msg.delete()
                except Exception as e:
                    logger.error(f"Error deleting message for user {id}: {e}")
                    continue
            await notification_msg.edit(f"<blockquote><b>🗑️ Hey @{message.from_user.username}, your file has been successfully deleted!</b></blockquote>")
            return
        except Exception as e:
            logger.error(f"Error processing message for user {id}: {e}")
            return
    
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🦋 More", callback_data="about"), InlineKeyboardButton("📴 Close", callback_data="close")]
    ])
    await message.reply_text(
        text=START_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=reply_markup,
        disable_web_page_preview=True,
        quote=True
    )

@Bot.on_message(filters.command('start') & filters.private)
async def not_joined(client: Client, message: Message):
    buttons = [
        [InlineKeyboardButton("Join 1", url="https://t.me/+KvZCcSyOZ2plZTc9"), InlineKeyboardButton("Join 2", url=client.invitelink)],
        [InlineKeyboardButton("Join 3", url="https://t.me/+rXrYdP3-KzRlYTI9"), InlineKeyboardButton("Join 4", url="https://t.me/+e2XqhuSiab9iM2E1")]
    ]
    try:
        buttons.append([InlineKeyboardButton("🔄 Try Again", url=f"https://t.me/{client.username}?start={message.command[1]}")])
    except IndexError:
        pass

    await message.reply(
        text=FORCE_MSG.format(
            first=message.from_user.first_name,
            last=message.from_user.last_name,
            username=None if not message.from_user.username else '@' + message.from_user.username,
            mention=message.from_user.mention,
            id=message.from_user.id
        ),
        reply_markup=InlineKeyboardMarkup(buttons),
        quote=True,
        disable_web_page_preview=True
    )

@Bot.on_message(filters.command('users') & filters.private & filters.user(ADMINS))
async def get_users(client: Bot, message: Message):
    msg = await client.send_message(chat_id=message.chat.id, text=WAIT_MSG)
    try:
        users = await full_userbase()
        await msg.edit(f"{len(users)} users are using this bot")
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        await msg.edit("Failed to fetch user list.")

@Bot.on_message(filters.private & filters.command('broadcast') & filters.user(ADMINS))
async def send_text(client: Bot, message: Message):
    if message.reply_to_message:
        query = await full_userbase()
        broadcast_msg = message.reply_to_message
        total, successful, blocked, deleted, unsuccessful = 0, 0, 0, 0, 0

        pls_wait = await message.reply("<b>Broadcasting Message.. This will Take Some Time ⌚</b>")
        for chat_id in query:
            try:
                await broadcast_msg.copy(chat_id)
                successful += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
                await broadcast_msg.copy(chat_id)
                successful += 1
            except UserIsBlocked:
                await del_user(chat_id)
                blocked += 1
            except InputUserDeactivated:
                await del_user(chat_id)
                deleted += 1
            except Exception as e:
                unsuccessful += 1
                logger.error(f"Error broadcasting to user {chat_id}: {e}")
                continue
            total += 1

        status = f"""<blockquote><b>Broadcast Completed

-Total Users     : {total}
-Successful      : {successful}
-Blocked Users   : {blocked}
-Deleted Accounts: {deleted}
-Unsuccessful    : {unsuccessful}</b></blockquote>"""
        return await pls_wait.edit(status)
    else:
        msg = await message.reply(REPLY_ERROR)
        await asyncio.sleep(8)
        await msg.delete()

if USE_PAYMENT:
    @Bot.on_message(filters.command('add_prem') & filters.private & filters.user(ADMINS))
    async def add_user_premium_command(client: Bot, message: Message):
        try:
            user_id_msg = await client.ask(text="Enter id of user\nHit /cancel to cancel", chat_id=message.chat.id)
            if user_id_msg.text == "/cancel":
                await message.reply("<b>Cancelled adding user to premium list</b>")
                return
            id = int(user_id_msg.text)
            exp_time_msg = await client.ask(text="Enter time in days\nHit /cancel to cancel", chat_id=message.chat.id)
            if exp_time_msg.text == "/cancel":
                await message.reply("<b>Cancelled adding user to premium list</b>")
                return
            exp_time = int(exp_time_msg.text)
            if not await present_user(id):
                return await message.reply(f"User {id} not found in Database!")
            await increasepremtime(id, exp_time)
            new_expiry_time = await get_exp_time(id)
            await message.reply(f"Successfully added user to premium list till {new_expiry_time}")
        except Exception as e:
            logger.error(f"Error adding premium user: {e}")
            await message.reply("<b>Something went wrong while adding user to premium list</b>")
