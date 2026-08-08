import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = '''def _apply_api_cors_headers(response):
        try:
            origin = request.headers.get("Origin")
            
            allowed_origins = [
                "http://localhost:5173", 
                "http://localhost:5174", 
                "https://crm.ftstravels.net", 
                "https://api.ftstravels.com"
            ]
            
            if origin in allowed_origins or (origin and origin.endswith(".ftstravels.com")):
                response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "https://crm.ftstravels.net"

            if "Vary" not in response.headers:
                response.headers["Vary"] = "Origin"

            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                request.headers.get("Access-Control-Request-Headers")
                or "Content-Type, Authorization, Range, X-Requested-With, Cache-Control"
            )
            response.headers["Access-Control-Expose-Headers"] = (
                "Content-Type, Content-Length, Content-Disposition, "
                "Content-Range, Accept-Ranges"
            )
            response.headers["Access-Control-Allow-Credentials"] = "true"
        except Exception:
            pass
        return response'''

old_block = re.search(r'def _apply_api_cors_headers\(response\):.*?return response', content, re.DOTALL)

if old_block:
    content = content.replace(old_block.group(0), new_func)
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS')
else:
    print('FAILED')
