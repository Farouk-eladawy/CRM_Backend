import os
import zipfile

def zip_project(output_filename):
    # Get the current directory (project root)
    root_dir = os.getcwd()
    
    # Files/Folders to exclude
    EXCLUDE_FILES = [
        "All mail Including Spam.mbox",
        output_filename, # Don't zip the zip file itself!
        "knowledge.db", # Usually large and auto-generated
        "agent_log.txt", # Logs
        "simulator.log"
    ]
    
    EXCLUDE_DIRS = [
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        ".idea",
        ".vscode"
    ]

    print(f"Zipping project to {output_filename}...")
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(root_dir):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES:
                    print(f"Skipping excluded file: {file}")
                    continue
                
                if file.endswith(".pyc") or file.endswith(".DS_Store"):
                    continue

                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, root_dir)
                
                print(f"Adding: {arcname}")
                zipf.write(file_path, arcname)

    print(f"\nSuccessfully created {output_filename}")

if __name__ == "__main__":
    zip_project("AIAgentProject_Backup.zip")
