# ==========================================================
# Copyright (c) 2026 Avisha Music
# All Rights Reserved.
# ==========================================================
import aiohttp
from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

from Elevenyts import userbot, config, logger

GEMINI_API_KEY = config.GEMINI_API_KEY
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Conversation history per chat
chat_history = {}


async def ask_gemini(chat_id: int, user_name: str, user_message: str) -> str:
    """Send message to Gemini API and get reply."""
    if not GEMINI_API_KEY:
        return None

    # History maintain karo context ke liye
    if chat_id not in chat_history:
        chat_history[chat_id] = []

    chat_history[chat_id].append({
        "role": "user",
        "parts": [{"text": f"{user_name}: {user_message}"}]
    })

    # Max 10 messages history rakho
    if len(chat_history[chat_id]) > 10:
        chat_history[chat_id] = chat_history[chat_id][-10:]

    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "Tu ek friendly music bot assistant hai jiska naam 'Avisha' hai. "
                    "Tu Telegram group mein logon se Hindi aur English dono mein baat karta hai. "
                    "Tu music ke baare mein expert hai. "
                    "Short aur friendly replies de. "
                    "Kabhi bhi offensive mat bol."
                )
            }]
        },
        "contents": chat_history[chat_id]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"]

                # Assistant ka reply bhi history mein save karo
                chat_history[chat_id].append({
                    "role": "model",
                    "parts": [{"text": reply}]
                })

                return reply
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


async def is_song_playing(chat_id: int) -> bool:
    """Check if song is currently playing in this group."""
    try:
        from Elevenyts.core.mongo import db
        assistant_num = db.assistant.get(chat_id)
        return assistant_num is not None
    except:
        return False


def get_assistant_two():
    """Get assistant 2 client."""
    if hasattr(userbot, 'two') and userbot.two in userbot.clients:
        return userbot.two
    return None


# Assistant 2 ke saath chatbot — sirf tab jab song play ho
if hasattr(userbot, 'two'):
    @userbot.two.on_message(filters.group & filters.text & ~filters.bot & ~filters.command(["play", "skip", "stop", "pause", "resume", "queue"]))
    async def chatbot_reply(client, message: Message):
        """Assistant 2 group mein AI chatbot ki tarah reply karega."""
        try:
            chat_id = message.chat.id

            # Bot messages ko ignore karo
            if message.from_user and message.from_user.is_bot:
                return

            user_name = message.from_user.first_name if message.from_user else "User"
            user_text = message.text.strip()

            # Chote messages ignore karo (1-2 words)
            if len(user_text.split()) < 2:
                return

            # Gemini se reply lo
            reply = await ask_gemini(chat_id, user_name, user_text)

            if reply:
                await message.reply_text(
                    f"🤖 {reply}",
                    parse_mode=ParseMode.HTML
                )

        except Exception as e:
            logger.error(f"Chatbot error in {message.chat.id}: {e}")
