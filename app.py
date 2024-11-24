import os
import json
import requests
import time
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from azure.storage.blob import BlobServiceClient
from apscheduler.schedulers.background import BackgroundScheduler

# Flask app initialization
app = Flask(__name__)

# Azure Blob Storage and Telegram bot setup
connection_string = os.getenv('AZ_CSTRING')
bot_api = os.getenv('TELEGRAM_BOT_API')
container_name = "media-gallery"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Dictionary to store the time of the last message for each user
user_last_message_time = {}
response_timeout = 5

# Telegram Bot application
application = Application.builder().token(bot_api).build()

# Function to upload media to Azure Blob Storage
async def upload_to_azure(file_url, file_name):
    file_data = requests.get(file_url).content
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
    blob_client.upload_blob(file_data, overwrite=True)
    print(f"Uploaded {file_name} to Azure Blob Storage!")

# Start command to welcome the user
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("איזה כיף שהתחברת!🥰")
    await update.message.reply_text("ניתן לשלוח תמונות וסרטונים לשיתוף בגלריה")

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

# Add Telegram bot handlers
def add_telegram_handlers():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

# Start polling in the background
def start_polling():
    print("Starting Telegram bot polling...")
    application.run_polling()

# Flask route
@app.route('/')
def index():
    return "Hello, Flask and Telegram bot are running!"

@app.route('/status', methods=['GET'])
def status():
    return {"status": "Running"}

# Main function
def main():
    # Add Telegram bot handlers
    add_telegram_handlers()

    # Start Telegram bot polling in a background thread
    scheduler = BackgroundScheduler()
    scheduler.add_job(start_polling, 'interval', seconds=1)
    scheduler.start()

    # Run Flask app
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    main()
