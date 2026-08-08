import os
import re

file_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\ai_agent.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Modify _extract_evolution_message_text to also look for audio Message
old_func = """        def _extract_evolution_message_text(data):
            try:
                if isinstance(data, dict):
                    conversation = data.get("conversation")
                    if isinstance(conversation, str) and conversation.strip():
                        return conversation.strip()
                    ext_text = data.get("extendedTextMessage") or data.get("extendedText")
                    if isinstance(ext_text, dict):
                        text = ext_text.get("text")
                        if isinstance(text, str) and text.strip():
                            return text.strip()
                    for key in ("text", "caption", "body", "message"):
                        value = data.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                    for value in data.values():
                        found = _extract_evolution_message_text(value)
                        if found:
                            return found
                elif isinstance(data, list):
                    for item in data:
                        found = _extract_evolution_message_text(item)
                        if found:
                            return found
            except Exception:
                return ""
            return \"\""""

new_func = """        def _extract_evolution_message_text(data):
            try:
                if isinstance(data, dict):
                    # Check for audio message (Evolution API format)
                    audio_message = data.get("audioMessage")
                    if isinstance(audio_message, dict) and audio_message.get("url"):
                        import logging
                        try:
                            # Try to download and transcribe the audio URL
                            # Since we are inside a static method, we'll need to instantiate the agent or use the URL directly
                            url = audio_message.get("url")
                            mimetype = audio_message.get("mimetype", "")
                            
                            # Simple approach: Return a special marker that we'll catch later
                            return f"__AUDIO_URL__:{url}"
                        except Exception as e:
                            logging.error(f"Error handling internal audio message: {e}")
                            return "[Audio Message: Failed to process]"

                    conversation = data.get("conversation")
                    if isinstance(conversation, str) and conversation.strip():
                        return conversation.strip()
                    ext_text = data.get("extendedTextMessage") or data.get("extendedText")
                    if isinstance(ext_text, dict):
                        text = ext_text.get("text")
                        if isinstance(text, str) and text.strip():
                            return text.strip()
                    for key in ("text", "caption", "body", "message"):
                        value = data.get(key)
                        if isinstance(value, str) and value.strip():
                            return value.strip()
                    for value in data.values():
                        found = _extract_evolution_message_text(value)
                        if found:
                            return found
                elif isinstance(data, list):
                    for item in data:
                        found = _extract_evolution_message_text(item)
                        if found:
                            return found
            except Exception:
                return ""
            return \"\""""

content = content.replace(old_func, new_func)

# Also intercept the marker in the webhook processing
webhook_old = """                is_message_event = any(
                    token in event_name
                    for token in (
                        "messages.upsert",
                        "message.upsert",
                        "messages-update",
                        "messages_set",
                        "message",
                    )
                ) or bool(incoming_text)

                if is_message_event and not bool(from_me) and sender_phone and incoming_text:"""

webhook_new = """                # Process audio URL marker if present
                if incoming_text and incoming_text.startswith("__AUDIO_URL__:"):
                    audio_url = incoming_text.split(":", 1)[1]
                    try:
                        import requests, tempfile, os
                        import soundfile as sf
                        import speech_recognition as sr
                        
                        cfg = _load_internal_whatsapp_config()
                        api_key = str((cfg or {}).get("apiKey") or "").strip()
                        
                        headers = {"apikey": api_key}
                        media_res = requests.get(audio_url, headers=headers, timeout=20)
                        
                        if media_res.status_code == 200:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
                                tmp_ogg.write(media_res.content)
                                tmp_ogg_path = tmp_ogg.name
                                
                            tmp_wav_path = tmp_ogg_path + ".wav"
                            try:
                                data, samplerate = sf.read(tmp_ogg_path)
                                sf.write(tmp_wav_path, data, samplerate)
                                
                                recognizer = sr.Recognizer()
                                with sr.AudioFile(tmp_wav_path) as source:
                                    audio_data = recognizer.record(source)
                                    transcription = recognizer.recognize_google(audio_data, language="ar-EG")
                                    incoming_text = transcription
                                    logging.info(f"Internal Audio Transcribed: {transcription}")
                            except sr.UnknownValueError:
                                incoming_text = "[رسالة صوتية غير مفهومة]"
                            except Exception as e:
                                logging.error(f"Error transcribing internal audio: {e}")
                                incoming_text = "[خطأ في معالجة الرسالة الصوتية]"
                            finally:
                                if os.path.exists(tmp_ogg_path): os.remove(tmp_ogg_path)
                                if os.path.exists(tmp_wav_path): os.remove(tmp_wav_path)
                        else:
                            incoming_text = "[خطأ في تحميل الرسالة الصوتية]"
                    except Exception as e:
                        logging.error(f"Error downloading internal audio: {e}")
                        incoming_text = "[خطأ في تحميل الرسالة الصوتية]"

                is_message_event = any(
                    token in event_name
                    for token in (
                        "messages.upsert",
                        "message.upsert",
                        "messages-update",
                        "messages_set",
                        "message",
                    )
                ) or bool(incoming_text)

                if is_message_event and not bool(from_me) and sender_phone and incoming_text:"""

content = content.replace(webhook_old, webhook_new)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully.")
