from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import base64
import datetime

import os
from google.cloud import pubsub_v1
from google.api_core import exceptions
import json
import base64
import pickle
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import color_print as cp
from googleapiclient.errors import HttpError

project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
MY_TOPIC_NAME = os.getenv('PUB_SUB_TOPIC')
MY_SUBSCRIPTION_NAME = os.getenv('PUB_SUB_SUBSCRIPTION')

topic_name = f'projects/{project_id}/topics/{MY_TOPIC_NAME}'
subscription_name = f'projects/{project_id}/subscriptions/{MY_SUBSCRIPTION_NAME}'



def get_gmail_service():
   creds = None
   # The file token.pickle stores the user's access and refresh tokens, and is
   # created automatically when the authorization flow completes for the first time.
   if os.path.exists('token.pickle'):
       with open('token.pickle', 'rb') as token:
           creds = pickle.load(token)
   # If there are no (valid) credentials available, let the user log in.
   if not creds or not creds.valid:
       if creds and creds.expired and creds.refresh_token:
           creds.refresh(Request())
       else:
           flow = InstalledAppFlow.from_client_secrets_file(
               'credentials.json', SCOPES)
           creds = flow.run_local_server(port=8080)  # Explicitly set the port
       # Save the credentials for the next run
       with open('token.pickle', 'wb') as token:
           pickle.dump(creds, token)

   service = build('gmail', 'v1', credentials=creds)
   return service



# Build the Gmail service
gmail_service = get_gmail_service()

def callback(message):
    cp.warn(f"Received notification: {message.data.decode('utf-8')}")
    
    data = json.loads(message.data.decode('utf-8'))
    userId = 'me'
    
    try:
        # First, try to fetch history
        if 'historyId' in data:
            cp.info(f"Fetching history from {data['historyId']}")
            history_response = gmail_service.users().history().list(
                userId=userId,
                startHistoryId=data['historyId']
            ).execute()

            for history_item in history_response.get('history', []):
                for message_added in history_item.get('messagesAdded', []):
                    msg_id = message_added['message']['id']
                    fetch_and_process_message(userId, msg_id)
        
        # If no messages were found in history, fetch recent messages
        if not history_response.get('history'):
            cp.info("No messages found in history. Fetching recent messages...")
            
            # Get messages from the last 5 minutes
            delay_historic = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
            
            query = f'after:{delay_historic.strftime("%Y/%m/%d %H:%M:%S")}'
            cp.info(f"Fetching messages after {delay_historic.strftime('%Y/%m/%d %H:%M:%S')}")
            messages_response = gmail_service.users().messages().list(
                userId=userId,
                q=query
            ).execute()

            messages = messages_response.get('messages', [])
            for message in messages:
                fetch_and_process_message(userId, message['id'])
        
    except HttpError as error:
        cp.info(f"An error occurred while fetching data: ")
        cp.error(f"{str(error)[:-200]}")
    
    

def fetch_and_process_message(userId, msg_id):
    try:
        msg = gmail_service.users().messages().get(userId=userId, id=msg_id).execute()
        process_message(msg)
        
    except HttpError as error:
        cp.info(f"An error occurred while fetching message ")
        cp.error(f"{msg_id}:")
        cp.error(f"{str(error)[:-200]}")

def process_message(msg):
    # Extract and print email details
    headers = msg['payload']['headers']
    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
    recipient = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown recipient')
    
    cp.info(f"\nNew email received:")
    print(f"From: {sender}")
    print(f"To: {recipient}")
    print(f"Subject: {subject}")
    
    # Get the email body
    if 'parts' in msg['payload']:
        parts = msg['payload']['parts']
        data = parts[0]['body'].get('data', '')
        if data:
            text = base64.urlsafe_b64decode(data).decode()
            print(f"Body: {text[:100]}...")  # Print first 100 characters
    elif 'body' in msg['payload']:
        data = msg['payload']['body'].get('data', '')
        if data:
            text = base64.urlsafe_b64decode(data).decode()
            print(f"Body: {text[:100]}...")  # Print first 100 characters
    
    # Check for attachments
    if 'parts' in msg['payload']:
        for part in msg['payload']['parts']:
            if part.get('filename'):
                print(f"Attachment: {part['filename']}")




with pubsub_v1.SubscriberClient() as subscriber:
    cp.error("STARTING")
    try:

        subscriber.create_subscription(name=subscription_name, topic=topic_name)
        cp.warn(f"Subscription {subscription_name} created.")
    except exceptions.AlreadyExists:
        cp.info(f"Subscription {subscription_name} already exists.")

    future = subscriber.subscribe(subscription_name, callback)
    cp.info(f"Listening for messages on {subscription_name}...")

    try:
        future.result()  # Block until the future completes
    except KeyboardInterrupt:
        future.cancel()  # Cancel the future if the user interrupts the program

