#!/usr/bin/env python3
"""Spotify control: auth | devices | play <n|name> [m:ss] | stop | now"""
import sys,json,os,time,base64,hashlib,secrets,urllib.parse,urllib.request,http.server
D=os.path.dirname(os.path.abspath(__file__)); CFG=D+'/config.json'; TOK=D+'/token.json'
RED='http://127.0.0.1:8888/callback'
SC='user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private playlist-modify-private playlist-modify-public'
def cfg(): return json.load(open(CFG)) if os.path.exists(CFG) else {}
def save(p,d): json.dump(d,open(p,'w'),indent=1)
def post_tok(data):
    r=urllib.request.urlopen(urllib.request.Request('https://accounts.spotify.com/api/token',urllib.parse.urlencode(data).encode(),{'Content-Type':'application/x-www-form-urlencoded'}))
    t=json.load(r); t['exp']=time.time()+t['expires_in']-60; return t
def auth():
    c=cfg(); v=secrets.token_urlsafe(64); ch=base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b'=').decode()
    url='https://accounts.spotify.com/authorize?'+urllib.parse.urlencode(dict(client_id=c['client_id'],response_type='code',redirect_uri=RED,code_challenge_method='S256',code_challenge=ch,scope=SC))
    open(D+'/auth_url.txt','w').write(url); print(url,flush=True)
    got={}
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(s):
            q=urllib.parse.parse_qs(urllib.parse.urlparse(s.path).query); got.update(q)
            s.send_response(200); s.end_headers(); s.wfile.write(b'Hockey Music Bot connected. You can close this tab.')
        def log_message(s,*a): pass
    srv=http.server.HTTPServer(('127.0.0.1',8888),H)
    while 'code' not in got and 'error' not in got: srv.handle_request()
    if 'error' in got: print('ERROR',got); return
    t=post_tok(dict(grant_type='authorization_code',code=got['code'][0],redirect_uri=RED,client_id=c['client_id'],code_verifier=v))
    save(TOK,t); print('AUTH OK')
def token():
    t=json.load(open(TOK))
    if time.time()>t['exp']:
        n=post_tok(dict(grant_type='refresh_token',refresh_token=t['refresh_token'],client_id=cfg()['client_id']))
        n.setdefault('refresh_token',t['refresh_token']); save(TOK,n); t=n
    return t['access_token']
def api(m,p,body=None):
    req=urllib.request.Request('https://api.spotify.com/v1'+p,json.dumps(body).encode() if body is not None else (b'' if m=='PUT' else None),{'Authorization':'Bearer '+token(),'Content-Type':'application/json'},method=m)
    try:
        r=urllib.request.urlopen(req); b=r.read(); 
        try: return r.status,(json.loads(b) if b else None)
        except ValueError: return r.status,b[:80]
    except urllib.error.HTTPError as e: return e.code,e.read().decode()
def secs(s):
    if ':' in s: a,b=s.split(':'); return int(a)*60+float(b)
    return float(s)
def find(q):
    tr=json.load(open(D+'/songs.json'))['tracks']
    if q.isdigit(): return tr[int(q)-1]
    ql=q.lower()
    tr=[t for t in tr if not t.get('removed')]
    for f in (lambda t:ql==t['title'].lower(), lambda t:ql in (t.get('alias') or '').lower() or ql in t['title'].lower(), lambda t:ql in (t['title']+' '+t['artist']).lower()):
        for t in tr:
            if f(t): return t
    raise SystemExit('no match: '+q)
def dev():
    c=cfg(); return c.get('device_id')
