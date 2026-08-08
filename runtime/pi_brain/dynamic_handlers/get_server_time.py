def handle_get_server_time(payload, actor_name):
    import datetime
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {
        "status": "success",
        "message": f"Server time is {current_time}"
    }