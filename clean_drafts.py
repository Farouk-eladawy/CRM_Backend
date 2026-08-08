import sqlite3
conn=sqlite3.connect('chat_history.db')
c=conn.cursor()
c.execute('''
DELETE FROM messages 
WHERE text LIKE '[PROPOSED_DRAFT]%' 
AND chat_id IN (
    SELECT DISTINCT chat_id 
    FROM messages 
    WHERE sender_type IN ('agent','ai') 
    AND text NOT LIKE '[PROPOSED_DRAFT]%' 
    AND text NOT LIKE '[System Log]%'
)
''')
conn.commit()
print('Deleted old drafts:', c.rowcount)
