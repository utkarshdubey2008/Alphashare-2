from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import math
from typing import Union, Optional

def get_size_formatted(size: Union[int, float]) -> str:
    """
    Convert file size to human-readable format
    
    Args:
        size: File size in bytes
        
    Returns:
        str: Formatted size string (e.g., "1.23 MB")
    """
    if not isinstance(size, (int, float)):
        return "0 B"
    
    size = float(size)
    units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']
    
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'B':
                return f"{int(size)} {unit}"
            return f"{size:.2f} {unit}"
        size /= 1024

def time_formatter(seconds: float) -> str:
    """
    Convert seconds to human readable time format
    
    Args:
        seconds: Time in seconds
        
    Returns:
        str: Formatted time string (e.g., "2 hours 30 minutes")
    """
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    time_parts = []
    
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if seconds > 0 or not time_parts:
        time_parts.append(f"{seconds}s")
    
    return " ".join(time_parts)

class ButtonManager:
    """Class to manage various button layouts for the bot"""
    
    @staticmethod
    def help_button() -> InlineKeyboardMarkup:
        """Generate help button"""
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("Help", callback_data="help")]]
        )
    
    @staticmethod
    def batch_buttons(batch_id: str, share_link: Optional[str] = None) -> InlineKeyboardMarkup:
        """Generate buttons for batch messages"""
        buttons = []
        
        if share_link:
            buttons.append([InlineKeyboardButton("🔗 Share Link", url=share_link)])
        
        buttons.append([InlineKeyboardButton("🗑 Delete Batch", callback_data=f"delete_batch_{batch_id}")])
        
        return InlineKeyboardMarkup(buttons)
    
    @staticmethod
    def file_buttons(file_id: str, share_link: Optional[str] = None) -> InlineKeyboardMarkup:
        """Generate buttons for file messages"""
        buttons = []
        
        if share_link:
            buttons.append([InlineKeyboardButton("🔗 Share Link", url=share_link)])
        
        buttons.extend([
            [InlineKeyboardButton("⬇️ Download", callback_data=f"download_{file_id}")],
            [InlineKeyboardButton("❌ Close", callback_data="close")]
        ])
        
        return InlineKeyboardMarkup(buttons)
