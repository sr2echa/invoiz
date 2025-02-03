import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from base64 import urlsafe_b64decode, urlsafe_b64encode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type
from dotenv import load_dotenv
load_dotenv()


SCOPES = ["https://mail.google.com/"]
our_email = os.getenv('DEV_EMAIL')


def gmail_authenticate():
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)

def search_messages(service, query, limit=5):
    result = service.users().messages().list(userId='me',q=query).execute()
    messages = []
    if 'messages' in result:
        messages.extend(result['messages'])
    while 'nextPageToken' in result and (limit is None or len(messages) < limit):
        page_token = result['nextPageToken']
        result = service.users().messages().list(userId='me',q=query, pageToken=page_token).execute()
        if 'messages' in result:
            messages.extend(result['messages'])
    return messages[:limit] if limit is not None else messages

def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"

def clean(text):
    return "".join(c if c.isalnum() else "_" for c in text)

def parse_parts(service, parts, folder_name, message, email_data):
    """
    Utility function that parses the content of an email partition and stores paths in email_data
    """
    if parts:
        for part in parts:
            filename = part.get("filename")
            mimeType = part.get("mimeType")
            body = part.get("body")
            data = body.get("data")
            file_size = body.get("size")
            part_headers = part.get("headers")
            if part.get("parts"):
                parse_parts(service, part.get("parts"), folder_name, message, email_data)
            if mimeType == "text/plain":
                if data:
                    text = urlsafe_b64decode(data).decode()
                    text_file = os.path.join(folder_name, "content.txt")
                    with open(text_file, "w") as f:
                        f.write(text)
                    email_data["content"]["text"].append(os.path.abspath(text_file))
            elif mimeType == "text/html":
                if not filename:
                    filename = "index.html"
                filepath = os.path.join(folder_name, filename)
                with open(filepath, "wb") as f:
                    f.write(urlsafe_b64decode(data))
                email_data["content"]["html"].append(os.path.abspath(filepath))
            else:
                for part_header in part_headers:
                    part_header_name = part_header.get("name")
                    part_header_value = part_header.get("value")
                    if part_header_name == "Content-Disposition":
                        if "attachment" in part_header_value:
                            attachment_id = body.get("attachmentId")
                            attachment = service.users().messages() \
                                        .attachments().get(id=attachment_id, userId='me', messageId=message['id']).execute()
                            data = attachment.get("data")
                            filepath = os.path.join(folder_name, filename)
                            if data:
                                with open(filepath, "wb") as f:
                                    f.write(urlsafe_b64decode(data))
                                email_data["content"]["attachments"].append({
                                    "filename": filename,
                                    "size": get_size_format(file_size),
                                    "path": os.path.abspath(filepath)
                                })


def read_message(service, message):
    """
    This function takes Gmail API `service` and the given `message_id` and does the following:
        - Downloads the content of the email
        - Stores email basic information (To, From, Subject & Date) and plain/text parts
        - Creates a folder for each email based on the subject inside /downloads directory
        - Downloads text/html content (if available) and saves it under the folder created as index.html
        - Downloads any file that is attached to the email and saves it in the folder created
        - Returns a dictionary containing all email information and absolute paths to downloaded content
    """
    email_data = {
        "metadata": {},
        "content": {
            "text": [],
            "html": [],
            "attachments": []
        }
    }
    msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
    payload = msg['payload']
    headers = payload.get("headers")
    parts = payload.get("parts")
    downloads_dir = "downloads"
    if not os.path.exists(downloads_dir):
        os.makedirs(downloads_dir)
    folder_name = os.path.join(downloads_dir, "email")
    has_subject = False
    if headers:
        for header in headers:
            name = header.get("name")
            value = header.get("value")
            if name.lower() == 'from':
                email_data["metadata"]["from"] = value
            if name.lower() == "to":
                email_data["metadata"]["to"] = value
            if name.lower() == "subject":
                has_subject = True
                email_data["metadata"]["subject"] = value
                folder_name = os.path.join(downloads_dir, clean(value))
                folder_counter = 0
                while os.path.isdir(folder_name):
                    folder_counter += 1
                    if folder_name[-1].isdigit() and folder_name[-2] == "_":
                        folder_name = f"{folder_name[:-2]}_{folder_counter}"
                    elif folder_name[-2:].isdigit() and folder_name[-3] == "_":
                        folder_name = f"{folder_name[:-3]}_{folder_counter}"
                    else:
                        folder_name = f"{folder_name}_{folder_counter}"
                os.mkdir(folder_name)
            if name.lower() == "date":
                email_data["metadata"]["date"] = value
    if not has_subject:
        if not os.path.isdir(folder_name):
            os.mkdir(folder_name)
    parse_parts(service, parts, folder_name, message, email_data)
    email_data["folder"] = os.path.abspath(folder_name)
    return email_data

def search_and_read(service, query, limit=5):
    messages = search_messages(service, query, limit)
    print("Total messages fetched: ", len(messages))
    emails_data = []
    if messages:
        for msg in messages:
            email_data = read_message(service, msg)
            emails_data.append(email_data)
    return emails_data


if __name__ == "__main__":
    service = gmail_authenticate()
    query = input("Enter your query: ")
    limit_input = input("Enter number of emails to fetch (press Enter for default 5, 'all' for no limit): ")
    limit = None if limit_input.lower() == 'all' else (int(limit_input) if limit_input.strip() else 5)
    emails_data = search_and_read(service, query, limit)
    print("\nEmail data dictionary:")
    for i, email in enumerate(emails_data, 1):
        print(f"\nEmail {i}:")
        print(f"From: {email['metadata'].get('from')}")
        print(f"Subject: {email['metadata'].get('subject')}")
        print(f"Folder: {email['folder']}")
        print(f"Text files: {email['content']['text']}")
        print(f"HTML files: {email['content']['html']}")
        print(f"Attachments: {len(email['content']['attachments'])} files")
        if email['content']['attachments']:
            print("Attachment details:")
            for attachment in email['content']['attachments']:
                print(f"  - {attachment['filename']} ({attachment['size']})")
                print(f"    Location: {attachment['path']}")
        print("="*50)