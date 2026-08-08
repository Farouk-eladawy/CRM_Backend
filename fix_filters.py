import re
with open('frontend_dashboard/new_frontend_dashboard/src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace('className={`basis-[calc(50%-0.125rem)] md:basis-0 md:flex-1 min-w-0 whitespace-nowrap', 'className={`flex-none min-w-[85px] whitespace-nowrap')
content = content.replace('<div className="flex flex-wrap md:flex-nowrap gap-1 bg-white/75 p-1 rounded-xl mt-2.5 border border-white/70 shadow-[0_12px_34px_rgba(15,23,42,0.06)] backdrop-blur">', '<div className="flex flex-nowrap overflow-x-auto scrollbar-none gap-1 bg-white/75 p-1 rounded-xl mt-2.5 border border-white/70 shadow-[0_12px_34px_rgba(15,23,42,0.06)] backdrop-blur">')

with open('frontend_dashboard/new_frontend_dashboard/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")