# Airtable Phone Corrector

This tool automatically standardizes phone numbers in your Airtable database to ensure the AI Agent can find them easily.

## Features
- **Removes Spaces & Symbols**: Converts formats like `+44 7599 888 526` to `+447599888526`.
- **Validates Numbers**: Uses Google's `phonenumbers` library to ensure validity.
- **AI Extraction**: Uses DeepSeek/OpenAI to extract numbers from messy text (e.g. "010xxxx (Husband)").
- **Safe Updates**: Only updates records if the number format actually changes.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   Ensure your `.env` file (in the root or parent folder) has:
   ```env
   AIRTABLE_TOKEN=your_token
   AIRTABLE_BASE_ID=your_base_id
   AIRTABLE_TABLE=List
   DEEP_SEEK_API_KEY=your_key  # Optional, for AI extraction
   ```

## Usage

Run the script manually to clean all existing records:

```bash
python phone_corrector.py
```

## Automation

You can schedule this script to run daily using Windows Task Scheduler, or trigger it via a webhook if you convert it to a Flask app.
