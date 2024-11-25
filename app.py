import os
import json
import requests
import time
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from azure.storage.blob import BlobServiceClient
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask app initialization
app = Flask(__name__)

# Environment variables
connection_string = os.getenv('AZ_CSTRING')
bot_api = os.getenv('TELEGRAM_BOT_API')
webhook_host = os.getenv('MY_WEBSITE_HOSTNAME')

# Azure Blob Storage setup
container_name = "media-gallery"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Telegram Bot application
application = Application.builder().token(bot_api).build()

# Dictionary to store the time of the last message for each user
user_last_message_time = {}
response_timeout = 5  # Time in seconds to wait before responding

# Persistent asyncio event loop
event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)


# Function to upload media to Azure Blob Storage
async def upload_to_azure(file_url, file_name):
    file_data = requests.get(file_url).content
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
    blob_client.upload_blob(file_data)
    print(f"Uploaded {file_name} to Azure Blob Storage!")


# Start command to welcome the user
async def start(update: Update, context: CallbackContext):
    print("Sending welcome message...")
    await update.message.reply_text("איזה כיף שהתחברת!🥰")
    await update.message.reply_text("ניתן לשלוח תמונות וסרטונים לשיתוף בגלריה")
    print("Welcome message sent.")


# Handle media (images, videos, or other files)
async def handle_media(update: Update, context: CallbackContext):
    sender_id = update.message.from_user.id
    current_time = time.time()

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


# Flask route to handle Telegram webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('utf-8')
        print("Incoming update:", json_str)  # Log the incoming update

        update = Update.de_json(json.loads(json_str), application.bot)

        # Ensure the task runs on the correct event loop
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update), event_loop
        )
        future.result()  # Wait for the task to complete

        return 'OK', 200
    except Exception as e:
        print(f"Error processing update: {e}")
        return 'Internal Server Error', 500


# Asynchronous initialization function
async def initialize_bot():
    global application

    print("Initializing Telegram bot...")
    await application.initialize()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    # Set webhook
    if not webhook_host:
        raise RuntimeError("MY_WEBSITE_HOSTNAME environment variable is not set")
    webhook_url = f"https://{webhook_host}/webhook"
    print(f"Setting webhook to {webhook_url}...")
    result = await application.bot.set_webhook(webhook_url)
    if result:
        print(f"Webhook successfully set to: {webhook_url}")
    else:
        raise RuntimeError("Failed to set webhook")


# Start Flask server
def start_flask():
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=8080)


# Main entry point
if __name__ == '__main__':
    try:
        # Run bot initialization in the event loop
        event_loop.run_until_complete(initialize_bot())
        # Start Flask server
        start_flask()
    except Exception as e:
        print(f"Error: {e}")
        exit(1)
