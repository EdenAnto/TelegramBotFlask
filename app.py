import os
import json
import requests
import time
import asyncio
from flask import Flask, request
from telegram import Update, Message, Bot
from telegram.ext import ApplicationBuilder
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Flask app initialization
app = Flask(__name__)

# Enable logging
logging.basicConfig(level=logging.DEBUG)

# Environment variables
connection_string = os.getenv('AZ_CSTRING')
bot_api = os.getenv('TELEGRAM_BOT_API')

# Azure Blob Storage setup
container_name = "media-gallery"
blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Telegram Bot instance
bot = Bot(token=bot_api)

# Build application with an increased connection pool
application = ApplicationBuilder().token(bot_api).connection_pool_size(16).pool_timeout(60).build()

# Dictionary to store the time of the last message for each user
user_last_message_time = {}
response_timeout = 5  # Time in seconds to wait before responding

# Function to upload media to Azure Blob Storage
async def upload_to_azure(file_url, file_name):
    try:
        file_data = requests.get(file_url).content
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=file_name)
        blob_client.upload_blob(file_data, overwrite=True)
        print(f"Uploaded {file_name} to Azure Blob Storage!")
    except Exception as e:
        print(f"Error uploading {file_name} to Azure: {str(e)}")

# Function to handle /start command
async def handle_start(chat_id):
    try:
        print("Sending message 1...")
        await bot.send_message(chat_id=chat_id, text="איזה כיף שהתחברת!🥰")
        print("Message 1 sent.")
        await asyncio.sleep(1)  # Add delay to avoid spamming the connection pool
        await bot.send_message(chat_id=chat_id, text="ניתן לשלוח תמונות וסרטונים לשיתוף בגלריה")
        print("Message 2 sent.")
    except Exception as e:
        print(f"Error in handle_start: {str(e)}")

# Function to handle media (photos or videos)
async def handle_media(chat_id, message: Message):
    try:
        user_id = message.from_user.id
        current_time = time.time()

        # Throttling logic
        if user_id in user_last_message_time:
            time_difference = current_time - user_last_message_time[user_id]
        else:
            time_difference = response_timeout

        if time_difference >= response_timeout:
            # Process photos
            if message.photo:
                file = await bot.get_file(message.photo[-1].file_id)
                file_url = file.file_path
                file_name = f"wedding_{user_id}_{file.file_id}.jpg"
            # Process videos
            elif message.video:
                file = await bot.get_file(message.video.file_id)
                file_url = file.file_path
                file_name = f"wedding_{user_id}_{file.file_id}.mp4"
            else:
                await bot.send_message(chat_id=chat_id, text="Please send a photo or video!")
                return

            # Upload to Azure
            await upload_to_azure(file_url, file_name)

            # Respond to user
            await bot.send_message(chat_id=chat_id, text="תודה על השיתוף!")
            await asyncio.sleep(1)
            await bot.send_message(chat_id=chat_id, text="ניתן לצפות בגלריה המלאה בקישור הבא")
            await asyncio.sleep(1)
            await bot.send_message(chat_id=chat_id, text="https://en-wedding.vercel.app/")
            await bot.send_message(chat_id=chat_id, text="Nessya💍Eden")

            # Update last message time
            user_last_message_time[user_id] = current_time
    except Exception as e:
        print(f"Error in handle_media: {str(e)}")

# Flask route to handle Telegram webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('utf-8')
        print("Incoming update JSON:", json_str)  # Log the incoming update
        
        update = json.loads(json_str)

        # Extract chat ID and message
        message = update.get("message")
        if not message:
            print("No message in the update.")
            return 'OK', 200

        chat_id = message["chat"]["id"]
        text = message.get("text")

        # Determine action based on message content
        if text and text.startswith("/start"):
            print("Handling /start command")
            asyncio.run(handle_start(chat_id))
        elif "photo" in message or "video" in message:
            print("Handling media")
            asyncio.run(handle_media(chat_id, Message.de_json(message, bot)))
        else:
            print("Unknown message type")

        return 'OK', 200
    except Exception as e:
        print("Error processing webhook:", str(e))
        return 'Internal Server Error', 500

# Function to set the Telegram webhook
def set_webhook():
    webhook_url = f"https://{os.getenv('WEBSITE_HOSTNAME')}/webhook"
    response = bot.set_webhook(url=webhook_url)
    print(f"Webhook set to: {webhook_url} -> {response}")

# Main function
def main():
    try:
        # Set the webhook
        set_webhook()

        # Use dynamic port for Flask in Azure
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"Error in main function: {str(e)}")

if __name__ == '__main__':
    main()
