from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import base64

# Load credentials (make sure this is set up correctly)
creds = Credentials.from_authorized_user_file('token.pickle', ['https://www.googleapis.com/auth/gmail.readonly'])

# Build the Gmail service
gmail_service = build('gmail', 'v1', credentials=creds)

def callback(message):
    print(f"Received notification: {message.data.decode('utf-8')}")
    
    data = json.loads(message.data.decode('utf-8'))
    if 'historyId' in data:
        userId = 'me'  # 'me' refers to the authenticated user
        
        try:
            # Fetch the history
            history_response = gmail_service.users().history().list(
                userId=userId,
                startHistoryId=data['historyId']
            ).execute()

            # Process each history item
            for history_item in history_response.get('history', []):
                for message_added in history_item.get('messagesAdded', []):
                    msg_id = message_added['message']['id']
                    
                    # Fetch the full message
                    msg = gmail_service.users().messages().get(userId=userId, id=msg_id).execute()
                    
                    # Extract and print email details
                    headers = msg['payload']['headers']
                    subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No subject')
                    sender = next((header['value'] for header in headers if header['name'].lower() == 'from'), 'Unknown sender')
                    recipient = next((header['value'] for header in headers if header['name'].lower() == 'to'), 'Unknown recipient')
                    
                    print(f"\nNew email received:")
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
        
        except Exception as e:
            print(f"An error occurred: {e}")

    message.ack()