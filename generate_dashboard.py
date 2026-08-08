
import csv
import os

CSV_FILE = "Airtable Fields.csv"
OUTPUT_FILE = "OpenClaw_Operations_Dashboard/index.html"

# Icon Mapping
TYPE_ICONS = {
    "singleLineText": "fa-font",
    "multilineText": "fa-align-left",
    "number": "fa-hashtag",
    "currency": "fa-dollar-sign",
    "percent": "fa-percentage",
    "duration": "fa-stopwatch",
    "rating": "fa-star",
    "formula": "fa-calculator",
    "rollup": "fa-search",
    "count": "fa-hashtag",
    "lookup": "fa-search",
    "createdTime": "fa-calendar-plus",
    "lastModifiedTime": "fa-calendar-check",
    "autoNumber": "fa-list-ol",
    "barcode": "fa-barcode",
    "button": "fa-play-circle",
    "checkbox": "fa-check-square",
    "date": "fa-calendar",
    "dateTime": "fa-calendar-alt",
    "email": "fa-envelope",
    "phoneNumber": "fa-phone",
    "singleSelect": "fa-chevron-down",
    "multipleSelects": "fa-list-ul",
    "singleCollaborator": "fa-user",
    "multipleCollaborators": "fa-users",
    "createdBy": "fa-user-edit",
    "lastModifiedBy": "fa-user-clock",
    "externalSyncSource": "fa-sync",
    "multipleAttachments": "fa-paperclip",
    "multipleRecordLinks": "fa-exchange-alt",
    "url": "fa-link",
    "aiText": "fa-robot",
}

# 1. Read CSV
fields = []
try:
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields.append(row)
except Exception as e:
    print(f"Error reading CSV: {e}")
    # Fallback/Empty just in case
    fields = []

# 2. Generate HTML
html_start = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Operations Workspace</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
        
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f5f5f5;
            overflow: hidden;
        }

        /* Airtable-like Scrollbars */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        ::-webkit-scrollbar-thumb {
            background: #c1c1c1;
            border-radius: 5px;
            border: 2px solid #f1f1f1;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #a8a8a8;
        }

        /* Table Styling */
        .airtable-grid {
            display: block;
            white-space: nowrap;
            overflow: auto;
            height: calc(100vh - 90px);
            border: 1px solid #e2e8f0;
            background: white;
        }
        
        .airtable-header-cell {
            position: sticky;
            top: 0;
            background: #f8f9fa;
            border-bottom: 1px solid #d1d5db;
            border-right: 1px solid #e2e8f0;
            padding: 8px 12px;
            font-size: 13px;
            color: #4b5563;
            font-weight: 500;
            z-index: 10;
            display: inline-block;
            height: 32px;
            box-sizing: border-box;
            vertical-align: middle;
            min-width: 150px; /* Default width */
        }
        
        /* Specific widths based on type */
        .w-xs { min-width: 80px; }
        .w-sm { min-width: 120px; }
        .w-md { min-width: 180px; }
        .w-lg { min-width: 250px; }
        .w-xl { min-width: 350px; }

        .airtable-row {
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            width: max-content; /* Critical for horizontal scroll */
        }
        
        .airtable-row:hover {
            background-color: #f8fafc;
        }

        .airtable-cell {
            display: inline-block;
            padding: 6px 12px;
            border-right: 1px solid #e2e8f0;
            font-size: 13px;
            color: #1f2937;
            height: 32px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            vertical-align: middle;
            box-sizing: border-box;
            min-width: 150px; /* Default width */
        }

        /* Field Type Icons */
        .field-icon {
            color: #9ca3af;
            margin-right: 6px;
            font-size: 11px;
        }
        
        /* Sticky First Column Checkbox */
        .sticky-col-1 {
            position: sticky;
            left: 0;
            z-index: 20; /* Higher than normal cells, but lower than sidebar if needed */
            background: inherit; /* Match row background */
            border-right: 1px solid #d1d5db;
        }
        
        /* Ensure sticky header stays on top of sticky column */
        .airtable-header-cell.sticky-col-1 {
            z-index: 30;
            background: #f8f9fa;
        }

    </style>
