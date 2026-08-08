const fs = require('fs');
const path = require('path');

const UI_DICT = {
  'Customers': 'العملاء',
  'AI Smart Sort': 'ترتيب ذكي بالذكاء الاصطناعي',
  'All Cities': 'جميع المدن',
  'Sharm El-Sheikh': 'شرم الشيخ',
  'Hurghada / Cairo': 'الغردقة / القاهرة',
  'All Channels': 'جميع القنوات',
  'WhatsApp': 'واتساب',
  'Email': 'البريد الإلكتروني',
  'OTA': 'وكالات السفر',
  'Loading bookings data...': 'جاري تحميل بيانات الحجوزات...',
  'VIP': 'شخصية هامة',
  'Time TBD': 'الوقت يحدد لاحقاً',
  'Soon': 'قريباً',
  'Location TBD': 'الموقع يحدد لاحقاً',
  'Pending Schedule': 'في انتظار الجدول',
  'Analyze': 'تحليل',
  'Generate WhatsApp': 'إنشاء رسالة واتساب',
  'Generate Email': 'إنشاء بريد إلكتروني',
  'Clear Filters': 'مسح الفلاتر',
  'Back to list': 'العودة للقائمة',
  'Active': 'نشط',
  'Complete Conversation History': 'سجل المحادثة بالكامل',
  'Loading conversation history...': 'جاري تحميل سجل المحادثة...',
  'Reply in Inbox': 'الرد في صندوق الوارد',
  'Customer Details': 'تفاصيل العميل',
  'First Contact': 'أول اتصال',
  'No media ID available to download': 'لا يوجد معرف وسائط للتحميل',
  'Click here to view / download': 'انقر هنا للعرض / التحميل',
  'View Attached Document': 'عرض المستند المرفق'
};

const keys = Object.keys(UI_DICT).sort((a,b) => b.length - a.length);

const targetFiles = [
  'frontend_dashboard/new_frontend_dashboard/src/views/CustomersView.tsx'
];

for (const relPath of targetFiles) {
  const p = path.join(__dirname, relPath);
  let content = fs.readFileSync(p, 'utf8');

  if (!content.includes('const _t = ')) {
    const helperCode = '\nconst UI_DICT: Record<string, string> = ' + JSON.stringify(UI_DICT, null, 2) + ';\n' +
      'const _t = (str: string, lang: string) => lang === "ar" ? (UI_DICT[str] || str) : str;\n\n';
    
    let lastImportIndex = 0;
    const lastFrom = content.lastIndexOf("from 'lucide-react';");
    if (lastFrom !== -1) {
      lastImportIndex = content.indexOf('\n', lastFrom) + 1;
    } else {
      lastImportIndex = content.lastIndexOf(';') + 1;
    }

    content = content.slice(0, lastImportIndex) + '\n' + helperCode + content.slice(lastImportIndex);
  }

  for (const k of keys) {
    const escapedK = k.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
    
    // Replace >Text< with >{_t('Text', currentLang)}<
    const regex1 = new RegExp('>' + escapedK + '<', 'g');
    content = content.replace(regex1, '>{_t("' + k + '", currentLang || "en")}<');
    
    // Replace > Text < with > {_t('Text', currentLang)} <
    const regex1b = new RegExp('>\\s+' + escapedK + '\\s+<', 'g');
    content = content.replace(regex1b, '> {_t("' + k + '", currentLang || "en")} <');

    // Replace >Text with >{_t('Text', currentLang)}
    const regex1c = new RegExp('>' + escapedK + '(?=\\s)', 'g');
    content = content.replace(regex1c, '>{_t("' + k + '", currentLang || "en")}');
    
    // Replace placeholder="Text" with placeholder={_t("Text", currentLang)}
    const regex2 = new RegExp('placeholder=["\']' + escapedK + '["\']', 'g');
    content = content.replace(regex2, 'placeholder={_t("' + k + '", currentLang || "en")}');
  }

  fs.writeFileSync(p, content);
}
console.log('Replaced texts in CustomersView successfully.');