def main(a):
    if a[0]=='auth': return auth()
    if a[0]=='devices': print(json.dumps(api('GET','/me/player/devices'),indent=1)); return
    if a[0]=='now': print(json.dumps(api('GET','/me/player'),indent=1)[:1500]); return
    if a[0]=='stop':
        open(D+'/last_play','w').write('stopped'); d=dev(); print(api('PUT','/me/player/pause'+(f'?device_id={d}' if d else ''))); return

    if a[0]=='startgame':
        save(D+'/game.json',{'played':[],'started':time.time()})
        if os.path.exists(D+'/next.json'): os.remove(D+'/next.json')
        print('GAME RESET'); return
    if a[0]=='queue':
        t=find(' '.join(a[1:])); save(D+'/next.json',{'n':t['n']}); print('QUEUED',t['n'],t['title'],'-',t['artist']); return
    if a[0]=='suggest':
        import random
        tr=json.load(open(D+'/songs.json'))['tracks']; g=json.load(open(D+'/game.json')) if os.path.exists(D+'/game.json') else {'played':[]}
        c=[t for t in tr if not t.get('removed') and t['n'] not in g['played']]
        for t in random.sample(c,min(int(a[1]) if len(a)>1 else 5,len(c))): print(t['n'],'|',t['title'],'|',t['artist'],'|',','.join(t['cats']))
        print('unplayed',len(c)); return
    if a[0]=='cat':
        import random,subprocess
        dur=0  # never auto-stop (user rule)
        tr=json.load(open(D+'/songs.json'))['tracks']
        pool=[t for t in tr if a[1] in t.get('cats',[a[1]]) and not t.get('explicit') and not t.get('removed')]
        hist=json.load(open(D+'/recent.json')) if os.path.exists(D+'/recent.json') else []
        g=json.load(open(D+'/game.json')) if os.path.exists(D+'/game.json') else {'played':[]}
        nx=json.load(open(D+'/next.json')) if os.path.exists(D+'/next.json') else None
        note=''
        if nx:
            t=[x for x in tr if x['n']==nx['n']][0]; os.remove(D+'/next.json'); note='QUEUED '
        else:
            cand=[t for t in pool if t['n'] not in g['played'] and t['uri'] not in hist] or [t for t in pool if t['n'] not in g['played']]
            if not cand: note='ALL-PLAYED-REPEAT '; cand=pool
            t=random.choice(cand)
        hist=(hist+[t['uri']])[-25:]; save(D+'/recent.json',hist)
        g['played']=g['played']+[t['n']]; save(D+'/game.json',g)
        st=secs(t.get({'short':'short_start','medium':'short_start','long':'long_start'}[a[1]]) or '0'); d=dev(); q=f'?device_id={d}' if d else ''
        s,r=api('PUT','/me/player/play'+q,{'uris':[t['uri']],'position_ms':int(st*1000)})
        tag=str(time.time()); open(D+'/last_play','w').write(tag)
        if dur and s in (200,202,204):
            subprocess.Popen([sys.executable,os.path.abspath(__file__),'autostop',str(dur),tag],start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        open(D+'/last_n','w').write(str(t['n']))
        print(note+str(s),r,'|',t['n'],t['title'],'-',t['artist'],'@',st); return
    if a[0]=='autostop':
        time.sleep(float(a[1]))
        if open(D+'/last_play').read()==a[2]: api('PUT','/me/player/pause'+(f'?device_id={dev()}' if dev() else ''))
        return
    if a[0] in ('earlier','later'):
        n=int(open(D+'/last_n').read()); k='short_start'
        d_=json.load(open(D+'/songs.json')); t=[x for x in d_['tracks'] if x['n']==n][0]
        v=max(0,secs(t.get(k) or '0')+(-1 if a[0]=='earlier' else 1)*float(a[1] if len(a)>1 else 3))
        t[k]=f"{int(v//60)}:{v%60:04.1f}".replace(".0",""); json.dump(d_,open(D+'/songs.json','w'),indent=1)
        a=['play',str(n),t[k]]
    if a[0]=='preview':
        d_=json.load(open(D+'/songs.json')); t=[x for x in d_['tracks'] if x['n']==int(a[1])][0]
        a=['play',a[1],t.get('long_start' if len(a)>2 and a[2]=='long' else 'short_start') or '0:00']
    if a[0]=='play':
        t=find(a[1]); st=secs(a[2]) if len(a)>2 else secs(t.get('start','0'))
        d=dev(); q=f'?device_id={d}' if d else ''
        s,r=api('PUT','/me/player/play'+q,{'uris':[t['uri']],'position_ms':int(st*1000)})
        open(D+'/last_play','w').write(str(time.time()))
        open(D+'/last_n','w').write(str(t['n']))
        print(s,r,'|',t['n'],t['title'],'-',t['artist'],'@',st); return
main(sys.argv[1:])
