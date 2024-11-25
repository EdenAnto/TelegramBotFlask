import os
import json
import aiohttp
import asyncio
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from azure.storage.blob.aio import BlobServiceClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment variables
connection_string = os.getenv('AZ_CSTRING')
bot_api = os.getenv('TELEGRAM_BOT_API')

# Azure Blob Storage setup
container_name = "media-gallery"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Telegram Bot application
application = Application.builder().token(bot_api).build()

# FastAPI application
app = FastAPI()

# Dictionary to store the time of the last message for each user
user_last_message_time = {}
response_timeout = 5  # Time in seconds to wait before responding

# Function to upload media to Azure Blob Storage
async def upload_to_azure(file_url, file_name):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as response:
            file_data = await response.read()
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
            await blob_client.upload_blob(file_data)
            print(f"Uploaded {file_name} to Azure Blob Storage!")

# Start command to welcome the user
async def start(update: Update, context):
    await update.message.reply_text("איזה כיף שהתחברת!🥰")
    await update.message.reply_text("ניתן לשלוח תמונות וסרטונים לשיתוף בגלריה")

# Handle media (images, videos, or other files)
async def handle_media(update: Update, context):
    sender_id = update.message.from_user.id
    current_time = asyncio.get_event_loop().time()

    if sender_id in user_last_message_time:
        time_difference = current_time - user_last_message_time[sender_id]
    else:
        time_difference = response_timeout

    if time_difference >= response_timeout:
        if update.message.photo:
            file = await update.message.photo[-1].get_file()
            file_extension = "jpg"
        elif update.message.video:
            file = await update.message.video.get_file()
            file_extension = "mp4"
        else:
            await update.message.reply_text("Please send a photo or video!")
            return

        file_url = file.file_path
        file_name = f"wedding_{update.message.from_user.id}_{file.file_id}.{file_extension}"

        await upload_to_azure(file_url, file_name)

        await update.message.reply_text("תודה על השיתוף!")
        await update.message.reply_text("ניתן לצפות בגלריה המלאה בקישור הבא")
        await update.message.reply_text("https://en-wedding.vercel.app/")
        await update.message.reply_text("Nessya💍Eden")

    user_last_message_time[sender_id] = current_time

# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    try:
        json_str = await request.body()
        update = Update.de_json(json.loads(json_str), application.bot)
        await application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing update: {str(e)}")
        return {"status": "error", "message": str(e)}

# Set the webhook URL
async def set_webhook():
    webhook_url = f"https://{os.getenv('MY_WEBSITE_HOSTNAME')}/webhook"  # Replace with your actual webhook URL
    await application.bot.set_webhook(webhook_url)
    print(f"Webhook successfully set to: {webhook_url}")

# Add command and message handlers
def add_handlers():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

# Initialize the bot and set the webhook
async def initialize_bot():
    add_handlers()
    await application.initialize()
    await set_webhook()
    print("Bot is ready!")

# Initialize the bot when the server starts
@app.on_event("startup")
async def on_startup():
    await initialize_bot()
