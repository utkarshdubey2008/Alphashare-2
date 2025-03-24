from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_size_formatted(size: int) -> str:
    """Convert file size to human-readable format"""
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PiB"

class ButtonManager:
    @staticmethod
    def help_button():
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("Help", callback_data="help")]]
        )
