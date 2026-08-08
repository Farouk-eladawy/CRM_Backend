import re

with open('frontend_dashboard/new_frontend_dashboard/src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add UserPlus to imports
if 'UserPlus' not in content:
    content = content.replace('Languages\n} from', 'Languages, UserPlus\n} from')

# 2. Add translations
if 'add_customer' not in content:
    content = content.replace("'settings': 'Settings',", "'settings': 'Settings',\n    'add_customer': 'Add Customer',\n    'search_customer_placeholder': 'Booking Nr, Email, Phone, or Exact Name...',\n    'search': 'Search',\n    'cancel': 'Cancel',")
    content = content.replace("'settings': 'الإعدادات',", "'settings': 'الإعدادات',\n    'add_customer': 'إضافة عميل',\n    'search_customer_placeholder': 'رقم الحجز، الايميل، الهاتف، أو الاسم بالكامل...',\n    'search': 'بحث',\n    'cancel': 'إلغاء',")

# 3. Add state variables
state_vars = """
  const [showAddCustomerModal, setShowAddCustomerModal] = useState(false);
  const [addCustomerSearchTerm, setAddCustomerSearchTerm] = useState('');
  const [addCustomerLoading, setAddCustomerLoading] = useState(false);
  const [addCustomerError, setAddCustomerError] = useState('');
"""
if 'showAddCustomerModal' not in content:
    content = content.replace("const [searchQuery, setSearchQuery] = useState('');", "const [searchQuery, setSearchQuery] = useState('');" + state_vars)

# 4. Add the handler function
handler = """
  const handleSearchAndAddCustomer = async () => {
    if (!addCustomerSearchTerm.trim()) return;
    setAddCustomerLoading(true);
    setAddCustomerError('');
    try {
      const response = await fetch(`${API_BASE}/customers/search_and_add`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ search_term: addCustomerSearchTerm.trim() })
      });
      const result = await response.json();
      if (result.status === 'success') {
        setShowAddCustomerModal(false);
        setAddCustomerSearchTerm('');
        await fetchChats();
        // Select the newly added chat if we can find it
        const newChatId = result.data.chat_id;
        const chatsRes = await fetch(`${API_BASE}/chats`);
        const chatsData = await chatsRes.json();
        if (chatsData.status === 'success') {
           const newChatRaw = chatsData.data.find((c: any) => c.chat_id === newChatId);
           if (newChatRaw) {
               const key = newChatRaw.airtable_record_id || newChatRaw.chat_id;
               const groupedIds = chatsData.data
                 .filter((c: any) => (c.airtable_record_id || c.chat_id) === key)
                 .map((c: any) => c.chat_id);
               
               const newChatWithGroup = {
                   ...newChatRaw,
                   grouped_chat_ids: groupedIds
               };
               selectChat(newChatWithGroup);
           }
        }
      } else {
        setAddCustomerError(result.message || 'Customer not found.');
      }
    } catch (err) {
      setAddCustomerError('Failed to connect to the server.');
    } finally {
      setAddCustomerLoading(false);
    }
  };
"""
if 'handleSearchAndAddCustomer' not in content:
    content = content.replace('const fetchChats = async () => {', handler + '\n  const fetchChats = async () => {')

# 5. Add the button in the UI
btn_html = """
              <button
                onClick={() => setShowAddCustomerModal(true)}
                className="w-8 h-8 flex items-center justify-center rounded-[6px] text-[#6B7280] hover:text-[#1E40AF] hover:bg-[#EFF6FF] transition-colors"
                title={t('add_customer')}
              >
                <UserPlus size={16} />
              </button>
"""
if 'UserPlus size={16}' not in content:
    content = content.replace('<RefreshCw size={16} />\n              </button>\n            </div>', '<RefreshCw size={16} />\n              </button>\n' + btn_html + '            </div>')

# 6. Add the modal
modal_html = """
      {/* Add Customer Modal */}
      {showAddCustomerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-[12px] shadow-xl w-full max-w-md overflow-hidden flex flex-col" dir={currentLang === 'ar' ? 'rtl' : 'ltr'}>
            <div className="flex justify-between items-center p-4 border-b border-[#E5E7EB]">
              <h3 className="font-bold text-[#111827] text-[16px]">{t('add_customer')}</h3>
              <button onClick={() => setShowAddCustomerModal(false)} className="text-[#6B7280] hover:text-[#111827]">
                <X size={20} />
              </button>
            </div>
            <div className="p-5 flex flex-col gap-4">
              <input
                type="text"
                value={addCustomerSearchTerm}
                onChange={(e) => setAddCustomerSearchTerm(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearchAndAddCustomer()}
                placeholder={t('search_customer_placeholder')}
                className="w-full border border-[#E5E7EB] rounded-[8px] px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6]"
                autoFocus
              />
              {addCustomerError && (
                <div className="text-[#DC2626] text-[13px] bg-[#FEF2F2] p-2.5 rounded-[6px] border border-[#FECACA]">
                  {addCustomerError}
                </div>
              )}
            </div>
            <div className="p-4 border-t border-[#E5E7EB] bg-[#F9FAFB] flex justify-end gap-3">
              <button
                onClick={() => setShowAddCustomerModal(false)}
                className="px-4 py-2 text-[14px] font-medium text-[#4B5563] bg-white border border-[#D1D5DB] rounded-[8px] hover:bg-[#F3F4F6] transition-colors"
                disabled={addCustomerLoading}
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleSearchAndAddCustomer}
                className="px-4 py-2 text-[14px] font-medium text-white bg-[#3B82F6] rounded-[8px] hover:bg-[#2563EB] transition-colors flex items-center gap-2 disabled:opacity-50"
                disabled={addCustomerLoading || !addCustomerSearchTerm.trim()}
              >
                {addCustomerLoading && <RefreshCw size={14} className="animate-spin" />}
                {t('search')}
              </button>
            </div>
          </div>
        </div>
      )}
"""
if 'Add Customer Modal' not in content:
    idx = content.rfind('</div>')
    content = content[:idx] + modal_html + content[idx:]

with open('frontend_dashboard/new_frontend_dashboard/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')
