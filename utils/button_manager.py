from typing import List, Union
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import config

class ButtonManager:
    def __init__(self):
        self.db_channel = config.DB_CHANNEL_ID

    async def check_force_sub(self, client, user_id: int) -> bool:
        channels = [
            config.FSUB_CHNL_ID,
            config.FSUB_CHNL_2_ID,
            config.FSUB_CHNL_3_ID,
            config.FSUB_CHNL_4_ID
        ]
        
        for channel in channels:
            if channel:  # Check if the channel ID is not empty
                try:
                    member = await client.get_chat_member(channel, user_id)
                    if member.status not in ["member", "administrator", "creator"]:
                        return False
                except:
                    return False
        return True

    def force_sub_button(self) -> InlineKeyboardMarkup:
        buttons = []
        channels = [
            (config.FSUB_CHNL_ID, config.FSUB_CHNL_LINK),
            (config.FSUB_CHNL_2_ID, config.FSUB_CHNL_2_LINK),
            (config.FSUB_CHNL_3_ID, config.FSUB_CHNL_3_LINK),
            (config.FSUB_CHNL_4_ID, config.FSUB_CHNL_4_LINK)
        ]
        
        for channel_id, channel_link in channels:
            if channel_id and channel_link:  # Check if both ID and link are not empty
                buttons.append([InlineKeyboardButton(text="Join Channel", url=channel_link)])
        
        return InlineKeyboardMarkup(buttons)

    async def show_start(self, client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            config.Messages.START_TEXT.format(
                bot_name=config.BOT_NAME,
                user_mention=callback_query.from_user.mention
            ),
            reply_markup=self.start_button()
        )

    async def show_help(self, client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            config.Messages.HELP_TEXT,
            reply_markup=self.help_button()
        )

    async def show_about(self, client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            config.Messages.ABOUT_TEXT.format(
                bot_name=config.BOT_NAME,
                version=config.BOT_VERSION
            ),
            reply_markup=self.about_button()
        )

    def start_button(self) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton("Help 📜", callback_data="help"),
                InlineKeyboardButton("About ℹ️", callback_data="about")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK),
                InlineKeyboardButton("Developer 👨‍💻", url=config.DEVELOPER_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    def help_button(self) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton("Home 🏠", callback_data="home"),
                InlineKeyboardButton("About ℹ️", callback_data="about")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    def about_button(self) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton("Home 🏠", callback_data="home"),
                InlineKeyboardButton("Help 📜", callback_data="help")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    def file_button(self, file_uuid: str) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton("Download 📥", callback_data=f"download_{file_uuid}"),
                InlineKeyboardButton("Share Link 🔗", callback_data=f"share_{file_uuid}")
            ]
        ]
        return InlineKeyboardMarkup(buttons)
