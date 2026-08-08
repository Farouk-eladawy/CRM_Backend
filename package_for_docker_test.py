import os
import shutil
import zipfile
from datetime import datetime

def package_project():
    print("🚀 بدء تجهيز حزمة المحاكاة (Docker Test Package)...")
    
    # تحديد مسار المشروع واسم الملف المضغوط
    base_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"Docker_Test_Env_{timestamp}.zip"
    zip_filepath = os.path.join(base_dir, zip_filename)
    
    # القوائم البيضاء (ما الذي يجب ضغطه فقط)
    files_to_include = [
        "ai_agent.py",
        "airtable_mirror.py",
        "background_task_engine.py",
        "fts_paths.py",
        "requirements.txt"
    ]
    
    data_files_to_include = [
        "chat_history.db",
        "airtable_mirror.db",
        "knowledge.db",
        "users.json",
        "config.json",
        "credentials.json",
        "token.json",
        "token_sales.json",
        "learned_corrections.json",
        "system_config.json"
    ]

    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # 1. إضافة ملفات Docker
            print("📦 جاري إنشاء ملفات Docker الأساسية...")
            dockerfile_content = """FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FTS_DATA_DIR=/app/data
CMD ["python", "ai_agent.py"]
"""
            docker_compose_content = """version: '3.8'
services:
  fts-teacher:
    build: .
    ports:
      - "5001:5001"
    volumes:
      - ./data:/app/data
    environment:
      - FTS_DATA_DIR=/app/data
    restart: always

  background-engine:
    build: .
    command: python background_task_engine.py
    volumes:
      - ./data:/app/data
    environment:
      - FTS_DATA_DIR=/app/data
    restart: always
"""
            zipf.writestr("Dockerfile", dockerfile_content)
            zipf.writestr("docker-compose.yml", docker_compose_content)

            # 2. إضافة الأكواد الأساسية
            print("📦 جاري إضافة أكواد البايثون الأساسية...")
            for file in files_to_include:
                file_path = os.path.join(base_dir, file)
                if os.path.exists(file_path):
                    zipf.write(file_path, file)
                else:
                    print(f"⚠️ تحذير: الملف {file} غير موجود.")

            # 3. إضافة واجهة التحكم (Frontend)
            print("📦 جاري إضافة واجهة التحكم (Frontend)...")
            frontend_dir = os.path.join(base_dir, "frontend_dashboard")
            if os.path.exists(frontend_dir):
                for root, dirs, files in os.walk(frontend_dir):
                    dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', '.git']]
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, base_dir)
                        zipf.write(file_path, arcname)

            # 4. إضافة قواعد البيانات والإعدادات داخل مجلد 'data'
            print("📦 جاري أخذ نسخة آمنة من قواعد البيانات والإعدادات...")
            for file in data_files_to_include:
                file_path = os.path.join(base_dir, file)
                if os.path.exists(file_path):
                    arcname = f"data/{file}"
                    zipf.write(file_path, arcname)

        print(f"✅ تمت العملية بنجاح! تم إنشاء الملف: {zip_filename}")
        print(f"حجم الملف: {os.path.getsize(zip_filepath) / (1024 * 1024):.2f} ميجابايت")
        return zip_filename
        
    except Exception as e:
        print(f"❌ حدث خطأ أثناء الضغط: {e}")
        return None

if __name__ == "__main__":
    package_project()
