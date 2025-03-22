from typing import List, Union
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import config
import logging

class ButtonManager:
    def __init__(self):
        self.db_channel = config.DB_CHANNEL_ID

    async def check_force_sub(self, client, user_id: int) -> bool:
        # Define all possible channels with their names
        channel_configs = [
            (config.FSUB_CHNL_ID, "Main Channel"),
            (config.FSUB_CHNL_2_ID, "Second Channel"),
            (config.FSUB_CHNL_3_ID, "Third Channel"),
            (config.FSUB_CHNL_4_ID, "Fourth Channel")
        ]
        
        # Filter out empty channel configurations
        active_channels = [(id, name) for id, name in channel_configs if id]
        
        if not active_channels:  # If no channels are configured
            return True
        
        for channel_id, channel_name in active_channels:
            try:
                member = await client.get_chat_member(channel_id, user_id)
                logging.info(f"Checking {channel_name} ({channel_id}) for user {user_id} - Status: {member.status}")
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except Exception as e:
                logging.error(f"Error checking {channel_name} ({channel_id}): {str(e)}")
                if "USER_NOT_PARTICIPANT" in str(e):
                    return False
                continue  # Continue checking other channels if there's a different error
        return True

    def force_sub_button(self) -> InlineKeyboardMarkup:
        buttons = []
        # Check all possible channel configurations
        channel_configs = [
            (config.FSUB_CHNL_ID, config.FSUB_CHNL_LINK, "Main"),
            (config.FSUB_CHNL_2_ID, config.FSUB_CHNL_2_LINK, "Second"),
            (config.FSUB_CHNL_3_ID, config.FSUB_CHNL_3_LINK, "Third"),
            (config.FSUB_CHNL_4_ID, config.FSUB_CHNL_4_LINK, "Fourth")
        ]
        
        # Add buttons only for configured channels
        for channel_id, channel_link, channel_name in channel_configs:
            if channel_id and channel_link:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"Join {channel_name} Channel 📢", 
                        url=channel_link
                    )
                ])
        
        if buttons:  # Add a "Check Subscription" button if there are any channels
            buttons.append([
                InlineKeyboardButton(
                    text="🔄 Check Subscription",
                    callback_data="check_sub"
                )
            ])
        
        return InlineKeyboardMarkup(buttons)

    async def show_start(self, client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            config.Messages.START_TEXT.format(
                bot_name=config.BOT_NAME,
                user_mention=callback_query.from_user.mention
            ),
            reply_markup=self.start_button(),
            disable_web_page_preview=True
        )

    async def show_help(self, client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            config.Messages.HELP_TEXT,
            reply_markup=self.help_button(),
            disable_web_page_preview=True
        )

    async def show_about(self, client, callback_query: CallbackQuery):
        await callback_query.message.edit_text(
            config.Messages.ABOUT_TEXT.format(
                bot_name=config.BOT_NAME,
                version=config.BOT_VERSION
            ),
            reply_markup=self.about_button(),
            disable_web_page_preview=True
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
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)
