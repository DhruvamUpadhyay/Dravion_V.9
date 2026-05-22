import os.path
import datetime
import json
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/contacts.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

# We are assuming running from a:\Dravion_v.9 directory.
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

def get_service(api_name, api_version):
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Error reading token: {e}")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            print(f"⚠️ Google Token missing or expired. Please run 'python -c \"import Dravion_backend.skills.google_suite as g; g.authenticate_user()\"' or use the agent to login.")
            return None
            
    try:
        service = build(api_name, api_version, credentials=creds)
        return service
    except HttpError as err:
        print(err)
        return None

def authenticate_user():
    """
    Explicitly triggers the browser authentication flow.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        return "credentials.json missing. Please download it from Google Cloud Console and place it in the root folder."
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        return "Authentication successful. You can now use Google Workspace features."
    except Exception as e:
        return f"Authentication failed: {e}"

def get_recent_emails(max_results=5):
    """Fetch recent unread emails using Gmail API."""
    service = get_service('gmail', 'v1')
    if not service:
        return "I need a credentials.json file and to be authenticated to access your emails, boss."

    try:
        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return "You have no unread emails."

        email_list = []
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = "No Subject"
            sender = "Unknown"
            date = "Unknown Date"
            for h in headers:
                if h['name'] == 'Subject': subject = h['value']
                if h['name'] == 'From': sender = h['value']
                if h['name'] == 'Date': date = h['value']
            
            # Clean up sender
            if '<' in sender: sender = sender.split('<')[0].strip().replace('"', '')
            
            email_list.append(f"From: {sender}\nSubject: {subject}\nDate: {date}")

        return "\n---\n".join(email_list)
    except Exception as e:
        return f"Error reading emails: {e}"

def get_upcoming_calendar_events(max_results=5):
    """Fetch upcoming events from Google Calendar."""
    service = get_service('calendar', 'v3')
    if not service:
        return "I need a credentials.json file and to be authenticated to access your calendar, boss."

    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=max_results, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return "No upcoming events found."

        event_list = []
        for event in events:
            start_dt = event['start'].get('dateTime')
            start_date = event['start'].get('date')
            
            if start_dt:
                try:
                    dt = datetime.datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                    start_str = dt.strftime("%b %d at %I:%M %p")
                except Exception:
                    start_str = start_dt
            elif start_date:
                 try:
                     dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
                     start_str = dt.strftime("%b %d (All Day)")
                 except Exception:
                     start_str = start_date
            else:
                start_str = "Unknown time"

            summary = event.get('summary', 'Untitled Event')
            event_list.append(f"{summary} on {start_str}")

        return "\n".join(event_list)
    except Exception as e:
        error_str = str(e)
        if "accessNotConfigured" in error_str or "403" in error_str:
             return "Google Calendar API is not enabled. Please enable it in the Google Cloud Console."
        return f"Error reading calendar: {e}"

def send_email(to, subject, body):
    """Send an email using Gmail API."""
    service = get_service('gmail', 'v1')
    if not service:
        return "I need a credentials.json file and to be authenticated to send emails, boss."
    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_message = service.users().messages().send(userId="me", body=create_message).execute()
        return f"Email sent successfully to {to}."
    except Exception as e:
        return f"Error sending email: {e}"
