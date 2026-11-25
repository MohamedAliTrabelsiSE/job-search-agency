"""Private run artifacts and durable job-level application history."""
import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Short sibling name also supports Windows workspaces near MAX_PATH.
    temp = path.with_name('.j-' + uuid.uuid4().hex[:8] + '.tmp')
    try:
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def job_key(card):
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    url = card.get('url') or ''
    if url:
        parts = urlsplit(url)
        identity_query = [(k,v) for k,v in parse_qsl(parts.query) if k.lower() in {'gh_jid','jobid','job_id','id'}]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/').removesuffix('/application'), urlencode(sorted(identity_query)), ''))
    return hashlib.sha256(json.dumps([card.get(k) for k in ('company','title','location')]).encode()).hexdigest()


class Store:
    def __init__(self, data):
        self.data = Path(data)
        self.data.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, started TEXT, status TEXT, details TEXT);
                CREATE TABLE IF NOT EXISTS applications (job TEXT PRIMARY KEY, company TEXT, status TEXT, updated TEXT, details TEXT);
                CREATE TABLE IF NOT EXISTS sources (source TEXT PRIMARY KEY, checked TEXT, status TEXT, details TEXT);
                CREATE TABLE IF NOT EXISTS application_events (job TEXT, status TEXT, updated TEXT, details TEXT);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.data / 'agency.sqlite3')
        try:
            with db:
                yield db
        finally:
            db.close()

    def start_run(self):
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
        folder = self.data / 'runs' / run_id
        folder.mkdir(parents=True)
        with self.connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?)', (run_id, now(), 'running', '{}'))
        return run_id, folder

    def finish_run(self, run_id, status, details):
        with self.connect() as db:
            db.execute('UPDATE runs SET status=?, details=? WHERE id=?', (status, json.dumps(details), run_id))

    def record_application(self, card, status, details):
        allowed = {'prepared','approved','submitted','duplicate_blocked','failed'}
        if status not in allowed:
            raise ValueError('Unknown application status')
        if status in {'submitted','duplicate_blocked'} and not details.get('evidence'):
            raise ValueError('A submission outcome requires observed evidence')
        previous = self.application(card)
        if previous and previous['status'] in {'submitted','duplicate_blocked'} and status in {'prepared','approved'}:
            raise ValueError('An existing application outcome cannot be replaced by preparation or approval.')
        with self.connect() as db:
            db.execute('INSERT INTO application_events VALUES (?,?,?,?)',
                       (job_key(card), status, now(), json.dumps(details)))
            db.execute('INSERT OR REPLACE INTO applications VALUES (?,?,?,?,?)',
                       (job_key(card), card.get('company'), status, now(), json.dumps(details)))

    def application(self, card):
        with self.connect() as db:
            row = db.execute('SELECT status, details FROM applications WHERE job=?', (job_key(card),)).fetchone()
        return {'status':row[0], 'details':json.loads(row[1])} if row else None

    def application_history(self, card):
        with self.connect() as db:
            rows = db.execute('SELECT status, updated, details FROM application_events WHERE job=? ORDER BY rowid', (job_key(card),)).fetchall()
        return [{'status':status,'updated':updated,'details':json.loads(details)} for status,updated,details in rows]

    def record_sources(self, reports):
        with self.connect() as db:
            for report in reports:
                db.execute('INSERT OR REPLACE INTO sources VALUES (?,?,?,?)',
                           (report['platform'] + ':' + report['company'], now(), report['status'], json.dumps(report)))
