import json, urllib.request, urllib.error
# try POST force only if route exists - user asked
url='https://api.ftstravels.com/api/mirror/force_sync'
try:
    req=urllib.request.Request(url, data=b'{}', method='POST', headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=20) as resp:
        print('POST', url, resp.status, resp.read()[:300])
except urllib.error.HTTPError as e:
    print('POST', url, 'HTTP', e.code, e.read()[:300])
except Exception as e:
    print('POST', url, type(e).__name__, e)
