import json, time, uuid, re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, timezone
DOCS = {}  # name -> {fields, updated}
def now():
    t = time.time(); d = datetime.fromtimestamp(t, timezone.utc)
    return d.strftime('%Y-%m-%dT%H:%M:%S.') + '%06dZ' % d.microsecond
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def cors(self):
        self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Access-Control-Allow-Headers', '*'); self.send_header('Access-Control-Allow-Methods', '*')
    def do_OPTIONS(self): self.send_response(204); self.cors(); self.end_headers()
    def out(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code); self.cors(); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(b)
    def body(self):
        n = int(self.headers.get('Content-Length') or 0); return self.rfile.read(n).decode()
    def authed(self): return (self.headers.get('Authorization') or '').startswith('Bearer tok')
    def do_GET(self):
        m = re.search(r'/documents/(.*)$', self.path)
        if not self.authed(): return self.out(403, {'error': {'message': 'denied'}})
        name = 'projects/P/databases/(default)/documents/' + m.group(1)
        if name in DOCS: return self.out(200, {'name': name, 'fields': DOCS[name]['fields']})
        return self.out(404, {'error': {'message': 'not found'}})
    def do_POST(self):
        p = self.path; b = self.body()
        if 'accounts:signUp' in p: return self.out(200, {'idToken': 'tok' + uuid.uuid4().hex, 'refreshToken': 'r', 'expiresIn': '3600'})
        if '/v1/token' in p: return self.out(200, {'id_token': 'tok2', 'refresh_token': 'r', 'expires_in': '3600'})
        if not self.authed(): return self.out(403, {'error': {'message': 'denied'}})
        j = json.loads(b)
        if p.endswith(':commit'):
            t = now()
            for w in j['writes']:
                n = w['update']['name']
                if w.get('currentDocument', {}).get('exists') is False and n in DOCS: return self.out(409, {'error': {'message': 'exists'}})
            for w in j['writes']:
                f = dict(w['update']['fields'])
                for tr in w.get('updateTransforms', []): f[tr['fieldPath']] = {'timestampValue': t}
                DOCS[w['update']['name']] = {'fields': f}
            return self.out(200, {'commitTime': t})
        if p.endswith(':runQuery'):
            parent = p.split('/documents/')[1].replace(':runQuery', '')
            q = j['structuredQuery']; pre = 'projects/P/databases/(default)/documents/' + parent + '/records/'
            rows = [(n, d) for n, d in DOCS.items() if n.startswith(pre)]
            if 'where' in q:
                v = q['where']['fieldFilter']['value']['timestampValue']
                def key(s):  # compare as times
                    s = s.rstrip('Z'); a, _, frac = s.partition('.'); return a + '.' + (frac + '000000')[:6]
                rows = [r for r in rows if key(r[1]['fields']['updated']['timestampValue']) > key(v)]
            rows.sort(key=lambda r: r[1]['fields']['updated']['timestampValue'])
            rows = rows[:q.get('limit', 1000)]
            res = [{'document': {'name': n, 'fields': d['fields']}, 'readTime': now()} for n, d in rows] or [{'readTime': now()}]
            return self.out(200, res)
        self.out(400, {'error': {'message': 'bad'}})
ThreadingHTTPServer(('127.0.0.1', 8765), H).serve_forever()
