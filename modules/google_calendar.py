import os.path
import datetime as dt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_events(uid):
    creds = None

    uid = str(uid)

    if os.path.exists('users/' + uid + '/token.json'):
        creds = Credentials.from_authorized_user_file('users/' + uid + '/token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'calendar_credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('users/' + uid + '/token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)

        now = dt.datetime.utcnow().isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', timeMin=now,
            maxResults=10, singleEvents=True,
            orderBy='startTime').execute()
        
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')

        events_string = ''

        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            events_string += f'{start} - {event["summary"]}\n'
            print(start, event['summary'])

        return events_string

    except HttpError as err:
        print(err)

