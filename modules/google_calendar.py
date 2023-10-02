import os.path
import datetime as dt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/calendar']

def check_auth(uid):
    creds = None

    uid = str(uid)

    if os.path.exists('users/' + uid + '/token.json'):
        creds = Credentials.from_authorized_user_file('users/' + uid + '/token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            return False     
    return True

def get_auth_url(uid):
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
            # generate a link to get the token
            auth_url, _ = flow.authorization_url(prompt='consent')


            return(format(auth_url))


def get_events(uid):
    creds = None

    uid = str(uid)

    if os.path.exists('users/' + uid + '/token.json'):
        creds = Credentials.from_authorized_user_file('users/' + uid + '/token.json', SCOPES)

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

def create_event(uid,event_object):
    creds = None

    uid = str(uid)

    if os.path.exists('users/' + uid + '/token.json'):
        creds = Credentials.from_authorized_user_file('users/' + uid + '/token.json', SCOPES)

    try:
        service = build('calendar', 'v3', credentials=creds)

        now = dt.datetime.utcnow().isoformat() + 'Z'

        event = service.events().insert(calendarId='primary', body=event_object).execute()

        print('Event created: %s' % (event.get('htmlLink')))
        return True
    
    except HttpError as err:
        print(err)
        return False
        


        