</head>
<body class="flex h-screen w-screen text-gray-800">

    <!-- 1. LEFT SIDEBAR -->
    <div class="w-16 bg-[#333333] flex flex-col items-center py-4 text-white z-40 flex-shrink-0 shadow-lg">
        <div class="mb-6 w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center shadow-lg cursor-pointer hover:bg-blue-600 transition">
            <i class="fas fa-paw text-xl"></i>
        </div>
        
        <div class="space-y-4 flex flex-col items-center w-full">
            <div class="p-2 bg-gray-700 rounded-lg cursor-pointer relative group">
                <i class="fas fa-table text-lg text-white"></i>
                <div class="absolute left-14 top-2 bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap z-50 pointer-events-none">
                    Leads CRM
                </div>
            </div>
            <div class="p-2 text-gray-400 hover:text-white cursor-pointer relative group">
                <i class="fas fa-plane text-lg"></i>
                 <div class="absolute left-14 top-2 bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition whitespace-nowrap z-50 pointer-events-none">
                    Trips Catalog
                </div>
            </div>
        </div>

        <div class="mt-auto mb-4">
            <img src="https://ui-avatars.com/api/?name=Admin&background=random" class="w-8 h-8 rounded-full border-2 border-gray-600 cursor-pointer">
        </div>
    </div>

    <!-- 2. MAIN CONTENT -->
    <div class="flex-1 flex flex-col h-full overflow-hidden bg-white relative">
        
        <!-- Toolbar -->
        <div class="h-14 border-b border-gray-200 flex items-center justify-between px-4 bg-white shadow-sm z-30 relative">
            <div class="flex items-center gap-4">
                <div class="flex items-center gap-2 cursor-pointer hover:bg-gray-100 px-2 py-1 rounded">
                    <h2 class="font-bold text-lg text-gray-800">Leads CRM</h2>
                    <i class="fas fa-chevron-down text-xs text-gray-500"></i>
                </div>
                
                <div class="h-6 w-px bg-gray-300 mx-2"></div>

                <div class="flex bg-gray-100 rounded p-0.5">
                    <div class="px-3 py-1 bg-white shadow-sm rounded text-xs font-medium text-blue-600 flex items-center gap-2 cursor-pointer">
                        <i class="fas fa-th"></i> Grid View
                    </div>
                    <div class="px-3 py-1 text-xs font-medium text-gray-500 flex items-center gap-2 cursor-pointer hover:bg-gray-200 rounded">
                        <i class="fas fa-columns"></i> Kanban
                    </div>
                </div>
            </div>

            <div class="flex items-center gap-3">
                 <div class="flex items-center gap-1 text-gray-600 text-sm hidden md:flex">
                    <button class="hover:bg-gray-100 px-2 py-1 rounded flex items-center gap-1"><i class="fas fa-filter text-gray-400"></i> Filter</button>
                    <button class="hover:bg-gray-100 px-2 py-1 rounded flex items-center gap-1"><i class="fas fa-sort text-gray-400"></i> Sort</button>
                    <button class="hover:bg-gray-100 px-2 py-1 rounded flex items-center gap-1"><i class="fas fa-palette text-gray-400"></i> Color</button>
                </div>
                <div class="relative">
                    <i class="fas fa-search absolute left-2 top-2 text-gray-400 text-xs"></i>
                    <input type="text" placeholder="Find..." class="pl-7 pr-3 py-1 text-sm border border-gray-300 rounded-full focus:outline-none focus:border-blue-500 w-32 md:w-48 transition-all focus:w-60">
                </div>
                <button class="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700">Add Record</button>
            </div>
        </div>

        <!-- THE GRID -->
        <div class="airtable-grid flex-1 overflow-auto bg-white" id="grid-container">
            <!-- HEADERS ROW -->
            <div class="flex w-max bg-gray-50 border-b border-gray-300 sticky top-0 z-20">
                <!-- Checkbox Column -->
                <div class="airtable-header-cell sticky-col-1 w-xs text-center border-l-4 border-l-transparent">
                    <input type="checkbox">
                </div>
"""

# Generate Dynamic Headers
headers_html = ""
for field in fields:
    field_name = field.get('name', 'Unknown')
    field_type = field.get('type', 'singleLineText')
    icon = TYPE_ICONS.get(field_type, "fa-font") # Default icon
    
    # Determine Width based on type/name
    width_class = "w-md"
    if field_type in ['checkbox', 'number', 'currency', 'rating']: width_class = "w-xs"
    elif field_type in ['date', 'dateTime', 'phoneNumber', 'singleSelect']: width_class = "w-sm"
    elif field_type in ['multilineText', 'multipleRecordLinks', 'url']: width_class = "w-lg"
    
    headers_html += f"""
                <div class="airtable-header-cell {width_class}">
                    <i class="fas {icon} field-icon"></i> {field_name}
                </div>"""

html_middle = """
            </div>

            <!-- ROWS (Mock Data - 3 Rows) -->
            <div class="w-max">
