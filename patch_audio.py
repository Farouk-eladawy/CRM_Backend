import os

file_path = r"C:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\ai_agent.py"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add download_and_transcribe_audio after download_whatsapp_media_base64
func_to_insert = """
    def download_and_transcribe_audio(self, media_id):
        \"\"\"
        Downloads a WhatsApp audio message and transcribes it using Google Web Speech API.
        \"\"\"
        try:
            import requests, tempfile, os
            import soundfile as sf
            import speech_recognition as sr
            import logging
            
            access_token = self._get_whatsapp_access_token()
            if not access_token:
                return None, "[Audio Error: No Access Token]"
            
            url = f"https://graph.facebook.com/v18.0/{media_id}"
            headers = {"Authorization": f"Bearer {access_token}"}
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                return None, f"[Audio Error: Failed to get URL - {res.status_code}]"
            
            media_url = res.json().get('url')
            if not media_url:
                return None, "[Audio Error: Empty media URL]"
                
            media_res = requests.get(media_url, headers=headers, timeout=20)
            if media_res.status_code != 200:
                return None, f"[Audio Error: Failed to download media - {media_res.status_code}]"
                
            # Save the raw audio (usually OGG/OPUS) to a temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
                tmp_ogg.write(media_res.content)
                tmp_ogg_path = tmp_ogg.name
                
            tmp_wav_path = tmp_ogg_path + ".wav"
            
            try:
                # Convert OGG to WAV using soundfile
                data, samplerate = sf.read(tmp_ogg_path)
                sf.write(tmp_wav_path, data, samplerate)
                
                # Transcribe using SpeechRecognition
                recognizer = sr.Recognizer()
                with sr.AudioFile(tmp_wav_path) as source:
                    audio_data = recognizer.record(source)
                    # Use Google Web Speech API (supports Arabic "ar-EG")
                    text = recognizer.recognize_google(audio_data, language="ar-EG")
                    return text, None
            except sr.UnknownValueError:
                return None, "[Audio Error: Could not understand audio]"
            except sr.RequestError as e:
                return None, f"[Audio Error: Google API error - {e}]"
            except Exception as e:
                logging.error(f"Error during transcription: {e}")
                return None, f"[Audio Error: Conversion/Transcription failed - {e}]"
            finally:
                # Clean up temp files
                if os.path.exists(tmp_ogg_path):
                    os.remove(tmp_ogg_path)
                if os.path.exists(tmp_wav_path):
                    os.remove(tmp_wav_path)
                    
        except Exception as e:
            logging.error(f"Error in download_and_transcribe_audio for {media_id}: {e}")
            return None, f"[Audio Error: {str(e)}]"
"""

target_str = """            return f"data:{content_type};base64,{b64}"
        except Exception as e:
            logging.error(f"Error downloading media {media_id} for AI Vision: {e}")
            return None"""

if func_to_insert not in content:
    content = content.replace(target_str, target_str + "\n" + func_to_insert)

# 2. Modify the webhook part
webhook_old = """                            elif msg_type == 'audio':
                                audio_id = msg.get('audio', {}).get('id', '')
                                msg_body = f"[Customer sent an audio message. Audio ID: {audio_id}]"
                                logging.info(f"Received Audio from {sender_name}. ID: {audio_id}")"""

webhook_new = """                            elif msg_type == 'audio':
                                audio_id = msg.get('audio', {}).get('id', '')
                                transcription, error = self.download_and_transcribe_audio(audio_id)
                                if transcription:
                                    msg_body = f"[رسالة صوتية مفرغة]: {transcription}"
                                else:
                                    msg_body = f"[Customer sent an audio message. Audio ID: {audio_id}] {error or ''}"
                                logging.info(f"Received Audio from {sender_name}. Transcription: {msg_body}")"""

content = content.replace(webhook_old, webhook_new)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully.")
