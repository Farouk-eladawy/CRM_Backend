import base64
import urllib.parse
import struct
import sys

def get_varint(data, pos):
    result = 0
    shift = 0
    while True:
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7

def parse_otp_migration(uri):
    parsed = urllib.parse.urlparse(uri)
    query_params = urllib.parse.parse_qs(parsed.query)
    data_str = query_params['data'][0]
    
    # Base64 decode
    binary_data = base64.b64decode(data_str)
    
    pos = 0
    length = len(binary_data)
    
    secrets = []
    
    while pos < length:
        # Read Key
        if pos >= length: break
        key, pos = get_varint(binary_data, pos)
        field_number = key >> 3
        wire_type = key & 0x07
        
        if field_number == 1: # otp_parameters (repeated)
            # Read Length
            msg_len, pos = get_varint(binary_data, pos)
            end_pos = pos + msg_len
            
            # Parse OtpParameters message
            secret = None
            name = None
            issuer = None
            
            p_pos = pos
            while p_pos < end_pos:
                p_key, p_pos = get_varint(binary_data, p_pos)
                p_field = p_key >> 3
                p_wire = p_key & 0x07
                
                if p_field == 1: # secret
                    s_len, p_pos = get_varint(binary_data, p_pos)
                    secret = binary_data[p_pos : p_pos + s_len]
                    p_pos += s_len
                elif p_field == 2: # name
                    n_len, p_pos = get_varint(binary_data, p_pos)
                    name = binary_data[p_pos : p_pos + n_len].decode('utf-8', errors='ignore')
                    p_pos += n_len
                elif p_field == 3: # issuer
                    i_len, p_pos = get_varint(binary_data, p_pos)
                    issuer = binary_data[p_pos : p_pos + i_len].decode('utf-8', errors='ignore')
                    p_pos += i_len
                else:
                    # Skip unknown fields (assuming length delimited for simplicity or varint)
                    # This is a naive parser, valid only for expected types
                    if p_wire == 2: # Length delimited
                        l, p_pos = get_varint(binary_data, p_pos)
                        p_pos += l
                    elif p_wire == 0: # Varint
                        _, p_pos = get_varint(binary_data, p_pos)
                    # Add other wire types if needed
            
            if secret:
                secrets.append({
                    'secret_bytes': secret,
                    'name': name,
                    'issuer': issuer
                })
            
            pos = end_pos
        else:
             # Skip outer fields
            if wire_type == 2:
                l, pos = get_varint(binary_data, pos)
                pos += l
            elif wire_type == 0:
                _, pos = get_varint(binary_data, pos)
                
    return secrets

if __name__ == "__main__":
    uri = "otpauth-migration://offline?data=CmQKFHr6%2BefJQG5I79n53sfzIay5XLsUEhxyZWlzZW5AYWVneXB0ZW4tYXVzZmx1ZWdlLmRlGhNTdXBwbGllciBQb3J0YWwgMkZBIAEoATACQhM2ZGYzYzExNzQ2MjgxNjIyODA0EAIYASAA"
    
    try:
        secrets = parse_otp_migration(uri)
        import base64
        
        for s in secrets:
            # Convert bytes to Base32
            b32_secret = base64.b32encode(s['secret_bytes']).decode('utf-8').replace('=', '')
            print(f"Name: {s['name']}")
            print(f"Issuer: {s['issuer']}")
            print(f"Secret (Base32): {b32_secret}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error: {e}")
