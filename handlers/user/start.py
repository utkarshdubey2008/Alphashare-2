from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
from utils import ButtonManager
import config
import asyncio
from utils.message_delete import schedule_message_deletion

db = Database()
button_manager = ButtonManager()

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await db.add_user(message.from_user.id, message.from_user.username)

    if len(message.command) > 1:
        file_uuid = message.command[1]

        if not await button_manager.check_force_sub(client, message.from_user.id):
            await message.reply_text(
                config.Messages.FORCE_SUB_TEXT,
                reply_markup=button_manager.force_sub_button(),
                protect_content=config.PRIVACY_MODE
            )
            return

        file_data = await db.get_file(file_uuid)
        if not file_data:
            await message.reply_text(
                "❌ File not found or has been deleted!",   
                protect_content=config.PRIVACY_MODE  
            )
            return

        try:
            if file_data["file_type"] == "video":
                msg = await client.send_video(
                    chat_id=message.chat.id,
                    video=file_data["file_path"],
                    caption=file_data["caption"],
                    protect_content=config.PRIVACY_MODE
                )
            else:
                msg = await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=config.DB_CHANNEL_ID,
                    message_id=file_data["message_id"],
                    protect_content=config.PRIVACY_MODE
                )

            await db.increment_downloads(file_uuid)
            await db.update_file_message_id(file_uuid, msg.id, message.chat.id)

            if file_data.get("auto_delete"):
                delete_time = file_data.get("auto_delete_time")
                if delete_time:
                    info_msg = await msg.reply_text(
                        f"⏳ This file will be automatically deleted in {delete_time} minutes\n"
                        f"💡 Save it to your saved messages before deletion!",
                        protect_content=config.PRIVACY_MODE
                    )
                    asyncio.create_task(schedule_message_deletion(
                        client, file_uuid, message.chat.id,
                        [msg.id, info_msg.id], delete_time
                    ))

        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}", protect_content=config.PRIVACY_MODE)
        return

    if len(message.command) > 1 and message.command[1].startswith("batch_"):
        batch_id = message.command[1].split("_")[1]

        try:
            batch_data = await db.get_batch(batch_id)

            if not batch_data:
                await message.reply_text("❌ Invalid batch link or batch has expired.")
                return

            text = f"📦 **Batch Files**\n\n"
            text += f"🆔 Batch ID: `{batch_id}`\n"
            text += f"📄 Total Files: {len(batch_data['files'])}\n\n"

            buttons = []
            for idx, file in enumerate(batch_data['files'], 1):
                text += f"{idx}. {file['name']} ({file['size_formatted']})\n"
                buttons.append([
                    InlineKeyboardButton(
                        f"📎 Download File {idx}",
                        url=f"https://t.me/{client.username}?start=file_{file['file_id']}"
                    )
                ])

            keyboard = InlineKeyboardMarkup(buttons)

            await message.reply_text(text, reply_markup=keyboard)

        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}")
        return

    await message.reply_text(
        config.Messages.START_TEXT.format(
            bot_name=config.BOT_NAME,
            user_mention=message.from_user.mention
        ),
        reply_markup=button_manager.start_button(),
        protect_content=config.PRIVACY_MODE
    )
