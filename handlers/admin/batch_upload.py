from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from uuid import uuid4
import os
import time
from database import Database
from config import Messages, ADMIN_IDS, DB_CHANNEL_ID

# Store batch upload sessions
admin_batch_sessions = {}

class BatchUploadSession:
    def __init__(self, admin_id: int):
        self.admin_id = admin_id
        self.files = []
        self.batch_id = str(uuid4())[:8]
        self.start_time = time.time()

def admin_check(func):
    """Decorator to check if user is an admin"""
    async def wrapper(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply_text("⚠️ This command is only for admins!")
            return
        return await func(client, message)
    return wrapper

@Client.on_message(filters.command("batch_upload") & filters.private)
@admin_check
async def start_batch_upload(client: Client, message: Message):
    """Start a new batch upload session (Admin Only)"""
    admin_id = message.from_user.id
    
    # Check if admin already has an active session
    if admin_id in admin_batch_sessions:
        await message.reply_text(
            "You already have an active batch upload session. "
            "Please finish it with /done_batch or cancel it with /cancel_batch first."
        )
        return
    
    # Create new session
    admin_batch_sessions[admin_id] = BatchUploadSession(admin_id)
    
    await message.reply_text(
        "🔰 **Admin Batch Upload Mode Started!**\n\n"
        "Send me the files you want to include in this batch.\n\n"
        "Commands:\n"
        "• /done_batch - Finish and generate link\n"
        "• /cancel_batch - Cancel current session\n\n"
        "Note: Session will automatically expire in 30 minutes."
    )

@Client.on_message(filters.command("done_batch") & filters.private)
@admin_check
async def finish_batch_upload(client: Client, message: Message):
    """Finish batch upload and generate link (Admin Only)"""
    admin_id = message.from_user.id
    
    if admin_id not in admin_batch_sessions:
        await message.reply_text(
            "No active batch upload session. Start one with /batch_upload"
        )
        return
    
    session = admin_batch_sessions[admin_id]
    
    if not session.files:
        await message.reply_text(
            "No files in current batch. Send some files first or cancel with /cancel_batch"
        )
        return
    
    try:
        # Store batch information in database
        db = Database()
        batch_data = {
            "batch_id": session.batch_id,
            "admin_id": admin_id,
            "files": session.files,
            "created_at": time.time(),
            "is_active": True
        }
        
        await db.add_batch(batch_data)
        
        # Generate batch link
        batch_link = f"https://t.me/{client.username}?start=batch_{session.batch_id}"
        
        # Create summary message
        summary = f"📦 **Admin Batch Upload Complete!**\n\n"
        summary += f"🆔 Batch ID: `{session.batch_id}`\n"
        summary += f"📄 Total Files: {len(session.files)}\n"
        summary += f"👤 Uploaded by: {message.from_user.mention}\n\n"
        summary += "**Files in this batch:**\n"
        
        for idx, file in enumerate(session.files, 1):
            summary += f"{idx}. {file['name']} ({file['size_formatted']})\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Access Files", url=batch_link)],
            [InlineKeyboardButton("🗑 Delete Batch", callback_data=f"delete_batch_{session.batch_id}")]
        ])
        
        await message.reply_text(summary, reply_markup=keyboard)
        
        # Clear session
        del admin_batch_sessions[admin_id]
        
    except Exception as e:
        await message.reply_text(f"❌ Error occurred: {str(e)}")
        del admin_batch_sessions[admin_id]

@Client.on_message(filters.command("cancel_batch") & filters.private)
@admin_check
async def cancel_batch_upload(client: Client, message: Message):
    """Cancel current batch upload session (Admin Only)"""
    admin_id = message.from_user.id
    
    if admin_id in admin_batch_sessions:
        del admin_batch_sessions[admin_id]
        await message.reply_text("✅ Batch upload session cancelled.")
    else:
        await message.reply_text("No active batch upload session.")

@Client.on_message(filters.private & filters.media & ~filters.command)
async def handle_batch_file(client: Client, message: Message):
    """Handle incoming files during batch upload (Admin Only)"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    if user_id not in admin_batch_sessions:
        return
    
    session = admin_batch_sessions[user_id]
    
    # Check session timeout (30 minutes)
    if time.time() - session.start_time > 1800:
        del admin_batch_sessions[user_id]
        await message.reply_text(
            "⏰ Batch upload session expired (30 minutes timeout).\n"
            "Start a new session with /batch_upload"
        )
        return
    
    try:
        # Forward file to database channel
        file_msg = await message.forward(DB_CHANNEL_ID)
        
        # Get file information
        file_info = {
            "file_id": file_msg.id,
            "name": getattr(message.document, "file_name", None) or 
                   f"{message.media.value}.{message.file_name.split('.')[-1]}",
            "size": message.file_size,
            "size_formatted": get_size_formatted(message.file_size),
            "mime_type": getattr(message.document, "mime_type", ""),
            "timestamp": time.time()
        }
        
        session.files.append(file_info)
        
        await message.reply_text(
            f"✅ File added to batch!\n"
            f"📄 Current batch size: {len(session.files)} files\n\n"
            f"Send more files or use /done_batch to finish"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Failed to process file: {str(e)}")

@Client.on_callback_query(filters.regex("^delete_batch_"))
async def delete_batch_callback(client: Client, callback_query):
    """Handle batch deletion (Admin Only)"""
    user_id = callback_query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await callback_query.answer("⚠️ Only admins can delete batches!", show_alert=True)
        return
    
    batch_id = callback_query.data.split("_")[2]
    
    try:
        db = Database()
        result = await db.delete_batch(batch_id)
        
        if result.deleted_count > 0:
            await callback_query.message.edit_text(
                f"✅ Batch {batch_id} has been deleted.",
                reply_markup=None
            )
        else:
            await callback_query.answer("❌ Batch not found!", show_alert=True)
    
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

def get_size_formatted(size_in_bytes):
    """Convert size in bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"
