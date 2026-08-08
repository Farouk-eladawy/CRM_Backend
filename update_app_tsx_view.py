import os

file_path = r"c:\Users\Aloosh2020\Downloads\New Project's\AIAgentProject\OpenClaw_Version\frontend_dashboard\new_frontend_dashboard\src\App.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add button
sidebar_btn = """              {(!currentUser?.allowedLocations?.includes('Religious') && (currentUser?.allowedLocations?.includes('Sales') || currentUser?.allowedLocations?.includes('All') || isAdmin)) && (
                <button
                  onClick={() => { setActiveTabWithLog('sales_performance'); if (window.innerWidth < 768) setIsSidebarOpen(false); }}
                  title={!isSidebarOpen ? 'Sales Performance' : undefined}
                  aria-label={!isSidebarOpen ? 'Sales Performance' : undefined}
                  className={`relative flex items-center gap-2.5 px-2.5 py-2 rounded-xl transition-all border ${
                    activeTab === 'sales_performance'
                      ? 'text-[#10B981] bg-[#ECFDF5] border-[#D1FAE5] shadow-sm font-bold'
                      : 'text-[#475569] border-transparent hover:bg-white hover:border-[#E2E8F0] hover:shadow-sm'
                  } ${!isSidebarOpen && 'justify-center w-10 h-10 px-0 py-0'}`}>
                  {activeTab === 'sales_performance' && <span className="absolute start-1 top-2 bottom-2 w-1 rounded-full bg-gradient-to-b from-[#10B981] to-[#34D399]" />}
                  <LineChart size={18} />
                  {isSidebarOpen && <span className="text-[13px] flex-1 text-start">Sales Performance</span>}
                </button>
              )}
"""

target_btn_marker = "              {(!currentUser?.allowedLocations?.includes('Religious') || currentUser?.allowedLocations?.includes('All')) && (\n                <button\n                  onClick={() => { setActiveTabWithLog('fts_family');"
if sidebar_btn not in content:
    content = content.replace(target_btn_marker, sidebar_btn + "\n" + target_btn_marker)

# Add View Render
view_render = """      ) : activeTab === 'sales_performance' ? (
        <PerformanceView currentUser={currentUser} users={availableUsers} />
"""
target_view_marker = "      ) : activeTab === 'customers' ? ("

if view_render not in content:
    content = content.replace(target_view_marker, view_render + target_view_marker)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