"""

# Generate 3 Mock Rows
rows_html = ""
for i in range(1, 4):
    rows_html += f"""
                <!-- Row {i} -->
                <div class="airtable-row flex hover:bg-gray-50 group">
                    <div class="airtable-cell sticky-col-1 w-xs text-center border-l-4 border-l-transparent group-hover:bg-gray-100 font-bold text-gray-400 bg-white">
                        {i}
                    </div>
    """
    
    for field in fields:
        field_type = field.get('type', 'singleLineText')
        
        # Determine Width (Same logic as header)
        width_class = "w-md"
        if field_type in ['checkbox', 'number', 'currency', 'rating']: width_class = "w-xs"
        elif field_type in ['date', 'dateTime', 'phoneNumber', 'singleSelect']: width_class = "w-sm"
        elif field_type in ['multilineText', 'multipleRecordLinks', 'url']: width_class = "w-lg"
        
        # Mock Content
        content = "-"
        if field_type == 'singleLineText': content = "Text Value"
        elif field_type == 'multilineText': content = "Long text content..."
        elif field_type == 'date': content = "2026-02-25"
        elif field_type == 'dateTime': content = "2026-02-25 10:00"
        elif field_type == 'singleSelect': content = '<span class="bg-gray-100 px-2 py-0.5 rounded text-xs">Option 1</span>'
        elif field_type == 'checkbox': content = '<i class="far fa-square text-gray-300"></i>'
        elif field_type == 'number': content = "0"
        elif field_type == 'currency': content = "$0.00"
        elif field_type == 'button': content = '<button class="bg-gray-200 px-2 py-0.5 rounded text-xs hover:bg-gray-300">Click</button>'
        elif field_type == 'rating': content = '<i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i><i class="fas fa-star text-yellow-400"></i>'
        elif field_type == 'url': content = '<a href="#" class="text-blue-600 hover:underline text-xs">Link</a>'
        
        rows_html += f"""
                    <div class="airtable-cell {width_class}">
                        {content}
                    </div>"""
    
    rows_html += """
                </div>"""

html_end = """
            </div>
            
            <!-- Add Button Row -->
            <div class="border-b border-gray-200 p-2 text-gray-500 text-sm hover:bg-gray-50 cursor-pointer pl-10 sticky left-0">
                <i class="fas fa-plus mr-2"></i> Add Record
            </div>
        </div>

        <!-- Footer -->
        <div class="h-8 border-t bg-white flex items-center justify-between px-4 text-xs text-gray-500 z-30 relative">
            <div>3 records</div>
            <div class="flex items-center gap-4">
                <span><i class="fas fa-history"></i> Autosaved just now</span>
            </div>
        </div>
    </div>

    <!-- 3. RIGHT SIDEBAR (AI Assistant) -->
    <div class="w-[350px] bg-white border-l shadow-xl flex flex-col z-40 flex-shrink-0 transition-all duration-300" id="ai-sidebar">
        <!-- AI Header -->
        <div class="h-14 border-b flex items-center justify-between px-4 bg-gray-50">
            <div class="flex items-center gap-2">
                <div class="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white shadow-sm">
                    <i class="fas fa-robot text-sm"></i>
                </div>
                <div>
                    <h3 class="font-bold text-sm text-gray-800">OpenClaw Copilot</h3>
                    <div class="flex items-center gap-1">
                        <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
                        <span class="text-[10px] text-gray-500 uppercase tracking-wider">Connected</span>
                    </div>
                </div>
            </div>
            <button class="text-gray-400 hover:text-gray-600" onclick="document.getElementById('ai-sidebar').classList.toggle('hidden')"><i class="fas fa-times"></i></button>
        </div>

        <!-- Observer Insights (Live Feed) -->
        <div class="bg-indigo-50 p-3 border-b border-indigo-100">
            <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-indigo-900 flex items-center gap-1">
                    <i class="fas fa-eye text-indigo-500"></i> Live Observer
                </span>
                <span class="text-[10px] bg-white text-indigo-600 px-1.5 py-0.5 rounded border border-indigo-100 shadow-sm">Active</span>
            </div>
            <div class="space-y-2 max-h-32 overflow-y-auto" id="observer-feed">
                <!-- Log Item -->
                <div class="bg-white p-2 rounded border border-indigo-100 shadow-sm flex gap-2">
                    <div class="mt-0.5"><i class="fas fa-pen text-xs text-yellow-500"></i></div>
                    <div>
                        <div class="text-[10px] text-gray-400 mb-0.5">Just now • Manual Correction</div>
                        <p class="text-xs text-gray-700 leading-tight">System detected manual update on 'Pickup Time'.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Chat Area -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4 bg-white" id="chat-container">
            <!-- AI Welcome -->
            <div class="flex gap-3">
                <div class="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-1 text-indigo-600">
                    <i class="fas fa-robot text-xs"></i>
                </div>
                <div class="space-y-1">
                    <div class="text-xs text-gray-400 ml-1">OpenClaw • Now</div>
                    <div class="bg-gray-100 p-3 rounded-2xl rounded-tl-none text-sm text-gray-700 shadow-sm">
                        Hello! I am your AI assistant. How can I help you manage these bookings today?
                    </div>
                </div>
            </div>
        </div>

        <!-- Input Area -->
        <div class="p-4 border-t bg-white">
            <div class="relative shadow-sm group focus-within:ring-2 ring-indigo-500 rounded-xl">
                <textarea 
                    class="w-full bg-gray-50 border border-gray-200 rounded-xl pl-3 pr-10 py-3 text-sm focus:outline-none focus:bg-white resize-none transition-all" 
                    rows="1" 
                    placeholder="Ask OpenClaw..."
                    id="chat-input"
                ></textarea>
                <button class="absolute right-2 bottom-2 text-indigo-600 hover:bg-indigo-50 p-1.5 rounded-full transition-colors" onclick="sendMessage()">
                    <i class="fas fa-paper-plane"></i>
                </button>
            </div>
        </div>
    </div>

    <script>
        const chatInput = document.getElementById('chat-input');
        const chatContainer = document.getElementById('chat-container');
        const observerFeed = document.getElementById('observer-feed');
        const API_BASE = "http://localhost:18789"; // Change to your backend URL

        // 1. Load Data on Startup
        window.addEventListener('DOMContentLoaded', () => {
            fetchRecords();
            startObserverPolling();
        });

        async function fetchRecords() {
            try {
                const res = await fetch(`${API_BASE}/api/airtable/records`);
                const data = await res.json();
                if(data.status === 'success') {
                    renderGrid(data.records);
                }
            } catch(e) {
                console.error("Failed to fetch records:", e);
            }
        }

        function renderGrid(records) {
            // This is a placeholder. In a real React app, you'd map this.
            // For this static HTML demo, we'll just log it.
            console.log("Records Loaded:", records.length);
            // Ideally, clear .w-max rows and rebuild them here based on `records`
        }

        function startObserverPolling() {
            setInterval(async () => {
                try {
                    const res = await fetch(`${API_BASE}/api/observer/insights`);
                    const data = await res.json();
                    if(data.status === 'success') {
                        updateObserverFeed(data.insights);
                    }
                } catch(e) {
                    console.error("Observer poll failed:", e);
                }
            }, 5000); // Check every 5s
        }

        function updateObserverFeed(insights) {
            observerFeed.innerHTML = '';
            insights.slice().reverse().slice(0, 5).forEach(item => {
                const div = document.createElement('div');
                div.className = 'bg-white p-2 rounded border border-indigo-100 shadow-sm flex gap-2';
                div.innerHTML = `
                    <div class="mt-0.5"><i class="fas fa-pen text-xs text-yellow-500"></i></div>
                    <div>
                        <div class="text-[10px] text-gray-400 mb-0.5">${item.timestamp}</div>
                        <p class="text-xs text-gray-700 leading-tight">${item.content}</p>
                    </div>
                `;
                observerFeed.appendChild(div);
            });
        }

        chatInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        async function sendMessage() {
            const text = chatInput.value.trim();
            if (!text) return;

            // User Message
            appendMessage('user', text);
            chatInput.value = '';

            // Send to Backend
            try {
                const res = await fetch(`${API_BASE}/agent/message`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({user: 'DashboardUser', message: text})
                });
                const data = await res.json();
                appendMessage('ai', data.reply);
            } catch(e) {
                appendMessage('ai', "Error connecting to AI.");
            }
        }

        function appendMessage(sender, text) {
            const div = document.createElement('div');
            
            if (sender === 'user') {
                div.className = 'flex gap-3 flex-row-reverse';
                div.innerHTML = `
                    <div class="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 mt-1 text-gray-600">
                        <i class="fas fa-user text-xs"></i>
                    </div>
                    <div class="space-y-1 text-right">
                         <div class="text-xs text-gray-400 mr-1">You • Now</div>
                        <div class="bg-indigo-600 p-3 rounded-2xl rounded-tr-none text-sm text-white text-left shadow-sm">
                            ${text}
                        </div>
                    </div>
                `;
            } else {
                div.className = 'flex gap-3';
                div.innerHTML = `
                    <div class="w-6 h-6 rounded-full bg-indigo-100 flex items-center justify-center flex-shrink-0 mt-1 text-indigo-600">
                        <i class="fas fa-robot text-xs"></i>
                    </div>
                    <div class="space-y-1">
                        <div class="text-xs text-gray-400 ml-1">OpenClaw • Now</div>
                        <div class="bg-gray-100 p-3 rounded-2xl rounded-tl-none text-sm text-gray-700 shadow-sm">
                            ${text}
                        </div>
                    </div>
                `;
            }
            
            chatContainer.appendChild(div);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    </script>

</body>
</html>
"""

# 3. Write Output
with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write(html_start + headers_html + html_middle + rows_html + html_end)

print(f"Successfully generated {OUTPUT_FILE} with {len(fields)} columns.")
