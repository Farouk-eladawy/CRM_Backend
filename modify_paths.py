import os

def modify_file(filepath):
    if not os.path.exists(filepath):
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Add import if not exists
    if 'from fts_paths import get_data_path' not in content:
        content = content.replace('import os\n', 'import os\nfrom fts_paths import get_data_path, DATA_DIR\n', 1)

    replacements = [
        ("'chat_history.db'", "get_data_path('chat_history.db')"),
        ('"chat_history.db"', "get_data_path('chat_history.db')"),
        ("'users.json'", "get_data_path('users.json')"),
        ('"users.json"', "get_data_path('users.json')"),
        ("'config.json'", "get_data_path('config.json')"),
        ('"config.json"', "get_data_path('config.json')"),
        ("'credentials.json'", "get_data_path('credentials.json')"),
        ('"credentials.json"', "get_data_path('credentials.json')"),
        ("'token.json'", "get_data_path('token.json')"),
        ('"token.json"', "get_data_path('token.json')"),
        ("'token_sales.json'", "get_data_path('token_sales.json')"),
        ('"token_sales.json"', "get_data_path('token_sales.json')"),
        ("'learned_corrections.json'", "get_data_path('learned_corrections.json')"),
        ('"learned_corrections.json"', "get_data_path('learned_corrections.json')"),
        ("'system_config.json'", "get_data_path('system_config.json')"),
        ('"system_config.json"', "get_data_path('system_config.json')"),
        ("os.path.join(SCRIPT_DIR, 'config.json')", "get_data_path('config.json')"),
        ('os.path.join(SCRIPT_DIR, "config.json")', "get_data_path('config.json')"),
        ("os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')", "get_data_path('config.json')"),
        ('os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")', "get_data_path('users.json')"),
        ('os.path.join(os.getcwd(), "users.json")', "get_data_path('users.json')"),
        ('os.path.join(SCRIPT_DIR, "airtable_mirror.db")', "get_data_path('airtable_mirror.db')"),
        ('os.path.join(os.path.dirname(os.path.abspath(__file__)), "airtable_mirror.db")', "get_data_path('airtable_mirror.db')")
    ]

    for old, new in replacements:
        content = content.replace(old, new)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
modify_file('ai_agent.py')
modify_file('airtable_mirror.py')
modify_file('background_task_engine.py')
print('Paths modified successfully.')
