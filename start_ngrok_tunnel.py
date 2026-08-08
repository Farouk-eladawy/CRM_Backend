
import sys
import os
import time
from pyngrok import ngrok, conf

# Add the project root directory to Python path if needed
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

def start_ngrok():
    print("Initializing ngrok tunnel for port 5001...")
    
    # Kill any existing ngrok processes to avoid conflicts (Aggressive Windows Kill)
    print("Cleaning up existing ngrok processes...")
    try:
        if os.name == 'nt':
            os.system("taskkill /F /IM ngrok.exe >nul 2>&1")
        else:
            os.system("pkill -9 ngrok")
    except Exception:
        pass
        
    ngrok.kill()
    time.sleep(2) # Give it a moment to release ports
    
    # Set the auth token provided by user
    try:
        ngrok.set_auth_token("35ICtTbfJyBDDzCSvWHPR5Vhrc0_5pM1AZd1dgux1vgw43od2")
        print("Authenticated with ngrok successfully.")
    except Exception as e:
        print(f"Warning: Failed to set auth token: {e}")
    
    try:
        # Open a HTTP tunnel on the default port 5001
        # verify_token is not needed for ngrok itself, but for Meta verification
        public_url = ngrok.connect(5001).public_url
        print(f"\n✅ Ngrok Tunnel Started!")
        print(f"🔴 Copy this URL to Meta Developer Dashboard:")
        print(f"   Callback URL: {public_url}/webhook")
        print(f"   Verify Token: EAALCJ9i07dIBQe5BnokFM5gUCDXSFTfj8p98kfBFXhsHa0BDDZCeiXIQLZCWy0CgaOaGPvZCV4yzolGCLkLpcD1H5oOpLbYS3yWGXZBt5yRjxrFkHlqsOfTsxRgj8XNMsd5HetMz0SSBZB9GDgZBUU2BSR33BHllKKZAS7WBLquUQmTewslv8ZCOxMkWdvY8QQZDZD")
        print(f"\nPress Ctrl+C to stop the tunnel (Keep this window open while testing).")
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping ngrok...")
            ngrok.kill()

    except Exception as e:
        print(f"❌ Error starting ngrok: {e}")
        print("Tip: If you haven't set up your ngrok auth token, run: ngrok config add-authtoken <YOUR_TOKEN>")

if __name__ == "__main__":
    start_ngrok()
