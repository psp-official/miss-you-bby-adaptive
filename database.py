# database.py
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB Connection String
MONGO_URI = os.getenv("MONGO_URI", "")

# Database & Collections
client = AsyncIOMotorClient(MONGO_URI)
db = client["autobet_db"]

# Collection Definitions
users_collection = db["users"]
keys_collection = db["keys"]
allowed_uids_collection = db["allowed_uids"]
ai_states_collection = db["ai_states"]
game_history_collection = db["game_history"]

# ==========================================
# 👤 User Data Functions
# ==========================================
async def get_user(user_id: int):
    """
    Get user document by Telegram user ID.
    """
    return await users_collection.find_one({"_id": user_id})

async def save_user_login(
    user_id: int, 
    phone: str, 
    site_user_id: str, 
    nickname: str, 
    balance: str, 
    login_time: str, 
    ai_mode: str
):
    """
    Save or update user login information.
    """
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {
            "phone": phone,
            "user_id": site_user_id,
            "nickname": nickname,
            "balance": balance,
            "last_login": login_time,
            "ai_mode": ai_mode
        }},
        upsert=True
    )

async def update_user_ai_mode(user_id: int, ai_mode: str):
    """
    Update AI mode preference for a user.
    """
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"ai_mode": ai_mode}},
        upsert=True
    )

async def update_user_balance(user_id: int, balance: str):
    """
    Update user's real balance string.
    """
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"balance": balance}},
        upsert=True
    )

# ==========================================
# 🎮 Allowed Game UIDs (Whitelist)
# ==========================================
async def add_allowed_uid(uid: str):
    """
    Add a user ID to the whitelist.
    """
    await allowed_uids_collection.update_one(
        {"uid": uid}, 
        {"$set": {"uid": uid}}, 
        upsert=True
    )

async def remove_allowed_uid(uid: str):
    """
    Remove a user ID from the whitelist.
    """
    await allowed_uids_collection.delete_one({"uid": uid})

async def is_uid_allowed(uid: str) -> bool:
    """
    Check if a user ID is whitelisted.
    """
    doc = await allowed_uids_collection.find_one({"uid": uid})
    return bool(doc)

# ==========================================
# 🔑 Auth & Subscription Functions
# ==========================================
async def create_key(key_str: str, duration: str):
    """
    Create a new subscription key.
    """
    await keys_collection.insert_one({"key": key_str, "duration": duration})

async def get_key(key_str: str):
    """
    Retrieve a subscription key document.
    """
    return await keys_collection.find_one({"key": key_str})

async def delete_key(key_str: str):
    """
    Delete a used subscription key.
    """
    await keys_collection.delete_one({"key": key_str})

async def update_user_subscription(user_id: int, expire_iso: str):
    """
    Update user's subscription expiry date (ISO format).
    """
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"expire_date": expire_iso}},
        upsert=True
    )

async def get_user_subscription(user_id: int):
    """
    Get user's subscription expiry date (ISO format) or None.
    """
    user = await get_user(user_id)
    if user and "expire_date" in user:
        return user["expire_date"]
    return None

# ==========================================
# 🧪 Virtual Mode Functions
# ==========================================
async def set_virtual_balance(user_id: int, balance: float):
    """
    Set initial virtual balance for a user.
    """
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"virtual_balance": balance}},
        upsert=True
    )

async def get_virtual_balance(user_id: int) -> float:
    """
    Get current virtual balance for a user.
    """
    user = await get_user(user_id)
    if user and "virtual_balance" in user:
        return user["virtual_balance"]
    return 0.0

async def update_virtual_balance(user_id: int, balance: float):
    """
    Update user's virtual balance.
    """
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"virtual_balance": balance}},
        upsert=True
    )

# ==========================================
# 🧠 AI State Functions (Persistent Model Accuracy)
# ==========================================
async def save_ai_state(user_id: int, model_name: str, state_data: dict):
    """
    Save AI model state (e.g., model accuracies) for a user.
    """
    await ai_states_collection.update_one(
        {"user_id": user_id, "model_name": model_name},
        {"$set": {"state_data": state_data}},
        upsert=True
    )

async def get_ai_state(user_id: int, model_name: str) -> dict:
    """
    Retrieve AI model state for a user.
    """
    doc = await ai_states_collection.find_one(
        {"user_id": user_id, "model_name": model_name}
    )
    if doc and "state_data" in doc:
        return doc["state_data"]
    return {}

# ==========================================
# 📈 Historical Game Data Functions (9000+ Records)
# ==========================================
async def save_game_record(
    site: str, 
    game_type: int, 
    issue: str, 
    number: int, 
    size: str
):
    """
    Save a single game result to the database.
    Used for storing 9000+ historical records.
    """
    await game_history_collection.update_one(
        {"site": site, "game_type": game_type, "issue": str(issue)},
        {"$set": {"number": number, "size": size}},
        upsert=True
    )

async def get_game_history(
    site: str, 
    game_type: int, 
    limit: int = 9000
):
    """
    Retrieve game history records from the database.
    Default limit is 9000 to support deep memory AI.
    """
    cursor = game_history_collection.find(
        {"site": site, "game_type": game_type}
    ).sort("issue", -1).limit(limit)
    
    docs = await cursor.to_list(length=limit)
    return docs

# ==========================================
# 🧹 Utility Functions (Optional)
# ==========================================
async def delete_old_history(site: str, game_type: int, keep_count: int = 9000):
    """
    Optional: Delete records older than keep_count to manage database size.
    """
    docs = await get_game_history(site, game_type, limit=keep_count + 1)
    if len(docs) > keep_count:
        oldest_issue = docs[-1]["issue"]
        await game_history_collection.delete_many({
            "site": site,
            "game_type": game_type,
            "issue": {"$lt": oldest_issue}
        })
