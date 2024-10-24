import os
import json
import base64
import pickle
from google.cloud import pubsub_v1
from google.api_core import exceptions
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import color_print as cp

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
MY_TOPIC_NAME = os.getenv('PUB_SUB_TOPIC')
MY_SUBSCRIPTION_NAME = os.getenv('PUB_SUB_SUBSCRIPTION')

topic_name = f'projects/{project_id}/topics/{MY_TOPIC_NAME}'
subscription_name = f'projects/{project_id}/subscriptions/{MY_SUBSCRIPTION_NAME}'

def get_gmail_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

gmail_service = get_gmail_service()

def process_message(msg):
    headers = msg['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
    recipient = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown recipient')
    
    cp.info(f"\nNew email received:")
    cp.info(f"From: {sender}")
    cp.info(f"To: {recipient}")
    cp.info(f"Subject: {subject}")
    
    if 'parts' in msg['payload']:
        parts = msg['payload']['parts']
        data = parts[0]['body'].get('data', '')
        if data:
            text = base64.urlsafe_b64decode(data).decode()
            cp.info(f"Body: {text[:100]}...")
        for part in parts:
            if part.get('filename'):
                cp.info(f"Attachment: {part['filename']}")
    elif 'body' in msg['payload']:
        data = msg['payload']['body'].get('data', '')
        if data:
            text = base64.urlsafe_b64decode(data).decode()
            cp.info(f"Body: {text[:100]}...")

def callback(message):
    cp.warn(f"Received notification: {message.data.decode('utf-8')}")
    
    data = json.loads(message.data.decode('utf-8'))
    if 'historyId' in data:
        userId = 'me'
        try:
            history_response = gmail_service.users().history().list(
                userId=userId,
                startHistoryId=data['historyId']
            ).execute()

            for history_item in history_response.get('history', []):
                for message_added in history_item.get('messagesAdded', []):
                    msg_id = message_added['message']['id']
                    try:
                        msg = gmail_service.users().messages().get(userId=userId, id=msg_id).execute()
                        process_message(msg)
                    except HttpError as error:
                        cp.error(f"An error occurred while fetching message {msg_id}: {error}")
            else:
                cp.error(f"No messages added in this history item")
        except HttpError as error:
            cp.error(f"An error occurred while fetching history: {error}")
    
    message.ack()

def main():
    with pubsub_v1.SubscriberClient() as subscriber:
        try:
            subscriber.create_subscription(name=subscription_name, topic=topic_name)
            cp.warn(f"Subscription {subscription_name} created.")
        except exceptions.AlreadyExists:
            cp.warn(f"Subscription {subscription_name} already exists.")

        future = subscriber.subscribe(subscription_name, callback)
        cp.warn(f"Listening for messages on {subscription_name}...")

        try:
            future.result()
        except KeyboardInterrupt:
            future.cancel()
        except Exception as e:
            cp.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()