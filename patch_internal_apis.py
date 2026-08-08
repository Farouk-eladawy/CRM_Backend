import re

with open('ai_agent.py', 'r', encoding='utf-8') as f:
    content = f.read()

if '/api/users' not in content:
    patch = """
        # --- USERS API ---
        @app.route('/api/users', methods=['GET'])
        def api_get_users():
            try:
                import json, os
                if os.path.exists('users.json'):
                    users = json.load(open('users.json', 'r', encoding='utf-8'))
                else:
                    users = []
                return jsonify({"status": "success", "data": users}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route('/api/users', methods=['POST'])
        def api_save_users():
            try:
                import json
                data = request.json
                json.dump(data.get('users', []), open('users.json', 'w', encoding='utf-8'), indent=2)
                return jsonify({"status": "success"}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        # --- INTERNAL CHAT API ---
        @app.route('/api/internal/groups', methods=['GET', 'POST'])
        def api_internal_groups():
            import internal_chat_db
            try:
                if request.method == 'GET':
                    groups = internal_chat_db.get_all_groups()
                    return jsonify({"status": "success", "data": groups}), 200
                elif request.method == 'POST':
                    data = request.json
                    group_id = internal_chat_db.create_group(data['name'], data['created_by'], data['member_ids'])
                    return jsonify({"status": "success", "group_id": group_id}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
                
        @app.route('/api/internal/groups/<group_id>', methods=['PUT'])
        def api_update_internal_group(group_id):
            import internal_chat_db
            try:
                data = request.json
                internal_chat_db.update_group_members(group_id, data['member_ids'])
                return jsonify({"status": "success"}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @app.route('/api/internal/messages', methods=['GET', 'POST'])
        def api_internal_messages():
            import internal_chat_db
            try:
                if request.method == 'GET':
                    chat_id = request.args.get('chat_id')
                    is_group = request.args.get('is_group') == 'true'
                    user1 = request.args.get('user1')
                    user2 = request.args.get('user2')
                    messages = internal_chat_db.get_messages(chat_id, is_group, user1, user2)
                    return jsonify({"status": "success", "data": messages}), 200
                elif request.method == 'POST':
                    data = request.json
                    msg_id = internal_chat_db.send_message(data['chat_id'], data['sender_id'], data['text'], data.get('is_group', False))
                    return jsonify({"status": "success", "msg_id": msg_id}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

"""
    # Insert right before @app.route('/openapi.json'
    content = content.replace("        @app.route('/openapi.json'", patch + "        @app.route('/openapi.json'")
    
    with open('ai_agent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched successfully!")
else:
    print("Already patched.")
