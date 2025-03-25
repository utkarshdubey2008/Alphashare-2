from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from database import Database
from datetime import datetime
import config
import asyncio
from handlers.utils.message_delete import schedule_message_deletion
from utils.button_manager import ButtonManager

db = Database()
button_manager = ButtonManager()

async def check_force_sub(client: Client, user_id: int) -> bool:
    if not config.FORCE_SUB_CHANNELS:
        return True
    
    for channel_id in config.FORCE_SUB_CHANNELS:
        try:
            member = await client.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except UserNotParticipant:
            return False
        except Exception:
            continue
    return True

def get_force_sub_buttons(file_id=None):
    buttons = []
    for channel_id in config.FORCE_SUB_CHANNELS:
        if channel_id in config.FORCE_SUB_LINKS:
            buttons.append([
                InlineKeyboardButton("🔔 Join Channel", url=config.FORCE_SUB_LINKS[channel_id])
            ])
    
    start_command = "/start"
    if file_id:
        start_command += f" {file_id}"
        
    buttons.append([
        InlineKeyboardButton(
            "🔄 Refresh",
            url=f"https://t.me/{config.BOT_USERNAME}?start={start_command}"
        )
    ])
    return buttons

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await db.add_user(message.from_user.id, message.from_user.username)

    file_id = message.command[1] if len(message.command) > 1 else None

    if not await check_force_sub(client, message.from_user.id):
        await message.reply_text(
            "⚠️ Access Restricted\n\nPlease join our channel first and click 'Refresh' to continue.",
            reply_markup=InlineKeyboardMarkup(get_force_sub_buttons(file_id)),
            protect_content=config.PRIVACY_MODE
        )
        return

    if file_id:
        if file_id.startswith("batch_"):
            await handle_batch_download(client, message, file_id.split("_")[1])
            return
            
        file_data = await db.get_file(file_id)
        if not file_data:
            await message.reply_text(
                "❌ File not found or has been deleted!", 
                protect_content=config.PRIVACY_MODE
            )
            return

        try:
            msg = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=config.DB_CHANNEL_ID,
                message_id=file_data["message_id"],
                protect_content=config.PRIVACY_MODE
            )

            await db.increment_downloads(file_id)
            await db.update_file_message_id(file_id, msg.id, message.chat.id)

            if file_data.get("auto_delete"):
                delete_time = file_data.get("auto_delete_time", config.AUTO_DELETE_TIME)
                info_msg = await msg.reply_text(
                    config.Messages.FILE_TEXT.format(
                        file_name=file_data.get("file_name", "Unknown"),
                        file_size=file_data.get("file_size", "Unknown"),
                        file_type=file_data.get("file_type", "Unknown"),
                        downloads=file_data.get("downloads", 0),
                        upload_time=datetime.fromtimestamp(
                            file_data.get("upload_time", datetime.now().timestamp())
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        uploader=file_data.get("uploader_username", "Anonymous"),
                        share_link=f"https://t.me/{config.BOT_USERNAME}?start={file_id}"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        config.Buttons.file_buttons(file_id)
                    ),
                    protect_content=config.PRIVACY_MODE
                )

                asyncio.create_task(
                    schedule_message_deletion(
                        client, 
                        file_id, 
                        message.chat.id, 
                        [msg.id, info_msg.id], 
                        delete_time
                    )
                )

        except Exception as e:
            await message.reply_text(
                f"❌ Error: {str(e)}", 
                protect_content=config.PRIVACY_MODE
            )
        return

    await message.reply_text(
        config.Messages.START_TEXT.format(
            bot_name=config.BOT_NAME,
            user_mention=message.from_user.mention
        ),
        reply_markup=InlineKeyboardMarkup(config.Buttons.start_buttons()),
        protect_content=config.PRIVACY_MODE
    )

@Client.on_message(filters.command("upload") & filters.private & filters.reply)
async def upload_command(client: Client, message: Message):
    if not await check_force_sub(client, message.from_user.id):
        await message.reply_text(
            "⚠️ Access Restricted\n\nPlease join our channel first and click 'Refresh' to continue.",
            reply_markup=InlineKeyboardMarkup(get_force_sub_buttons()),
            protect_content=config.PRIVACY_MODE
        )
        return

    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply_text(
            "❌ Only admins can upload files.",
            protect_content=config.PRIVACY_MODE
        )
        return

    file_message = message.reply_to_message
    file_type = None
    for type_ in config.SUPPORTED_TYPES:
        if getattr(file_message, type_, None):
            file_type = type_
            break
    
    if not file_type:
        await message.reply_text(
            "❌ Please reply to a supported file type:\n" + 
            ", ".join(config.SUPPORTED_TYPES),
            protect_content=config.PRIVACY_MODE
        )
        return

    file_size = getattr(getattr(file_message, file_type), 'file_size', 0)
    if file_size > config.MAX_FILE_SIZE:
        await message.reply_text(
            f"❌ File size too large. Maximum allowed size is {config.MAX_FILE_SIZE/(1024*1024)}MB",
            protect_content=config.PRIVACY_MODE
        )
        return

    file_uuid = await db.save_file(file_message, message.from_user.id)
    
    await message.reply_text(
        f"✅ **File Successfully Uploaded!**\n\n"
        f"🔗 **Share Link:** `https://t.me/{config.BOT_USERNAME}?start={file_uuid}`\n\n"
        f"⚡ Share this link with others to let them download the file.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔗 Share Link",
                url=f"https://t.me/share/url?url=https://t.me/{config.BOT_USERNAME}?start={file_uuid}"
            )]
        ]),
        protect_content=config.PRIVACY_MODE
    )

