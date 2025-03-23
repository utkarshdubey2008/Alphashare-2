from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import config
from typing import Dict, Any, Optional, List


class Database:
    
    
    async def add_batch(self, batch_data: dict):
        """Add a new batch upload to database"""
        try:
            return await self.batches.insert_one(batch_data)
        except Exception as e:
            print(f"Database Error (add_batch): {str(e)}")
            raise

    async def get_batch(self, batch_id: str):
        """Get batch upload information"""
        try:
            return await self.batches.find_one({
                "batch_id": batch_id,
                "is_active": True
            })
        except Exception as e:
            print(f"Database Error (get_batch): {str(e)}")
            raise

    async def delete_batch(self, batch_id: str):
        """Delete a batch upload"""
        try:
            return await self.batches.delete_one({"batch_id": batch_id})
        except Exception as e:
            print(f"Database Error (delete_batch): {str(e)}")
            raise

    async def list_admin_batches(self, admin_id: int):
        """List all batches created by an admin"""
        try:
            cursor = self.batches.find({
                "admin_id": admin_id,
                "is_active": True
            }).sort("created_at", -1)
            return await cursor.to_list(length=None)
        except Exception as e:
            print(f"Database Error (list_admin_batches): {str(e)}")
            raise:
            
    def __init__(self):
        self.client = AsyncIOMotorClient(config.MONGO_URI)
        self.db = self.client[config.DATABASE_NAME]
        self.files = self.db.files
        self.users = self.db.users
        print("Database Connected Successfully!")

    async def add_file(self, file_data: Dict[str, Any]) -> str:
        file_doc = {
            "file_id": file_data["file_id"],
            "file_name": file_data["file_name"],
            "file_size": file_data["file_size"],
            "file_type": file_data["file_type"],
            "uuid": file_data["uuid"],
            "uploader_id": file_data["uploader_id"],
            "message_id": file_data["message_id"],
            "downloads": 0,
            "auto_delete": file_data.get("auto_delete", False),
            "auto_delete_time": file_data.get("auto_delete_time", None),
            "uploaded_at": datetime.utcnow()
        }
        await self.files.insert_one(file_doc)
        return file_doc["uuid"]

    async def get_file(self, uuid: str) -> Optional[Dict[str, Any]]:
        return await self.files.find_one({"uuid": uuid})

    async def increment_downloads(self, uuid: str) -> None:
        await self.files.update_one(
            {"uuid": uuid},
            {
                "$inc": {"downloads": 1},
                "$set": {"last_download": datetime.utcnow()}
            }
        )

    async def set_file_autodelete(self, uuid: str, delete_time: int) -> bool:
        """Set auto-delete time for a file in minutes"""
        result = await self.files.update_one(
            {"uuid": uuid},
            {
                "$set": {
                    "auto_delete": True,
                    "auto_delete_time": delete_time,
                    "delete_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    async def get_autodelete_files(self) -> List[Dict[str, Any]]:
        """Get all files that have auto-delete enabled"""
        return await self.files.find({"auto_delete": True}).to_list(None)

    async def update_file_message_id(self, uuid: str, message_id: int, chat_id: int) -> None:
        """Update message ID and chat ID for a file after sending to user"""
        await self.files.update_one(
            {"uuid": uuid},
            {
                "$push": {
                    "active_messages": {
                        "chat_id": chat_id,
                        "message_id": message_id,
                        "sent_at": datetime.utcnow()
                    }
                }
            }
        )

    async def remove_file_message(self, uuid: str, chat_id: int, message_id: int) -> None:
        """Remove a message reference from active_messages without deleting the file"""
        await self.files.update_one(
            {"uuid": uuid},
            {
                "$pull": {
                    "active_messages": {
                        "chat_id": chat_id,
                        "message_id": message_id
                    }
                }
            }
        )

    async def get_stats(self) -> Dict[str, Any]:
        total_files = await self.files.count_documents({})
        total_users = await self.users.count_documents({})

        total_size = 0
        total_downloads = 0

        async for file in self.files.find({}):
            total_size += file.get("file_size", 0)
            total_downloads += file.get("downloads", 0)

        return {
            "total_files": total_files,
            "total_users": total_users,
            "total_size": total_size,
            "total_downloads": total_downloads,
            "active_autodelete_files": await self.files.count_documents({"auto_delete": True})
        }

    async def add_user(self, user_id: int, username: str = None) -> None:
        await self.users.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "username": username,
                    "joined_date": datetime.utcnow(),
                    "last_active": datetime.utcnow()
                }
            },
            upsert=True
        )

    async def get_all_users(self) -> List[Dict[str, Any]]:
        return await self.users.find({}).to_list(None)

    async def get_file_messages(self, uuid: str) -> List[Dict[str, Any]]:
        """Get all active messages for a file"""
        file = await self.get_file(uuid)
        if file:
            return file.get("active_messages", [])
        return []

    async def check_autodelete_status(self, uuid: str) -> Optional[Dict[str, Any]]:
        """Check if a file should be auto-deleted from user chats"""
        file = await self.get_file(uuid)
        if file and file.get("auto_delete"):
            delete_time = file.get("auto_delete_time", 0)
            sent_time = file.get("delete_at")
            if sent_time:
                time_diff = (datetime.utcnow() - sent_time).total_seconds() / 60
                if time_diff >= delete_time:
                    return {
                        "should_delete": True,
                        "messages": file.get("active_messages", [])
                    }
        return None
