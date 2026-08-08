import re
text = '[PROPOSED_DRAFT] العفو يا فندم، دائمًا تحت أمرك.  \nهل حضرتك محتاج مساعدة في أي استفسار عن برامج الحج المتاحة؟ نقدر نوضح لك التفاصيل لو تحب.\n\nمع خالص التحية،  \nفرح'
print('Original:', repr(text))
print('Cleaned:', repr(re.sub(r'مع\s*خالص\s*التحية[،,]*\s*فرح\s*$', '', text)))
