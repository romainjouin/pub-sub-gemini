import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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

if __name__ == '__main__':
   service = get_gmail_service()
   print("Authentication successful!")
   email="admin@romainjouin.altostrat.com"
   watch_request = {
    'topicName': "projects/email-gemini-438712/topics/new-email",
    'labelIds': ['INBOX'],  # You can specify which labels to watch
    'labelFilterAction': 'INCLUDE'
}
   users = service.users()
   users.watch(userId="me", body=watch_request).execute()


