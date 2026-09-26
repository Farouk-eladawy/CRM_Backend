import os.path
import base64
import logging
import re
import json
import threading
import html as html_lib
import httplib2
import google_auth_httplib2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


_TRACKING_PAREN_URL_RE = re.compile(
    r"\s*\(\s*https?://(?:[\w.-]*sendgrid\.net|[\w.-]*getyourguide\.com|[\w.-]*viator\.com|[\w.-]*headout\.com)[^\s)]*\)",
    re.IGNORECASE,
)
_TRACKING_BARE_URL_RE = re.compile(
    r"https?://(?:u\d+\.ct\.sendgrid\.net|[\w.-]*\.ct\.sendgrid\.net)/ls/click\?[^\s)\]>\"']+",
    re.IGNORECASE,
)
_EMAIL_FOOTER_MARKERS = (
    "Become a Supply Partner",
    "GetYourGuide receives and processes replies",
    "GetYourGuide Deutschland GmbH",
    "This email was sent by GetYourGuide",
    "You are receiving this email because you are a GetYourGuide",
)


def clean_email_body_for_crm(text: str) -> str:
    """Normalize OTA/HTML-converted email bodies for CRM storage and display."""
    s = str(text or "")
    if not s.strip():
        return ""

    s = html_lib.unescape(s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _TRACKING_PAREN_URL_RE.sub("", s)
    s = _TRACKING_BARE_URL_RE.sub("", s)

    lower = s.lower()
    cut_at = None
    for marker in _EMAIL_FOOTER_MARKERS:
        idx = lower.find(marker.lower())
        if idx >= 80 and (cut_at is None or idx < cut_at):
            cut_at = idx
    if cut_at is not None:
        s = s[:cut_at]

    # Drop leading template junk (often a lone short digit/code from HTML conversion)
    s = re.sub(r"^(?:\s*\d{1,4}\s*\n)+", "", s)
    s = re.sub(r"[ \t]+\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import HttpRequest

#region debug-point gmail-attachment-ssl:reporter
import time
import urllib.request
import urllib.error
import traceback

_DBG_CFG = {"loaded": False, "url": None, "session_id": None}
_DBG_ACTIVE_LOCK = threading.Lock()
_DBG_ACTIVE_REQUESTS = {}

def _dbg_load_cfg():
    if _DBG_CFG["loaded"]:
        return _DBG_CFG
    _DBG_CFG["loaded"] = True
    env_url = os.environ.get("DEBUG_SERVER_URL")
    env_session = os.environ.get("DEBUG_SESSION_ID")
    if env_url and env_session:
        _DBG_CFG["url"] = env_url
        _DBG_CFG["session_id"] = env_session
        return _DBG_CFG
    try:
        env_path = os.path.join(os.getcwd(), ".dbg", "gmail-attachment-ssl.env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f.read().splitlines():
                    line = (line or "").strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = (k or "").strip()
                    v = (v or "").strip()
                    if k == "DEBUG_SERVER_URL":
                        _DBG_CFG["url"] = v
                    elif k == "DEBUG_SESSION_ID":
                        _DBG_CFG["session_id"] = v
    except Exception:
        return _DBG_CFG
    return _DBG_CFG

def _dbg_post(event_name, payload):
    cfg = _dbg_load_cfg()
    url = cfg.get("url")
    session_id = cfg.get("session_id")
    if not url or not session_id:
        return
    body = {
        "ts": int(time.time() * 1000),
        "sessionId": session_id,
        "event": event_name,
        "payload": payload or {},
    }
    try:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=2).read()
    except Exception:
        return

def _dbg_service_meta(service):
    http_obj = getattr(service, "_http", None) if service else None
    return {
        "service_id": id(service) if service else None,
        "http_id": id(http_obj) if http_obj else None,
        "http_type": type(http_obj).__name__ if http_obj else None,
        "thread_id": threading.get_ident(),
        "https_proxy": bool(os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")),
        "http_proxy": bool(os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")),
    }
#endregion debug-point gmail-attachment-ssl:reporter

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send', 
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CREDENTIALS_FILE = os.path.join(SCRIPT_DIR, 'credentials.json')
DEFAULT_TOKEN_FILE = os.path.join(SCRIPT_DIR, 'token.json')

class GmailService:
    def __init__(self, token_file=None, credentials_file=None, token_json=None, auto_auth=True):
        self.service = None
        self.token_file = token_file or DEFAULT_TOKEN_FILE
        self.credentials_file = credentials_file or DEFAULT_CREDENTIALS_FILE
        self.token_json = token_json
        self._credentials_lock = threading.Lock()
        self._attachment_transport_lock = threading.Lock()
        if auto_auth:
            self.authenticate()

    def _load_token_payload(self):
        raw_token_json = self.token_json
        if isinstance(raw_token_json, str) and raw_token_json.strip():
            try:
                raw_token_json = json.loads(raw_token_json)
            except Exception:
                raw_token_json = None
        if isinstance(raw_token_json, dict):
            return dict(raw_token_json)
        if self.token_file and os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'r', encoding='utf-8') as token_file:
                    payload = json.load(token_file)
                if isinstance(payload, dict):
                    return payload
            except Exception as e:
                logging.error(f"Error loading Gmail token file {self.token_file}: {e}")
        return None

    def _build_credentials_from_storage(self):
        payload = self._load_token_payload()
        if not payload:
            return None
        try:
            return Credentials.from_authorized_user_info(payload, SCOPES)
        except Exception as e:
            logging.error(f"Error loading Gmail token JSON: {e}")
            return None

    def _persist_credentials(self, creds):
        self.token_json = creds.to_json()
        if self.token_file:
            try:
                with open(self.token_file, 'w', encoding='utf-8') as token:
                    token.write(self.token_json)
            except Exception as e:
                logging.warning(f"Failed to persist Gmail token file {self.token_file}: {e}")

    def _ensure_valid_credentials(self):
        with self._credentials_lock:
            creds = self._build_credentials_from_storage()

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logging.error(f"Error refreshing token: {e}")
                        creds = None

                if not creds:
                    if not os.path.exists(self.credentials_file):
                        logging.error("credentials.json not found! Please download it from Google Cloud Console.")
                        print("ERROR: credentials.json not found! Please place it in the AIAgentProject folder.")
                        return None

                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)

                self._persist_credentials(creds)

            return creds

    def _build_service_instance(self, creds):
        if not creds:
            return None

        def build_request(unused_http, *args, **kwargs):
            fresh_http = google_auth_httplib2.AuthorizedHttp(
                creds,
                http=httplib2.Http(timeout=30)
            )
            return HttpRequest(fresh_http, *args, **kwargs)

        base_http = google_auth_httplib2.AuthorizedHttp(
            creds,
            http=httplib2.Http(timeout=30)
        )

        return build(
            'gmail',
            'v1',
            cache_discovery=False,
            requestBuilder=build_request,
            http=base_http,
        )

    def _get_service_for_request(self):
        creds = self._ensure_valid_credentials()
        if not creds:
            return None
        service = self._build_service_instance(creds)
        if service:
            self.service = service
        return service

    def _execute_gmail_call(self, operation_name, callback, retry_tls=True):
        attempts = 2 if retry_tls else 1
        last_error = None

        for attempt in range(1, attempts + 1):
            service = self._get_service_for_request()
            if not service:
                raise RuntimeError("Gmail service not initialized.")
            try:
                return callback(service)
            except Exception as e:
                last_error = e
                should_retry = retry_tls and attempt < attempts and self._is_retryable_tls_error(e)
                if should_retry:
                    logging.warning(
                        f"Retrying {operation_name} after transport/TLS error with a fresh Gmail transport: {e}"
                    )
                    continue
                raise

        raise last_error

    def authenticate(self):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = self._ensure_valid_credentials()
        if not creds:
            self.service = None
            return
        try:
            self.service = self._build_service_instance(creds)
            #region debug-point gmail-attachment-ssl:auth-success
            _dbg_post("gmail_service_authenticated", {
                "token_file": os.path.basename(str(self.token_file or "")),
                "credentials_file": os.path.basename(str(self.credentials_file or "")),
                **_dbg_service_meta(self.service),
            })
            #endregion debug-point gmail-attachment-ssl:auth-success
            logging.info("Gmail API Service authenticated successfully.")
        except HttpError as error:
            logging.error(f"An error occurred during Gmail auth: {error}")
            self.service = None

    @staticmethod
    def build_web_auth_url(credentials_file=None, redirect_uri=None, state=None):
        credentials_path = credentials_file or DEFAULT_CREDENTIALS_FILE
        flow = Flow.from_client_secrets_file(credentials_path, scopes=SCOPES)
        if redirect_uri:
            flow.redirect_uri = redirect_uri
        auth_url, next_state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        return auth_url, next_state

    @staticmethod
    def exchange_web_code(code, credentials_file=None, redirect_uri=None):
        credentials_path = credentials_file or DEFAULT_CREDENTIALS_FILE
        flow = Flow.from_client_secrets_file(credentials_path, scopes=SCOPES)
        if redirect_uri:
            flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        return flow.credentials.to_json()

    def get_profile_email(self):
        try:
            profile = self._execute_gmail_call(
                "gmail profile lookup",
                lambda service: service.users().getProfile(userId='me').execute(),
            )
            return str(profile.get('emailAddress') or '').strip() or None
        except Exception as e:
            logging.warning(f"Failed to fetch Gmail profile email: {e}")
            return None

    def _is_retryable_tls_error(self, error):
        err_text = str(error or "").strip().lower()
        return any(token in err_text for token in (
            "wrong version number",
            "ssl:",
            "tls",
            "eof occurred in violation of protocol",
        ))

    def create_draft(self, to_email, subject, html_content, sender_name="FTS Travels", thread_id=None, in_reply_to_message_id=None, attachments=None):
        """Create a draft email."""
        try:
            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = subject
            
            if in_reply_to_message_id:
                message['In-Reply-To'] = in_reply_to_message_id
                message['References'] = in_reply_to_message_id
            
            # Attach HTML Body
            msg = MIMEText(html_content, 'html')
            message.attach(msg)

            # Process Attachments
            if attachments:
                for att in attachments:
                    try:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(att['content'])
                        encoders.encode_base64(part)
                        
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= "{att["filename"]}"'
                        )
                        message.attach(part)
                    except Exception as e:
                        logging.error(f"Failed to attach file {att.get('filename')}: {e}")

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            body = {'message': {'raw': raw_message}}
            
            if thread_id:
                body['message']['threadId'] = thread_id

            draft = self._execute_gmail_call(
                "gmail draft creation",
                lambda service: service.users().drafts().create(userId="me", body=body).execute(),
            )
            logging.info(f"Draft created. Draft Id: {draft['id']}")
            return draft

        except HttpError as error:
            logging.error(f"An error occurred creating draft: {error}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error creating draft: {e}")
            return None

    def send_email(self, to_email, subject, html_content, sender_name="FTS Travels", thread_id=None, in_reply_to_message_id=None, attachments=None):
        """Create and send an email with optional attachments.
           attachments: list of dicts {'filename': str, 'content': bytes, 'mime_type': str}
        """
        try:
            message = MIMEMultipart()
            message['to'] = to_email
            message['subject'] = subject
            
            if in_reply_to_message_id:
                message['In-Reply-To'] = in_reply_to_message_id
                message['References'] = in_reply_to_message_id
            
            # Attach HTML Body
            msg = MIMEText(html_content, 'html')
            message.attach(msg)

            # Process Attachments
            if attachments:
                for att in attachments:
                    try:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(att['content'])
                        encoders.encode_base64(part)
                        
                        # Add header
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= "{att["filename"]}"'
                        )
                        message.attach(part)
                        logging.info(f"Attached file: {att['filename']}")
                    except Exception as e:
                        logging.error(f"Failed to attach file {att.get('filename')}: {e}")

            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            body = {'raw': raw_message}
            
            if thread_id:
                body['threadId'] = thread_id

            sent_message = self._execute_gmail_call(
                "gmail send",
                lambda service: service.users().messages().send(userId="me", body=body).execute(),
            )
            logging.info(f"Email sent to {to_email}. Message Id: {sent_message['id']}")
            return True

        except HttpError as error:
            logging.error(f"An error occurred sending email: {error}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error sending email: {e}")
            return False

    def get_label_id_by_name(self, label_name):
        """Retrieves the Label ID for a given Label Name."""
        try:
            results = self._execute_gmail_call(
                "gmail label lookup",
                lambda service: service.users().labels().list(userId='me').execute(),
            )
            labels = results.get('labels', [])
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            logging.warning(f"Label '{label_name}' not found.")
            return None
        except Exception as e:
            logging.error(f"Error retrieving label ID: {e}")
            return None

    def get_unread_threads(self, label_id, max_results=200, query_q=None):
        """Get unread threads with a specific label."""
        try:
            # query = f"label:{label_name} is:unread"
            # It's safer to use labelId in list()
            # Default maxResults is 100. We increase it to process more old emails if any.
            final_query = ''
            if query_q:
                final_query = f"{query_q}"
            if "is:unread" not in final_query.lower():
                final_query = (final_query + " is:unread").strip()
                
            results = self._execute_gmail_call(
                "gmail thread search",
                lambda service: service.users().threads().list(
                    userId='me',
                    labelIds=[label_id],
                    q=final_query,
                    maxResults=max_results
                ).execute(),
            )
            return results.get('threads', [])
        except Exception as e:
            logging.error(f"Error searching threads: {e}")
            return []

    def _get_body_from_payload(self, payload):
        """Helper to extract body from payload (Recursive)."""
        
        def get_data(part):
            data = part.get('body', {}).get('data')
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode('utf-8')
                except Exception as e:
                    logging.error(f"Error decoding part: {e}")
            return ""

        def find_text(part):
            mime_type = part.get('mimeType')
            
            # If this part is multipart, recurse
            if 'parts' in part:
                best_plain = ""
                best_html = ""
                for subpart in part['parts']:
                    plain, html = find_text(subpart)
                    if plain and not best_plain: best_plain = plain
                    if html and not best_html: best_html = html
                return best_plain, best_html
            
            # If this is a leaf part
            if mime_type == 'text/plain':
                return get_data(part), ""
            elif mime_type == 'text/html':
                return "", get_data(part)
            
            return "", ""

        plain, html = find_text(payload)

        if plain and plain.strip():
            return clean_email_body_for_crm(plain)

        if html and html.strip():
            # Fallback to HTML if no plain text
            # Try to convert to text for better AI processing
            try:
                # Basic cleaning
                text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
                text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)

                def _replace_anchor(match):
                    url = str(match.group(1) or "").strip()
                    label = re.sub(r"<[^>]+>", "", str(match.group(2) or "")).strip()
                    url_l = url.lower()
                    if any(x in url_l for x in ("sendgrid.net", "getyourguide.com", "viator.com", "headout.com")):
                        return label or ""
                    if label and url:
                        return f"{label} ({url})"
                    return label or url

                # Preserve non-tracking links: <a href="url">text</a> -> text (url)
                text = re.sub(
                    r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                    _replace_anchor,
                    text,
                    flags=re.IGNORECASE | re.DOTALL,
                )

                text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
                text = re.sub(r'</(p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
                text = re.sub(r'<[^>]+>', '\n', text)
                return clean_email_body_for_crm(text)
            except Exception:
                return clean_email_body_for_crm(html)
            
        return ""

    def _get_attachments_from_payload(self, payload):
        def get_header(part, name):
            headers = part.get('headers', []) or []
            for h in headers:
                if str(h.get('name', '')).lower() == str(name).lower():
                    return str(h.get('value', '') or '')
            return ""

        attachments = []

        def walk(part):
            if not isinstance(part, dict):
                return
            for sub in part.get('parts', []) or []:
                walk(sub)

            mime_type = str(part.get('mimeType') or '')
            if mime_type in ('text/plain', 'text/html'):
                return

            body = part.get('body', {}) or {}
            attachment_id = body.get('attachmentId')
            if not attachment_id:
                return

            filename = str(part.get('filename') or '').strip()
            content_disposition = get_header(part, 'Content-Disposition').lower()
            is_attachment_like = ('attachment' in content_disposition) or ('inline' in content_disposition) or bool(filename)
            if not is_attachment_like:
                return

            attachments.append({
                "attachment_id": str(attachment_id),
                "filename": filename or "attachment",
                "mime_type": mime_type or "application/octet-stream",
                "size": body.get('size')
            })

        walk(payload or {})
        return attachments

    def _find_attachment_part(self, payload, attachment_id):
        found = None

        def walk(part):
            nonlocal found
            if found is not None:
                return
            if not isinstance(part, dict):
                return
            body = part.get('body', {}) or {}
            if str(body.get('attachmentId') or '') == str(attachment_id):
                found = part
                return
            for sub in part.get('parts', []) or []:
                walk(sub)

        walk(payload or {})
        return found

    def get_attachment_content(self, message_id, attachment_id):
        service = self._get_service_for_request()
        if not service:
            return None
        #region debug-point gmail-attachment-ssl:get-attachment-content
        service_meta = _dbg_service_meta(service)
        service_id = service_meta.get("service_id")
        with _DBG_ACTIVE_LOCK:
            active_before = int(_DBG_ACTIVE_REQUESTS.get(service_id, 0))
            _DBG_ACTIVE_REQUESTS[service_id] = active_before + 1
            active_now = int(_DBG_ACTIVE_REQUESTS.get(service_id, 0))
        req_id = f"{int(time.time() * 1000)}-{os.getpid()}-{service_meta.get('thread_id')}-{str(message_id)[-6:]}"
        _dbg_post("gmail_attachment_content_start", {
            "req_id": req_id,
            "message_id": str(message_id),
            "attachment_id": str(attachment_id),
            "token_file": os.path.basename(str(self.token_file or "")),
            "credentials_file": os.path.basename(str(self.credentials_file or "")),
            "active_before": active_before,
            "active_now": active_now,
            **service_meta,
        })
        #endregion debug-point gmail-attachment-ssl:get-attachment-content
        stage = "init"
        try:
            stage = "transport_lock_wait"
            wait_started_at = time.time()
            #region debug-point gmail-attachment-ssl:lock-wait
            _dbg_post("gmail_attachment_lock_wait", {
                "req_id": req_id,
                "message_id": str(message_id),
                "attachment_id": str(attachment_id),
                "active_now": active_now,
                **service_meta,
            })
            #endregion debug-point gmail-attachment-ssl:lock-wait
            with self._attachment_transport_lock:
                lock_wait_ms = int((time.time() - wait_started_at) * 1000)
                service_meta = _dbg_service_meta(service)
                #region debug-point gmail-attachment-ssl:lock-acquired
                _dbg_post("gmail_attachment_lock_acquired", {
                    "req_id": req_id,
                    "message_id": str(message_id),
                    "attachment_id": str(attachment_id),
                    "lock_wait_ms": lock_wait_ms,
                    "active_now": active_now,
                    **service_meta,
                })
                #endregion debug-point gmail-attachment-ssl:lock-acquired

                stage = "message_get"
                #region debug-point gmail-attachment-ssl:message-get-start
                _dbg_post("gmail_attachment_message_get_start", {
                    "req_id": req_id,
                    "message_id": str(message_id),
                    "attachment_id": str(attachment_id),
                    "active_now": active_now,
                    **service_meta,
                })
                #endregion debug-point gmail-attachment-ssl:message-get-start
                msg = self._execute_gmail_call(
                    "gmail attachment message lookup",
                    lambda svc: svc.users().messages().get(
                        userId='me',
                        id=message_id,
                        format='full'
                    ).execute(),
                )
                payload = msg.get('payload', {}) or {}

                stage = "part_find"
                part = self._find_attachment_part(payload, attachment_id) or {}
                if not part:
                    #region debug-point gmail-attachment-ssl:part-missing
                    try:
                        atts = self._get_attachments_from_payload(payload) or []
                        att_ids = [str(a.get("attachment_id") or "") for a in atts if a.get("attachment_id")]
                    except Exception:
                        att_ids = []
                    _dbg_post("gmail_attachment_part_missing", {
                        "req_id": req_id,
                        "message_id": str(message_id),
                        "attachment_id": str(attachment_id),
                        "available_attachment_ids": att_ids[:30],
                        "available_attachment_ids_count": len(att_ids),
                    })
                    #endregion debug-point gmail-attachment-ssl:part-missing
                filename = str(part.get('filename') or '').strip() or "attachment"
                mime_type = str(part.get('mimeType') or '').strip() or "application/octet-stream"

                stage = "attachment_get"
                #region debug-point gmail-attachment-ssl:attachment-get-start
                _dbg_post("gmail_attachment_attachment_get_start", {
                    "req_id": req_id,
                    "message_id": str(message_id),
                    "attachment_id": str(attachment_id),
                    "active_now": active_now,
                    **service_meta,
                })
                #endregion debug-point gmail-attachment-ssl:attachment-get-start
                att = self._execute_gmail_call(
                    "gmail attachment download",
                    lambda svc: svc.users().messages().attachments().get(
                        userId='me',
                        messageId=message_id,
                        id=attachment_id
                    ).execute(),
                )
                data = att.get('data')
                if not data:
                    #region debug-point gmail-attachment-ssl:no-data
                    _dbg_post("gmail_attachment_no_data", {
                        "req_id": req_id,
                        "message_id": str(message_id),
                        "attachment_id": str(attachment_id),
                    })
                    #endregion debug-point gmail-attachment-ssl:no-data
                    return None
                content_bytes = base64.urlsafe_b64decode(data.encode('utf-8'))
                #region debug-point gmail-attachment-ssl:success
                _dbg_post("gmail_attachment_success", {
                    "req_id": req_id,
                    "message_id": str(message_id),
                    "attachment_id": str(attachment_id),
                    "bytes_len": len(content_bytes or b""),
                    "filename": filename,
                    "mime_type": mime_type,
                    "active_now": active_now,
                    "lock_wait_ms": lock_wait_ms,
                    **service_meta,
                })
                #endregion debug-point gmail-attachment-ssl:success
                return {"bytes": content_bytes, "filename": filename, "mime_type": mime_type}
        except Exception as e:
            #region debug-point gmail-attachment-ssl:exception
            _dbg_post("gmail_attachment_exception", {
                "req_id": req_id,
                "stage": stage,
                "message_id": str(message_id),
                "attachment_id": str(attachment_id),
                "exc_type": type(e).__name__,
                "exc": str(e)[:500],
                "stack": "".join(traceback.format_stack(limit=8)),
                "active_now": active_now,
                **service_meta,
            })
            #endregion debug-point gmail-attachment-ssl:exception
            logging.error(f"Error getting message attachment content: {e}")
            return None
        finally:
            #region debug-point gmail-attachment-ssl:end
            with _DBG_ACTIVE_LOCK:
                current = int(_DBG_ACTIVE_REQUESTS.get(service_id, 0))
                if current <= 1:
                    _DBG_ACTIVE_REQUESTS.pop(service_id, None)
                    active_after = 0
                else:
                    _DBG_ACTIVE_REQUESTS[service_id] = current - 1
                    active_after = int(_DBG_ACTIVE_REQUESTS.get(service_id, 0))
            _dbg_post("gmail_attachment_content_end", {
                "req_id": req_id,
                "message_id": str(message_id),
                "attachment_id": str(attachment_id),
                "stage": stage,
                "active_after": active_after,
                **service_meta,
            })
            #endregion debug-point gmail-attachment-ssl:end

    def get_message_details(self, message_id):
        """Get the subject, sender, and body of a message."""
        try:
            message = self._execute_gmail_call(
                "gmail message details lookup",
                lambda service: service.users().messages().get(userId='me', id=message_id).execute(),
            )
            payload = message['payload']
            headers = payload.get('headers', [])
            
            subject = ""
            sender = ""
            reply_to = ""
            date = ""
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                if header['name'] == 'From':
                    sender = header['value']
                if header['name'].lower() == 'reply-to':
                    reply_to = header['value']
                if header['name'] == 'Date':
                    date = header['value']
            
            body = self._get_body_from_payload(payload)
            attachments = self._get_attachments_from_payload(payload)
            
            return {
                "id": message_id,
                "threadId": message['threadId'],
                "subject": subject,
                "sender": sender,
                "reply_to": reply_to,
                "date": date,
                "body": body,
                "attachments": attachments
            }
        except Exception as e:
            logging.error(f"Error getting message details: {e}")
            return {}

    def get_thread_history(self, thread_id):
        """Get all messages in a thread sorted chronologically."""
        try:
            thread = self._execute_gmail_call(
                "gmail thread history lookup",
                lambda service: service.users().threads().get(userId='me', id=thread_id).execute(),
            )
            messages = thread.get('messages', [])
            
            history = []
            for msg in messages:
                payload = msg['payload']
                headers = payload.get('headers', [])
                
                sender = ""
                reply_to = ""
                date = ""
                subject = ""
                for header in headers:
                    if header['name'] == 'From':
                        sender = header['value']
                    if header['name'].lower() == 'reply-to':
                        reply_to = header['value']
                    if header['name'] == 'Date':
                        date = header['value']
                    if header['name'] == 'Subject':
                        subject = header['value']
                
                body = self._get_body_from_payload(payload)
                attachments = self._get_attachments_from_payload(payload)
                
                history.append({
                    "id": msg['id'],
                    "sender": sender,
                    "reply_to": reply_to,
                    "date": date,
                    "subject": subject,
                    "body": body,
                    "attachments": attachments
                })
            
            return history
        except Exception as e:
            logging.error(f"Error retrieving thread history: {e}")
            return []

    def modify_thread_labels(self, thread_id, add_labels=None, remove_labels=None):
        """Modify the labels of a thread."""
        try:
            add_labels = add_labels or []
            remove_labels = remove_labels or []
            if not add_labels and not remove_labels:
                return True
            body = {
                'addLabelIds': add_labels,
                'removeLabelIds': remove_labels
            }
            self._execute_gmail_call(
                "gmail thread label update",
                lambda service: service.users().threads().modify(
                    userId='me',
                    id=thread_id,
                    body=body
                ).execute(),
            )
            logging.info(f"Thread {thread_id} labels updated.")
            return True
        except Exception as e:
            logging.error(f"Error modifying thread labels: {e}")
            return False
