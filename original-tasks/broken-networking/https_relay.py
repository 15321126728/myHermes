#!/usr/bin/env python3
"""
HTTPS Relay Proxy - listens on localhost:8080, accepts plain HTTP,
connects to the target via HTTPS (port 443) to bypass transparent proxy on port 80.
"""
import socket
import ssl
import sys
import urllib.parse
import threading

def handle_client(conn, addr):
    try:
        data = conn.recv(16384)
        if not data:
            return
        
        request_text = data.decode('utf-8', errors='replace')
        lines = request_text.split('\r\n')
        
        if not lines:
            return
        
        # Parse the request line: GET /path HTTP/1.1
        request_line = lines[0]
        parts = request_line.split(' ')
        if len(parts) < 2:
            return
        
        method = parts[0]
        
        # Extract host from the URL or Host header
        url = parts[1]
        
        # Parse the URL to get the host
        if url.startswith('http://') or url.startswith('https://'):
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
        else:
            # Relative URL, need to get host from Host header
            host = None
            for line in lines[1:]:
                if line.lower().startswith('host:'):
                    host = line.split(':', 1)[1].strip()
                    break
            path = url
        
        if not host:
            # Remove port from host if present
            host = 'example.com'
        
        # Remove port if present in host
        if ':' in host:
            host = host.split(':')[0]
        
        # Connect via HTTPS (port 443) which bypasses the transparent proxy
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            ssock = ctx.wrap_socket(sock, server_hostname=host)
            ssock.connect((host, 443))
            
            # Forward the request, changing http:// to https:// in the URL
            # and using the absolute path
            new_request = f"{method} https://{host}{path} HTTP/1.1\r\n"
            for line in lines[1:]:
                # Remove Proxy-Connection header
                if line.lower().startswith('proxy-connection'):
                    continue
                # Change http:// to https:// in forwarded headers  
                if line.startswith('GET ') or line.startswith('POST ') or line.startswith('HEAD '):
                    continue
                new_request += line + '\r\n'
            new_request += '\r\n'
            
            ssock.sendall(new_request.encode())
            
            # Read the response
            response = b''
            while True:
                try:
                    chunk = ssock.recv(65536)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
                except ssl.SSLEOFError:
                    break
            
            ssock.close()
            
            # Send the response back to the client
            conn.sendall(response)
            
        except Exception as e:
            error_resp = f"HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nRelay error: {e}"
            conn.sendall(error_resp.encode())
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
    finally:
        try:
            conn.close()
        except:
            pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 8080))
    server.listen(50)
    print("HTTPS Relay Proxy listening on 127.0.0.1:8080", file=sys.stderr)
    
    while True:
        conn, addr = server.accept()
        t = threading.Thread(target=handle_client, args=(conn, addr))
        t.daemon = True
        t.start()

if __name__ == '__main__':
    main()
