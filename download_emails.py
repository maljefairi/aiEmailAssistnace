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
        parsed_date = email.utils.parsedate_to_datetime(date_str)
        if parsed_date.tzinfo:  # If the datetime is offset-aware
            return parsed_date.astimezone(timezone.utc).replace(tzinfo=None)  # Convert to UTC and remove tzinfo
        return parsed_date
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
        # Return string as is if it's already a string
        return data


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

                try:
                    email_date = msg["Date"]
                    email_datetime = datetime.strptime(email_date, '%a, %d %b %Y %H:%M:%S %z')
                    if not max_timestamp or email_datetime.replace(tzinfo=None) > max_timestamp:
                        max_timestamp = email_datetime

                    payload = msg.get_payload(decode=True)
                    body = safe_decode(payload) if payload else ''

                    all_emails.append({
                        "from": email_from,
                        "subject": email_subject,
                        "body": body,
                        "date": email_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except ValueError:
                    print(f"Could not parse date for email ID: {e_id.decode()}")

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
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
    return None


if __name__ == "__main__":
    last_timestamp = load_timestamp(LAST_TIMESTAMP_FILE)
    new_emails, new_timestamp = fetch_emails(last_timestamp)
    if new_emails:
        save_to_json(new_emails, OUTPUT_FILE)
        save_timestamp(new_timestamp, LAST_TIMESTAMP_FILE)
        print(f"Processed {len(new_emails)} new emails.")
    else:
        print("No new emails since the last run.")