@Client.on_message(filters.command("batch_upload") & filters.private & filters.reply)
async def batch_upload_command(client: Client, message: Message):
    if not await check_force_sub(client, message.from_user.id):
        await message.reply_text(
            "⚠️ Access Restricted\n\nPlease join our channel first and click 'Refresh' to continue.",
            reply_markup=InlineKeyboardMarkup(get_force_sub_buttons()),
            protect_content=config.PRIVACY_MODE
        )
        return

    if not message.reply_to_message or not message.reply_to_message.media_group_id:
        await message.reply_text(
            "❌ Please reply to an album (grouped files) to upload as a batch.",
            protect_content=config.PRIVACY_MODE
        )
        return

    media_group_id = message.reply_to_message.media_group_id
    media_messages = await client.get_media_group(message.chat.id, media_group_id)

    if not media_messages:
        await message.reply_text(
            "❌ No files found in the media group.",
            protect_content=config.PRIVACY_MODE
        )
        return

    batch_uuid = await db.save_batch(media_messages, message.from_user.id)

    await message.reply_text(
        f"✅ **Batch Successfully Uploaded!**\n\n"
        f"🔗 **Download Link:** `https://t.me/{config.BOT_USERNAME}?start=batch_{batch_uuid}`\n\n"
        f"⚡ Share this link to download all files in this batch.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "📦 Download Batch",
                url=f"https://t.me/{config.BOT_USERNAME}?start=batch_{batch_uuid}"
            )]
        ]),
        protect_content=config.PRIVACY_MODE
    )

async def handle_batch_download(client: Client, message: Message, batch_uuid: str):
    batch_data = await db.get_batch(batch_uuid)
    
    if not batch_data:
        await message.reply_text(
            "❌ Batch not found or has been deleted!",
            protect_content=config.PRIVACY_MODE
        )
        return

    info_msg = await message.reply_text(
        f"📦 **Batch Download Started**\n"
        f"Total files: {len(batch_data['files'])}\n"
        f"Please wait while I send all files...",
        protect_content=config.PRIVACY_MODE
    )

    success_count = 0
    for file_data in batch_data["files"]:
        try:
            msg = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=config.DB_CHANNEL_ID,
                message_id=file_data["message_id"],
                protect_content=config.PRIVACY_MODE
            )
            
            await db.increment_downloads(file_data["file_uuid"])
            await db.update_file_message_id(
                file_data["file_uuid"],
                msg.id,
                message.chat.id
            )
            
            success_count += 1
            await asyncio.sleep(1)
            
        except Exception as e:
            await message.reply_text(
                f"❌ Error sending file: {str(e)}",
                protect_content=config.PRIVACY_MODE
            )

    await info_msg.edit_text(
        f"📦 **Batch Download Completed**\n"
        f"Successfully sent: {success_count}/{len(batch_data['files'])} files",
        protect_content=config.PRIVACY_MODE
    )
