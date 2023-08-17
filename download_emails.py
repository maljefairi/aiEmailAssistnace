import imaplib
import email
import configparser
import json
import os
from email.header import decode_header
import ssl
from datetime import datetime
from datetime import timezone

# Configurations
CONFIG_FILE = 'config.ini'
OUTPUT_FILE = 'emails.json'
LAST_TIMESTAMP_FILE = 'last_timestamp.txt'

# Load configurations
config = configparser.ConfigParser(interpolation=None)
config.read(CONFIG_FILE)
EMAIL = config['credentials']['email']
PASSWORD = config['credentials']['password']
IMAP_SERVER = config['server']['IMAP_SERVER']
IMAP_PORT = int(config['server']['IMAP_PORT'])

def parse_email_date(date_str):
    try:
        dt = email.utils.parsedate_to_datetime(date_str)
        # If the datetime object is aware, strip it of timezone info
        if dt.tzinfo:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception as e:
        print(f"Error parsing date: {e}")
        return None

def safe_decode(data):
    if isinstance(data, bytes):
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data.decode('latin1')
    else:
        return data  # If already a string

def fetch_emails(last_timestamp=None):
    context = ssl.create_default_context()
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context)
    mail.login(EMAIL, PASSWORD)
    mail.select("inbox")

    if last_timestamp:
        query = f"SINCE {last_timestamp.strftime('%d-%b-%Y')}"
        status, messages = mail.search(None, query)
    else:
        status, messages = mail.search(None, "ALL")

    email_ids = messages[0].split(b' ')
    all_emails = []
    max_timestamp = last_timestamp

    for e_id in email_ids:
        _, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                email_subject = safe_decode(decode_header(msg["Subject"])[0][0])
                email_from = safe_decode(decode_header(msg["From"])[0][0])

                email_date = parse_email_date(msg["Date"])
                if not max_timestamp or email_date > max_timestamp:
                    max_timestamp = email_date

                payload = msg.get_payload(decode=True)
                body = safe_decode(payload) if payload else ''

                all_emails.append({
                    "from": email_from,
                    "subject": email_subject,
                    "body": body,
                    "date": email_date.strftime('%Y-%m-%d %H:%M:%S')
                })

    mail.close()
    mail.logout()
    return all_emails, max_timestamp

def save_to_json(data, filename):
    with open(filename, 'w', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_timestamp(timestamp, filename):
    with open(filename, 'w') as f:
        f.write(timestamp.strftime('%Y-%m-%d %H:%M:%S'))

def load_timestamp(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            timestamp_str = f.read().strip()
            dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            # If the datetime object is aware, strip it of timezone info
            if dt.tzinfo:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
    return None

def load_from_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    last_timestamp = load_timestamp(LAST_TIMESTAMP_FILE)
    stored_emails = load_from_json(OUTPUT_FILE)
    new_emails, new_timestamp = fetch_emails(last_timestamp)
    if new_emails:
        combined_emails = stored_emails + new_emails
        save_to_json(combined_emails, OUTPUT_FILE)
        save_timestamp(new_timestamp, LAST_TIMESTAMP_FILE)
        print(f"Processed {len(new_emails)} new emails.")
    else:
        print("No new emails since the last run.")
