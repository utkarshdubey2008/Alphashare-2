from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, FloodWait
from database import Database
from config import (
    FORCE_SUB_CHANNELS,
    FORCE_SUB_LINKS,
    Messages,
    Buttons,
    ADMIN_IDS,
    DB_CHANNEL_ID
)
import asyncio
import logging
from datetime import datetime

db = Database()
logger = logging.getLogger(__name__)

def get_size_formatted(size):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

async def check_force_sub(client: Client, user_id: int) -> list:
    if user_id in ADMIN_IDS:
        return []
    not_joined = []
    for channel_id in FORCE_SUB_CHANNELS:
        try:
            await client.get_chat_member(channel_id, user_id)
        except UserNotParticipant:
            not_joined.append(channel_id)
        except Exception as e:
            logger.error(f"Error checking channel {channel_id}: {e}")
    return not_joined

async def get_force_sub_buttons(not_joined: list) -> InlineKeyboardMarkup:
    buttons = []
    for channel_id in not_joined:
        if channel_id in FORCE_SUB_LINKS:
            link = FORCE_SUB_LINKS[channel_id]
            try:
                chat = await client.get_chat(channel_id)
                buttons.append([
                    InlineKeyboardButton(
                        f"📢 Join {chat.title}",
                        url=link
                    )
                ])
            except Exception as e:
                logger.error(f"Error getting chat info: {e}")
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("batch_"):
        await handle_batch_command(client, message, args[1])
        return
    await message.reply_text(
        text=Messages.START_TEXT.format(
            bot_name=client.me.first_name,
            user_mention=message.from_user.mention
        ),
        reply_markup=InlineKeyboardMarkup(Buttons.start_buttons()),
        disable_web_page_preview=True
    )

@Client.on_message(filters.command("upload") & filters.private)
async def upload_command(client: Client, message: Message):
    try:
        batch_id = message.text.split()[1]
        user_id = message.from_user.id
        batch_data = await db.get_batch(batch_id)
        if not batch_data or not batch_data.get("is_active", False):
            await message.reply_text(
                "❌ Invalid batch link or batch has been deleted.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Back to Home", callback_data="start")
                ]])
            )
            return
        not_joined = await check_force_sub(client, user_id)
        if not not_joined:
            await send_batch_files_without_forward(client, message, batch_data)
            return
        buttons = await get_force_sub_buttons(not_joined)
        buttons.inline_keyboard.append([
            InlineKeyboardButton("🔄 Try Again", callback_data=f"check_sub_{batch_id}")
        ])
        await message.reply_text(
            text=Messages.FORCE_SUB_TEXT,
            reply_markup=buttons
        )
    except Exception as e:
        logger.error(f"Error in upload command: {e}")
        await message.reply_text("❌ An error occurred. Please try again later.")

@Client.on_message(filters.command("batch_upload") & filters.private)
async def batch_upload_command(client: Client, message: Message):
    try:
        batch_id = message.text.split()[1]
        user_id = message.from_user.id
        batch_data = await db.get_batch(batch_id)
        if not batch_data or not batch_data.get("is_active", False):
            await message.reply_text(
                "❌ Invalid batch link or batch has been deleted.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Back to Home", callback_data="start")
                ]])
            )
            return
        not_joined = await check_force_sub(client, user_id)
        if not not_joined:
            await send_batch_files_without_forward(client, message, batch_data)
            return
        buttons = await get_force_sub_buttons(not_joined)
        buttons.inline_keyboard.append([
            InlineKeyboardButton("🔄 Try Again", callback_data=f"check_sub_{batch_id}")
        ])
        await message.reply_text(
            text=Messages.FORCE_SUB_TEXT,
            reply_markup=buttons
        )
    except Exception as e:
        logger.error(f"Error in batch_upload command: {e}")
        await message.reply_text("❌ An error occurred. Please try again later.")

async def send_batch_files_without_forward(client: Client, message: Message, batch_data: dict):
    try:
        files = batch_data.get("files", [])
        total_size = sum(file.get('size', 0) for file in files)
        info_text = (
            f"📦 **Batch Files**\n\n"
            f"📄 Total Files: {len(files)}\n"
            f"📊 Total Size: {get_size_formatted(total_size)}\n"
            f"⏰ Upload Date: {batch_data.get('created_at', 'N/A')}\n\n"
            f"Sending files..."
        )
        status_msg = await message.reply_text(info_text)
        for i, file in enumerate(files, 1):
            try:
                await client.send_document(
                    chat_id=message.chat.id,
                    document=file['file_id']
                )
                if i % 5 == 0:
                    await status_msg.edit_text(
                        f"{info_text}\n\n"
                        f"✅ Sent: {i}/{len(files)} files"
                    )
                    await asyncio.sleep(0.5)
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception as e:
                logger.error(f"Error sending file {file.get('name')}: {e}")
                continue
        await status_msg.edit_text(
            f"{info_text}\n\n"
            f"✅ Completed: {len(files)}/{len(files)} files sent"
        )
    except Exception as e:
        logger.error(f"Error in send_batch_files_without_forward: {e}")
        await message.reply_text("❌ An error occurred while sending files.")

@Client.on_callback_query(filters.regex('^check_sub_'))
async def check_subscription_callback(client: Client, callback: CallbackQuery):
    try:
        batch_id = callback.data.split('_')[2]
        user_id = callback.from_user.id
        not_joined = await check_force_sub(client, user_id)
        if not_joined:
            await callback.answer(
                "❌ Please join all channels first!", 
                show_alert=True
            )
            return
        batch_data = await db.get_batch(batch_id)
        if not batch_data or not batch_data.get("is_active", False):
            await callback.answer(
                "❌ This batch is no longer available!", 
                show_alert=True
            )
            return
        await callback.message.delete()
        message = await callback.message.reply_text("Processing...")
        await send_batch_files_without_forward(client, message, batch_data)
    except Exception as e:
        logger.error(f"Error in subscription callback: {e}")
        await callback.answer(
            "❌ An error occurred. Please try again.", 
            show_alert=True
    )
