const fs = require('fs');
const path = require('path');

const UI_DICT = {
  'AI Operation': 'عمليات الذكاء الاصطناعي',
  'Refresh': 'تحديث',
  'Add View': 'إضافة عرض',
  'Records': 'سجلات',
  'Fields': 'الحقول',
  'Filter': 'تصفية',
  'In this view, show records': 'في هذا العرض، إظهار السجلات',
  'No filters applied to this view': 'لا توجد فلاتر مطبقة على هذا العرض',
  'Where': 'حيث',
  'and': 'و',
  'or': 'أو',
  'Any of the following are true...': 'أي من التالي صحيح...',
  'All of the following are true...': 'كل ما يلي صحيح...',
  'Select an option...': 'اختر خياراً...',
  'Confirmed': 'مؤكد',
  'Pending': 'قيد الانتظار',
  'Cancelled': 'ملغي',
  'No Show': 'لم يحضر',
  'Sharm El-Sheikh': 'شرم الشيخ',
  'Hurghada': 'الغردقة',
  'Cairo': 'القاهرة',
  'Yes': 'نعم',
  'Add condition': 'إضافة شرط',
  'Add condition group': 'إضافة مجموعة شروط',
  'Copy from another view': 'نسخ من عرض آخر',
  'Cancel': 'إلغاء',
  'Apply': 'تطبيق',
  'Sort by': 'ترتيب حسب',
  'Sort records by multiple fields sequentially.': 'ترتيب السجلات حسب عدة حقول بتسلسل.',
  'No sorts applied to this view': 'لا يوجد ترتيب مطبق على هذا العرض',
  'then by': 'ثم حسب',
  'Add another sort': 'إضافة ترتيب آخر',
  'Automatically sort records': 'ترتيب السجلات تلقائياً',
  'Show/Hide Fields': 'إظهار/إخفاء الحقول',
  'Show all': 'إظهار الكل',
  'Default': 'الافتراضي',
  'Loading view...': 'جاري تحميل العرض...',
  'Loading operations data...': 'جاري تحميل بيانات العمليات...',
  'No bookings found for this view.': 'لا توجد حجوزات في هذا العرض.',
  'Changes': 'التغييرات',
  'No changes yet': 'لا توجد تغييرات بعد',
  'Time TBD': 'الوقت يحدد لاحقاً',
  'Change log': 'سجل التغييرات',
  'Loading...': 'جاري التحميل...',
  'No edits recorded yet.': 'لم تسجل أي تعديلات بعد.',
  'From:': 'من:',
  'Loading more...': 'تحميل المزيد...',
  'Empty': 'فارغ',
  '(Empty)': '(فارغ)',
  'No options': 'لا توجد خيارات',
  'Additional Details & Logs': 'تفاصيل إضافية وسجلات',
  'No file URL': 'لا يوجد رابط للملف',
  'Open file': 'فتح الملف',
  'Create New View': 'إنشاء عرض جديد',
  'View Name': 'اسم العرض',
  'Filter Settings': 'إعدادات الفلتر',
  'Duplicate current filters': 'تكرار الفلاتر الحالية',
  'Start with empty filters': 'البدء بفلاتر فارغة',
  'Create View': 'إنشاء عرض',
  'file(s)': 'ملفات',
  'Search by Booking Nr. or Name...': 'البحث برقم الحجز أو الاسم...'
};

const keys = Object.keys(UI_DICT).sort((a,b) => b.length - a.length);

const targetFiles = [
  'frontend_dashboard/new_frontend_dashboard/src/views/ReligiousOperationView.tsx',
  'frontend_dashboard/new_frontend_dashboard/src/views/AIOperationView.tsx'
];

for (const relPath of targetFiles) {
  const p = path.join(__dirname, relPath);
  let content = fs.readFileSync(p, 'utf8');

  if (!content.includes('const _t = ')) {
    const importRegex = /import\s+.*?from\s+['"].*?['"];\n/g;
    let lastImportIndex = 0;
    let match;
    while ((match = importRegex.exec(content)) !== null) {
      lastImportIndex = match.index + match[0].length;
    }
    
    const helperCode = '\nconst UI_DICT: Record<string, string> = ' + JSON.stringify(UI_DICT, null, 2) + ';\n' +
      'const _t = (str: string, lang: string) => lang === "ar" ? (UI_DICT[str] || str) : str;\n\n';
    
    content = content.slice(0, lastImportIndex) + helperCode + content.slice(lastImportIndex);
  }

  for (const k of keys) {
    const escapedK = k.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, "\\$&");
    
    // Replace >Text< with >{_t('Text', currentLang)}<
    const regex1 = new RegExp('>' + escapedK + '<', 'g');
    content = content.replace(regex1, '>{_t("' + k + '", currentLang)}<');
    
    // Replace > Text < with > {_t('Text', currentLang)} <
    const regex1b = new RegExp('>\\s+' + escapedK + '\\s+<', 'g');
    content = content.replace(regex1b, '> {_t("' + k + '", currentLang)} <');

    // Replace >Text with >{_t('Text', currentLang)}  (for strings at the end of a tag followed by whitespace)
    const regex1c = new RegExp('>' + escapedK + '(?=\\s)', 'g');
    content = content.replace(regex1c, '>{_t("' + k + '", currentLang)}');
    
    // Replace placeholder="Text" with placeholder={_t("Text", currentLang)}
    const regex2 = new RegExp('placeholder=["\']' + escapedK + '["\']', 'g');
    content = content.replace(regex2, 'placeholder={_t("' + k + '", currentLang)}');
  }

  fs.writeFileSync(p, content);
}
console.log('Replaced texts successfully.');
