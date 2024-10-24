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



def callback(message):
    data = json.loads(message.data.decode('utf-8'))
    cp.info(f"Received notification: {data}")
    
    if 'historyId' in data:
        # Fetch the latest changes
        gmail_service = get_gmail_service()
        users = gmail_service.users()
        userId='admin@romainjouin.altostrat.com'
        startHistoryId=data['historyId']
        history = users.messages().get(userId=userId,)
        cp.warn(f"history : {history}")
        # ********************************************************************************************************************************
        for history_item in history.get('history', []):
            for message_added in history_item.get('messagesAdded', []):
                cp.warn("-"*40)
                try:
                    msg_id = message_added['message']['id']
                    cp.warn(f"Message ID: {msg_id}")
                    # Fetch the full message
                    messages = users.messages()
                    msg = messages.get(userId='admin@romainjouin.altostrat.com', id=msg_id).execute()
                    
                    # Extract and cp.warn email details
                    headers = msg['payload']['headers']
                    subject = next(header['value'] for header in headers if header['name'].lower() == 'subject')
                    sender = next(header['value'] for header in headers if header['name'].lower() == 'from')
                    recipient = next(header['value'] for header in headers if header['name'].lower() == 'to')
                    
                    cp.warn(f"New email received:")
                    cp.warn(f"From: {sender}")
                    cp.warn(f"To: {recipient}")
                    cp.warn(f"Subject: {subject}")
                    # Get the email body
                    if 'parts' in msg['payload']:
                        parts = msg['payload']['parts']
                        data = parts[0]['body']['data']
                        text = base64.urlsafe_b64decode(data).decode()
                        cp.warn(f"Body: {text[:100]}...")  # cp.warn first 100 characters
                    
                    # Check for attachments
                    if 'parts' in msg['payload']:
                        for part in msg['payload']['parts']:
                            if part.get('filename'):
                                cp.warn(f"Attachment: {part['filename']}")
                except Exception as e:
                    cp.warn(f"Error: {e}")
        cp.warn("done")

    message.ack()

with pubsub_v1.SubscriberClient() as subscriber:
    try:
        subscriber.create_subscription(name=subscription_name, topic=topic_name)
        cp.warn(f"Subscription {subscription_name} created.")
    except exceptions.AlreadyExists:
        cp.warn(f"Subscription {subscription_name} already exists.")

    future = subscriber.subscribe(subscription_name, callback)
    cp.warn(f"Listening for messages on {subscription_name}...")

    try:
        future.result()  # Block until the future completes
    except KeyboardInterrupt:
        future.cancel()  # Cancel the future if the user interrupts the program


