from typing import List, Union
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import config
import logging
from pyrogram.errors import UserNotParticipant, BadRequest
from datetime import datetime

class ButtonManager:
    def __init__(self):
        self.db_channel = config.DB_CHANNEL_ID
        self._init_channels()
        self.current_time = "2025-03-25 15:25:42"
        self.current_user = "alphabotz"

    def _init_channels(self):
        self.channel_configs = []
        
        for channel_id in config.FORCE_SUB_CHANNELS:
            if channel_id in config.FORCE_SUB_LINKS:
                try:
                    clean_id = str(channel_id).replace("-100", "")
                    int_id = int(clean_id)
                    final_id = f"-100{int_id}" if not str(int_id).startswith("-100") else str(int_id)
                    self.channel_configs.append((final_id, config.FORCE_SUB_LINKS[channel_id]))
                except (ValueError, TypeError):
                    logging.error(f"Invalid channel ID format: {channel_id}")

    async def check_force_sub(self, client, user_id: int) -> bool:
        if not self.channel_configs:
            return True

        for channel_id, _ in self.channel_configs:
            try:
                member = await client.get_chat_member(int(channel_id), user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except UserNotParticipant:
                return False
            except BadRequest as e:
                if "user not found" in str(e).lower():
                    return False
                logging.error(f"Channel check error: {str(e)}")
                continue
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                continue
        return True

    def force_sub_button(self, file_id=None) -> InlineKeyboardMarkup:
        buttons = []
        
        for _, channel_link in self.channel_configs:
            if channel_link:
                buttons.append([
                    InlineKeyboardButton(text="📢 Join Channel", url=channel_link)
                ])

        refresh_command = "start"
        if file_id:
            refresh_command += f" {file_id}"
            
        buttons.append([
            InlineKeyboardButton(
                "🔄 Refresh",
                url=f"https://t.me/{config.BOT_USERNAME}?{refresh_command}"
            )
        ])
        
        return InlineKeyboardMarkup(buttons)

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

    async def show_start(self, client, callback_query: CallbackQuery):
        try:
            is_subbed = await self.check_force_sub(client, callback_query.from_user.id)
            if is_subbed:
                await callback_query.message.edit_text(
                    config.Messages.START_TEXT.format(
                        bot_name=config.BOT_NAME,
                        user_mention=callback_query.from_user.mention
                    ),
                    reply_markup=self.start_button(),
                    disable_web_page_preview=True
                )
            else:
                await callback_query.message.edit_text(
                    "⚠️ Access Restricted\n\nPlease join our channel first and click 'Refresh' to continue.",
                    reply_markup=self.force_sub_button(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error in show_start: {str(e)}")

    async def show_help(self, client, callback_query: CallbackQuery):
        try:
            is_subbed = await self.check_force_sub(client, callback_query.from_user.id)
            if is_subbed:
                await callback_query.message.edit_text(
                    config.Messages.HELP_TEXT,
                    reply_markup=self.help_button(),
                    disable_web_page_preview=True
                )
            else:
                await callback_query.message.edit_text(
                    "⚠️ Access Restricted\n\nPlease join our channel first and click 'Refresh' to continue.",
                    reply_markup=self.force_sub_button(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error in show_help: {str(e)}")

    async def show_about(self, client, callback_query: CallbackQuery):
        try:
            is_subbed = await self.check_force_sub(client, callback_query.from_user.id)
            if is_subbed:
                await callback_query.message.edit_text(
                    config.Messages.ABOUT_TEXT.format(
                        bot_name=config.BOT_NAME,
                        version=config.BOT_VERSION,
                        current_time=self.current_time,
                        current_user=self.current_user
                    ),
                    reply_markup=self.about_button(),
                    disable_web_page_preview=True
                )
            else:
                await callback_query.message.edit_text(
                    "⚠️ Access Restricted\n\nPlease join our channel first and click 'Refresh' to continue.",
                    reply_markup=self.force_sub_button(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error in show_about: {str(e)}")
