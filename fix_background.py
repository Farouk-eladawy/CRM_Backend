import os
with open('runtime/pi_brain/background_task_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# I need to add an elif block for develop_new_capability
new_handler = '''
        elif action_type == "develop_new_capability":
            try:
                tool_name = payload.get("tool_name", "unknown_tool")
                tool_desc = payload.get("tool_description", "")
                param_schema = payload.get("parameters_schema", {})
                python_code = payload.get("python_code", "")
                
                if not tool_name or not python_code:
                    raise ValueError("tool_name and python_code are required")
                
                # 1. Save Schema
                schema_dir = os.path.join("runtime", "pi_brain", "schemas")
                os.makedirs(schema_dir, exist_ok=True)
                schema_path = os.path.join(schema_dir, f"{tool_name}_schema.json")
                
                schema_obj = {
                    "name": tool_name,
                    "description": tool_desc,
                    "parameters": {
                        "type": "object",
                        "properties": param_schema.get("properties", param_schema) if "properties" in param_schema else param_schema,
                        "required": param_schema.get("required", [])
                    }
                }
                
                with open(schema_path, 'w', encoding='utf-8') as sf:
                    json.dump(schema_obj, sf, ensure_ascii=False, indent=2)
                
                # 2. Save Python Handler
                handlers_dir = os.path.join("runtime", "pi_brain", "dynamic_handlers")
                os.makedirs(handlers_dir, exist_ok=True)
                handler_path = os.path.join(handlers_dir, f"{tool_name}.py")
                
                with open(handler_path, 'w', encoding='utf-8') as hf:
                    hf.write(python_code)
                
                result["status"] = "success"
                result["message"] = f"تم إنشاء الأداة الجديدة '{tool_name}' بنجاح وهي الآن جاهزة للاستخدام في النظام."
            except Exception as e:
                result["status"] = "error"
                result["message"] = f"Failed to develop new capability: {e}"
                logging.error(f"Capability Dev Error: {e}")
'''

# Find a good place to inject this. After lif action_type == "query_records": block
# Let's just find lif action_type in ["update_record", "update_airtable"]: and insert it before that.

if "elif action_type == \"develop_new_capability\":" not in content:
    content = content.replace('elif action_type in ["update_record", "update_airtable"]:', new_handler + '\n        elif action_type in ["update_record", "update_airtable"]:')

with open('runtime/pi_brain/background_task_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("SUCCESS added develop_new_capability handler")
