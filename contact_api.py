"""Contact-only API for the public HYDD website.

Run behind HTTPS Nginx at /api/contact; no credentials embedded in code.
A request is an enquiry, never a booking or payment.
Rate limiting is local to ONE process; use a WAF/Redis for high-traffic deployments.
"""
from __future__ import annotations
import os,re,ssl,smtplib,time,threading
from collections import defaultdict,deque
from email.message import EmailMessage
from datetime import date
from urllib.parse import urlsplit
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

app=FastAPI(title='HYDD contact gateway',docs_url=None,redoc_url=None,openapi_url=None)
_ALLOWED_LANG={'fr','en','ar'}
_ALLOWED_SERVICE={'','chauffeur','transfer','vip','events','excursions','concierge','protection'}
_REQUESTS:dict[str,deque]=defaultdict(deque)
_LOCK=threading.Lock()
_MAX_BYTES=8192
_EMAIL=re.compile(r'^[^\s@<>\x00-\x1f]+@[^\s@<>\x00-\x1f]+\.[A-Za-z]{2,}$')
_PHONE=re.compile(r'^[0-9+().\-\s]{0,40}$')


def origin():
    return os.getenv('SITE_ORIGIN','https://www.hydd.fr').rstrip('/')


def rate_allow(ip):
    """Allow at most 5 submissions per hour / IP. Deploy one worker; use edge controls too."""
    now=time.monotonic()
    with _LOCK:
        dq=_REQUESTS[ip]
        while dq and dq[0]<now-3600: dq.popleft()
        if len(dq)>=5:return False
        dq.append(now)
        return True


def validate_payload(payload):
    if not isinstance(payload,dict): raise HTTPException(400,'Invalid enquiry')
    if set(payload.keys())-{'name','email','phone','date','service','message','consent','website','language','page'}:
        raise HTTPException(400,'Unexpected fields')
    if payload.get('website'):
        raise HTTPException(400,'Invalid enquiry')  # hidden honeypot
    def field(key,maxlen,required=False):
        value=payload.get(key,'')
        if not isinstance(value,str) or len(value)>maxlen: raise HTTPException(400,'Invalid '+key)
        value=value.strip()
        if required and not value:raise HTTPException(400,'Missing '+key)
        return value
    name=field('name',120,True)
    if len(name)<2: raise HTTPException(400,'Invalid name')
    email=field('email',254,True)
    if not _EMAIL.fullmatch(email):raise HTTPException(400,'Invalid email')
    phone=field('phone',40)
    if not _PHONE.fullmatch(phone):raise HTTPException(400,'Invalid phone')
    service=field('service',35)
    if service not in _ALLOWED_SERVICE:raise HTTPException(400,'Invalid service')
    travel_date=field('date',10)
    if travel_date:
        try:date.fromisoformat(travel_date)
        except ValueError: raise HTTPException(400,'Invalid date')
    message=field('message',4000,True)
    if len(message)<8: raise HTTPException(400,'Message too short')
    language=field('language',2)
    if language not in _ALLOWED_LANG:raise HTTPException(400,'Invalid language')
    page=field('page',500)
    if page:
        u=urlsplit(page)
        site=urlsplit(origin())
        if u.scheme!=site.scheme or u.netloc!=site.netloc or not u.path.startswith('/'):
            # localhost staging needs SITE_ORIGIN set accordingly.
            raise HTTPException(400,'Invalid page')
    if payload.get('consent') is not True:raise HTTPException(400,'Consent required')
    return {'name':name,'email':email,'phone':phone,'service':service,'date':travel_date,
            'message':message,'language':language,'page':page}


def smtp_configured():
    required=('EMAIL_HOST','EMAIL_HOST_USER','EMAIL_HOST_PASSWORD','EMAIL_FROM','CONTACT_TO')
    return all(bool(os.environ.get(k)) for k in required)


def send_contact_email(d):
    """Deliver to verified recipient over TLS. No end-user supplied headers."""
    if not smtp_configured():raise RuntimeError('SMTP_NOT_CONFIGURED')
    hostname=os.environ['EMAIL_HOST']
    port=int(os.getenv('EMAIL_PORT','587'))
    if port not in (465,587): raise RuntimeError('SMTP_TLS_REQUIRED')
    from_address=os.environ['EMAIL_FROM']
    recipient=os.environ['CONTACT_TO']
    if not _EMAIL.fullmatch(from_address) or not _EMAIL.fullmatch(recipient):
        raise RuntimeError('INVALID_SMTP_ADDRESS')
    msg=EmailMessage()
    msg['Subject']='HYDD website enquiry'  # Never use untrusted data in headers.
    msg['From']=from_address
    msg['To']=recipient
    msg['Reply-To']=d['email']
    msg.set_content('\n'.join([
      'HYDD Website Enquiry (not a confirmed booking)',
      'Name: '+d['name'],'Email: '+d['email'],'Phone: '+d['phone'],
      'Service: '+d['service'],'Date: '+d['date'],'Language: '+d['language'],
      'Page: '+d['page'],'','Message:',d['message']
    ]))
    user=os.environ['EMAIL_HOST_USER'];password=os.environ['EMAIL_HOST_PASSWORD']
    if port==465:
        with smtplib.SMTP_SSL(hostname,port,timeout=10,context=ssl.create_default_context()) as client:
            client.login(user,password);client.send_message(msg)
    else:
        with smtplib.SMTP(hostname,port,timeout=10) as client:
            client.ehlo();client.starttls(context=ssl.create_default_context());client.ehlo()
            client.login(user,password);client.send_message(msg)


@app.get('/health')
async def health():
    return {'ok':True,'email_ready':smtp_configured()}


@app.post('/api/contact')
async def contact(request:Request):
    # The website and API must share exactly one HTTPS origin in production.
    if request.headers.get('origin') != origin():
        raise HTTPException(403,'Invalid origin')
    if 'application/json' not in request.headers.get('content-type',''):
        raise HTTPException(415,'JSON required')
    content_length=request.headers.get('content-length')
    if content_length:
        try:
            if int(content_length)>_MAX_BYTES: raise HTTPException(413,'Enquiry too large')
        except ValueError:raise HTTPException(400,'Invalid request length')
    # Hard limit actual body length even when Content-Length is missing/incorrect.
    received=bytearray()
    async for part in request.stream():
        received.extend(part)
        if len(received)>_MAX_BYTES:raise HTTPException(413,'Enquiry too large')
    try:
        import json
        payload=json.loads(received)
    except (ValueError,UnicodeDecodeError):raise HTTPException(400,'Invalid JSON')
    values=validate_payload(payload)
    if not smtp_configured():raise HTTPException(503,'Email unavailable')
    client_ip=request.headers.get('x-real-ip') if os.environ.get('HYDD_TRUST_NGINX')=='1' else None
    if client_ip is None:client_ip=request.client.host if request.client else 'unknown'
    if not rate_allow(client_ip):raise HTTPException(429,'Please try again later')
    try:send_contact_email(values)
    except Exception:
        # Do not log sender details, SMTP passwords, or error objects containing credentials.
        raise HTTPException(503,'Email unavailable')
    return JSONResponse({'ok':True})
