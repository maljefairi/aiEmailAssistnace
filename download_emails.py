import imaplib
import email
import configparser
import json
from email.header import decode_header
import ssl
import os

# Constants
CONFIG_FILE = 'config.ini'
EMAIL_FILE = 'emails.json'

# Read the configuration file
config = configparser.ConfigParser(interpolation=None)
config.read(CONFIG_FILE)

EMAIL = config['credentials']['email']
PASSWORD = config['credentials']['password']
IMAP_SERVER = config['server']['IMAP_SERVER']
IMAP_PORT = int(config['server']['IMAP_PORT'])

def connect_to_mailbox():
    context = ssl.create_default_context()
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT, ssl_context=context)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        return mail
    except imaplib.IMAP4.error:
        print("Authentication failed. Check your email and password in the config file.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def safe_decode(data):
    if isinstance(data, bytes):
        try:
            return data.decode()
        except UnicodeDecodeError:
            return data.decode('utf-8', 'replace')
    return data  # if it's already a string


def fetch_emails(last_email_id=None):
    mail = connect_to_mailbox()
    if not mail:
        return []

    status, messages = mail.search(None, "ALL")
    email_ids = messages[0].split(b' ')
    
    if last_email_id:
        start_index = email_ids.index(last_email_id) + 1
        email_ids = email_ids[start_index:]

    all_emails = []
    for e_id in email_ids:
        _, msg_data = mail.fetch(e_id, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                email_subject = decode_header(msg["Subject"])[0][0]
                email_subject = safe_decode(email_subject)
                email_from = decode_header(msg["From"])[0][0]
                email_from = safe_decode(email_from)
                payload = msg.get_payload(decode=True)
                body = safe_decode(payload) if payload else ''
                all_emails.append({
                    "from": email_from,
                    "subject": email_subject,
                    "body": body,
                    "id": e_id.decode()
                })
                print(f"Processed email ID: {e_id.decode()}")
                # Intermediate save
                save_to_json(all_emails, EMAIL_FILE)

    mail.close()
    mail.logout()
    return all_emails

def save_to_json(data, filename):
    with open(filename, 'w', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_existing_emails(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding="utf-8") as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    existing_emails = load_existing_emails(EMAIL_FILE)
    last_email_id = existing_emails[-1]['id'] if existing_emails else None
    
    new_emails = fetch_emails(last_email_id)

    all_emails = existing_emails + new_emails
    save_to_json(all_emails, EMAIL_FILE)
    print(f"Total emails saved: {len(all_emails)}")
