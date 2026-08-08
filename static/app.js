// No hardcoded API URL needed! We use relative paths.
const API_URL = ''; 

// State
let activeChat = null;
let commandMode = false;

// DOM Elements
const appContainer = document.getElementById('app-container');
const loginModal = document.getElementById('login-modal');
const loginBtn = document.getElementById('login-btn');
const chatList = document.getElementById('chat-list');
const chatContainer = document.getElementById('chat-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const commandToggle = document.getElementById('command-mode-toggle');
const modeLabel = document.getElementById('mode-label');

// --- Auth (Simplified for Simulator) ---
loginBtn.addEventListener('click', () => {
    loginModal.style.display = 'none';
    appContainer.style.display = 'flex';
    // Dummy chats for testing
    const chats = [
        { phone: '123456789', last_message: 'Hello', timestamp: new Date() },
        { phone: 'COMMAND_LOG', last_message: 'System Ready', timestamp: new Date() }
    ];
    renderChatList(chats);
    
    // Auto-select first chat to prevent confusion
    if (chats.length > 0) {
        selectChat(chats[0].phone);
    }
});

// --- Command Mode Toggle ---
commandToggle.addEventListener('change', (e) => {
    commandMode = e.target.checked;
    modeLabel.textContent = commandMode ? 'Command' : 'Chat';
    userInput.placeholder = commandMode ? 'Enter command (e.g., /invoice ...)' : 'Type a message';
    
    if (commandMode) {
        document.body.classList.add('command-mode-active');
    } else {
        document.body.classList.remove('command-mode-active');
    }
});

// --- Chat List ---
function renderChatList(chats) {
    chatList.innerHTML = '';
    chats.forEach(chat => {
        const div = document.createElement('div');
        div.className = `chat-item ${activeChat === chat.phone ? 'active' : ''}`;
        div.onclick = () => selectChat(chat.phone);
        
        div.innerHTML = `
            <div class="avatar-circle">${chat.phone[0]}</div>
            <div class="chat-info">
                <div class="chat-top">
                    <span class="chat-name">${chat.phone}</span>
                </div>
                <div class="chat-bottom">
                    <span class="chat-preview">${chat.last_message}</span>
                </div>
            </div>
        `;
        chatList.appendChild(div);
    });
}

function selectChat(phone) {
    activeChat = phone;
    document.getElementById('header-name').textContent = phone;
    document.getElementById('header-status').textContent = 'Online';
    chatContainer.innerHTML = ''; // Clear for now
    
    // Welcome message
    addMessageToUI("Chat loaded with " + phone, 'system', new Date());
    
    // Update active class in list
    document.querySelectorAll('.chat-item').forEach(el => {
        el.classList.remove('active');
        if (el.querySelector('.chat-name').textContent === phone) {
            el.classList.add('active');
        }
    });
}

// --- Messaging ---
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text || !activeChat) return;
    
    // Add User Message to UI
    addMessageToUI(text, 'user', new Date());
    userInput.value = '';
    
    // Determine Endpoint based on Mode
    const payload = {
        user: activeChat,
        message: commandMode ? `CMD: ${text}` : text
    };
    
    try {
        const res = await fetch(`${API_URL}/agent/message`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const data = await res.json();
        
        if (data.status === 'success') {
            // Add AI Reply
            addMessageToUI(data.reply, 'ai', new Date(), true); // true = enable editing
        } else {
            addMessageToUI("Error: " + data.message, 'system', new Date());
        }
        
    } catch (e) {
        console.error(e);
        addMessageToUI("Connection Error to OpenClaw Core", 'system', new Date());
    }
}

// --- UI Helpers ---
function addMessageToUI(text, type, timestamp, editable = false) {
    const div = document.createElement('div');
    div.className = `message ${type}`;
    
    const time = new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    let contentHtml = formatText(text);
    
    // If editable (AI response), add edit button
    let actionsHtml = '';
    if (editable && type === 'ai') {
        actionsHtml = `
            <div class="msg-actions">
                <button class="edit-btn" onclick="editMessage(this)">✏️ Correct & Learn</button>
            </div>
        `;
    }
    
    div.innerHTML = `
        <div class="bubble">
            <div class="msg-content">${contentHtml}</div>
            ${actionsHtml}
            <div class="msg-meta">${time}</div>
        </div>
    `;
    
    chatContainer.appendChild(div);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function formatText(text) {
    return text.replace(/\n/g, '<br>');
}

// --- Feedback / Learning ---
window.editMessage = function(btn) {
    const bubble = btn.closest('.bubble');
    const contentDiv = bubble.querySelector('.msg-content');
    const oldText = contentDiv.innerText; // Get text without HTML
    
    // Replace with textarea
    const textarea = document.createElement('textarea');
    textarea.value = oldText;
    textarea.className = 'edit-textarea';
    
    const saveBtn = document.createElement('button');
    saveBtn.innerText = 'Save & Teach';
    saveBtn.className = 'save-btn';
    
    saveBtn.onclick = async () => {
        const newText = textarea.value;
        
        // Update UI
        contentDiv.innerHTML = formatText(newText);
        
        // Restore original UI state
        textarea.replaceWith(contentDiv);
        saveBtn.remove();
        btn.style.display = 'inline-block'; // Show edit button again
        
        // Send Feedback to API
        await sendFeedback(oldText, newText);
    };
    
    contentDiv.replaceWith(textarea);
    btn.style.display = 'none'; // Hide edit button while editing
    bubble.appendChild(saveBtn);
};

async function sendFeedback(aiDraft, humanFinal) {
    if (aiDraft === humanFinal) return; // No change
    
    try {
        const res = await fetch(`${API_URL}/agent/feedback`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ai_draft: aiDraft,
                human_final: humanFinal,
                context: "Correction from Command Center"
            })
        });
        
        const data = await res.json();
        console.log("Learning Status:", data);
        
        // Show toaster or small notification
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerText = '🎓 OpenClaw learned from your correction!';
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
        
    } catch (e) {
        console.error("Feedback Error", e);
    }
}
