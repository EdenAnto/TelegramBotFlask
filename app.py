import os
import json
import requests
import time
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from azure.storage.blob import BlobServiceClient
import asyncio

# Flask app initialization
app = Flask(__name__)

# Environment variables
connection_string = os.getenv('AZ_CSTRING')
bot_api = os.getenv('TELEGRAM_BOT_API')

# Azure Blob Storage setup
container_name = "media-gallery"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Telegram Bot application
application = Application.builder().token(bot_api).build()

# Dictionary to store the time of the last message for each user
user_last_message_time = {}
response_timeout = 5  # Time in seconds to wait before responding

# Function to upload media to Azure Blob Storage
async def upload_to_azure(file_url, file_name):
    file_data = requests.get(file_url).content
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
    blob_client.upload_blob(file_data)
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

# Flask route to handle Telegram webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('utf-8')
        print("Incoming update:", json_str)  # Log the incoming update

        update = Update.de_json(json.loads(json_str), application.bot)

        # Process the update using asyncio.run for compatibility
        asyncio.run(application.process_update(update))

        return 'OK', 200
    except Exception as e:
        print("Error processing update:", str(e))
        return 'Internal Server Error', 500

# Set the webhook URL
async def set_webhook():
    # Adjust webhook URL dynamically for Azure
    webhook_url = f"https://{os.getenv('WEBSITE_HOSTNAME')}/webhook"
    await application.bot.set_webhook(webhook_url)
    print(f"Webhook successfully set to: {webhook_url}")

# Main function
def main():
    # Initialize the application
    asyncio.run(application.initialize())

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

    # Set the webhook
    asyncio.run(set_webhook())

    # Run the Flask app
    app.run(host='0.0.0.0', port=8080)

if __name__ == '__main__':
    main()
