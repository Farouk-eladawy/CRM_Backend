with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

dynamic_execution = '''
                    else:
                        # Check if there's a dynamic handler
                        handlers_dir = os.path.join("runtime", "pi_brain", "dynamic_handlers")
                        handler_path = os.path.join(handlers_dir, f"{action_type}.py")
                        payload = action.get("payload", {})
                        if os.path.exists(handler_path):
                            try:
                                import importlib.util
                                import sys
                                
                                spec = importlib.util.spec_from_file_location(f"dynamic_{action_type}", handler_path)
                                mod = importlib.util.module_from_spec(spec)
                                sys.modules[f"dynamic_{action_type}"] = mod
                                spec.loader.exec_module(mod)
                                
                                if hasattr(mod, f"handle_{action_type}"):
                                    handler_func = getattr(mod, f"handle_{action_type}")
                                    dynamic_result = handler_func(payload, actor_name)
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": dynamic_result.get("status", "executed"),
                                        "message": dynamic_result.get("message", "Dynamic action executed.")
                                    })
                                else:
                                    result["actions_results"].append({
                                        "action_type": action_type,
                                        "status": "error",
                                        "message": f"Dynamic handler missing 'handle_{action_type}'."
                                    })
                            except Exception as e:
                                result["actions_results"].append({
                                    "action_type": action_type,
                                    "status": "error",
                                    "message": f"Dynamic execution failed: {e}"
                                })
                        else:
                            # محاكاة التنفيذ للإجراءات الأخرى
                            result["actions_results"].append({
                                "action_type": action_type,
                                "status": "executed",
                                "message": f"Action {action_type} processed safely via Guard (No dynamic handler found)."
                            })
'''

old_block = '''                    else:
                        # محاكاة التنفيذ للإجراءات الأخرى
                        result["actions_results"].append({
                            "action_type": action_type,
                            "status": "executed",
                            "message": "Action processed safely via Guard"
                        })'''

if old_block in content:
    content = content.replace(old_block, dynamic_execution.strip('\n'))
    with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS replaced else block")
else:
    print("FAILED to find else block")
