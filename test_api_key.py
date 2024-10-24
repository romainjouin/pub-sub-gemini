from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Load credentials from a file
creds = Credentials.from_authorized_user_file('path/to/token.json', ['https://www.googleapis.com/auth/gmail.readonly'])

# Create a service object
service = build('gmail', 'v1', credentials=creds)

# Use the service
results = service.users().labels().list(userId='me').execute()
labels = results.get('labels', [])

for label in labels:
    print(label['name'])
