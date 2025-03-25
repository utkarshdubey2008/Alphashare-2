from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from database import Database
from datetime import datetime
import config
import asyncio
from handlers.utils.message_delete import schedule_message_deletion

db = Database()

async def check_force_sub(client: Client, user_id: int) -> bool:
    """Check if user is subscribed to all force subscription channels"""
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

def get_force_sub_buttons():
    """Generate force subscription buttons"""
    buttons = []
    for channel_id in config.FORCE_SUB_CHANNELS:
        if channel_id in config.FORCE_SUB_LINKS:
            buttons.append([
                InlineKeyboardButton("🔔 Join Channel", url=config.FORCE_SUB_LINKS[channel_id])
            ])
    buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="check_subscription")])
    return buttons

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle the /start command"""
    # Add user to database
    await db.add_user(message.from_user.id, message.from_user.username)

    # Check force subscription
    if not await check_force_sub(client, message.from_user.id):
        await message.reply_text(
            config.Messages.FORCE_SUB_TEXT,
            reply_markup=InlineKeyboardMarkup(get_force_sub_buttons()),
            protect_content=config.PRIVACY_MODE
        )
        return

    # Handle file sharing via start parameter
    if len(message.command) > 1:
        file_uuid = message.command[1]
        
        # Handle batch downloads
        if file_uuid.startswith("batch_"):
            await handle_batch_download(client, message, file_uuid.split("_")[1])
            return
            
        # Handle single file downloads
        file_data = await db.get_file(file_uuid)
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

            await db.increment_downloads(file_uuid)
            await db.update_file_message_id(file_uuid, msg.id, message.chat.id)

            # Handle auto-deletion
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
                        share_link=f"https://t.me/{config.BOT_USERNAME}?start={file_uuid}"
                    ),
                    reply_markup=InlineKeyboardMarkup(
                        config.Buttons.file_buttons(file_uuid)
                    ),
                    protect_content=config.PRIVACY_MODE
                )

                asyncio.create_task(
                    schedule_message_deletion(
                        client, 
                        file_uuid, 
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

    # Show start message
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
    """Handle the /upload command"""
    # Check force subscription
    if not await check_force_sub(client, message.from_user.id):
        await message.reply_text(
            config.Messages.FORCE_SUB_TEXT,
            reply_markup=InlineKeyboardMarkup(get_force_sub_buttons()),
            protect_content=config.PRIVACY_MODE
        )
        return

    # Check if user is admin
    if message.from_user.id not in config.ADMIN_IDS:
        await message.reply_text(
            "❌ Sorry, only admins can upload files.",
            protect_content=config.PRIVACY_MODE
        )
        return

    file_message = message.reply_to_message
    
    # Validate file type
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

    # Check file size
    file_size = getattr(getattr(file_message, file_type), 'file_size', 0)
    if file_size > config.MAX_FILE_SIZE:
        await message.reply_text(
            f"❌ File size too large. Maximum allowed size is {config.MAX_FILE_SIZE/(1024*1024)}MB",
            protect_content=config.PRIVACY_MODE
        )
        return

    # Save file
    file_uuid = await db.save_file(file_message, message.from_user.id)
    
    await message.reply_text(
        f"✅ **File Successfully Uploaded!**\n\n"
        f"🔗 **Download Link:** `https://t.me/{config.BOT_USERNAME}?start={file_uuid}`\n\n"
        f"⚡ Share this link with others to let them download the file.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔗 Download File", 
                url=f"https://t.me/{config.BOT_USERNAME}?start={file_uuid}"
            )]
        ]),
        protect_content=config.PRIVACY_MODE
    )

async def handle_batch_download(client: Client, message: Message, batch_uuid: str):
    """Handle batch file downloads"""
    batch_data = await db.get_batch(batch_uuid)
    
    if not batch_data:
        await message.reply_text(
            "❌ Batch not found or has been deleted!",
            protect_content=config.PRIVACY_MODE
        )
        return

    # Send batch info message
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
            
            # Add delay between messages to prevent flooding
            await asyncio.sleep(1)
            
        except Exception as e:
            await message.reply_text(
                f"❌ Error sending file: {str(e)}",
                protect_content=config.PRIVACY_MODE
            )

    # Update info message with final status
    await info_msg.edit_text(
        f"📦 **Batch Download Completed**\n"
        f"Successfully sent: {success_count}/{len(batch_data['files'])} files",
        protect_content=config.PRIVACY_MODE
        )
