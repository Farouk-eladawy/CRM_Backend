import os

# ==============================================================================
# FTS Travels CRM - DATA PATH RESOLVER
# ==============================================================================
# This file centralizes the paths for all stateful data (databases, configs).
# It allows the system to run seamlessly on the old Windows server (root directory)
# and the new Docker architecture (data directory) without code conflicts.

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# If FTS_DATA_DIR is set (e.g., in Docker), use it. Otherwise, fallback to SCRIPT_DIR.
DATA_DIR = os.environ.get("FTS_DATA_DIR", SCRIPT_DIR)

def get_data_path(filename):
    """
    Returns the absolute path to a stateful file (like .db or .json).
    In Docker, this will point to /app/data/filename.
    On Windows, this will point to C:\...\filename.
    """
    primary_path = os.path.join(DATA_DIR, filename)
    fallback_path = os.path.join(SCRIPT_DIR, filename)
    
    # For config files, if they don't exist in the data dir but exist in the script dir, use the script dir one.
    if filename.endswith('.json') and not os.path.exists(primary_path) and os.path.exists(fallback_path):
        return fallback_path
        
    return primary_path

def ensure_data_dir():
    """Ensure the data directory exists."""
    if not os.path.exists(DATA_DIR):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
        except Exception:
            pass
