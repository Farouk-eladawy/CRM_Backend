# Debug Session: whatsapp-send-failure [OPEN]

## الهدف
- اختبار الإرسال الفعلي إلى الرقم `201010323484`
- تحديد سبب الفشل بدليل runtime واضح
- الوصول إلى إصلاح minimal ومثبت

## الأعراض
- فشل إرسال رسالة واتساب من النظام إلى الرقم المذكور
- الواجهة قد تعرض `CORS` أو `Failed to fetch` رغم أن السبب قد يكون upstream/backend

## خطوات إعادة الإنتاج
1. تنفيذ إرسال واتساب إلى `201010323484`
2. جمع رد API الداخلي
3. مراجعة سجل السيرفر ورد Meta

## الفرضيات الأولية
- H1: Meta Cloud API ترجع خطأ transient أو OAuth مؤقت من الجهة الخارجية
- H2: الطلب يمر عبر Phone Number ID أو routing غير صحيح لهذا الشات
- H3: هناك فرق بين الإرسال النصي والإرسال عبر template في بناء الـ payload
- H4: البروكسي أو طبقة API العامة تعيد صياغة الخطأ بشكل يظهره للواجهة كـ CORS
- H5: توجد حالة بيانات في الشات نفسه تؤثر على اختيار قناة الإرسال أو معلماتها

## حالة الجلسة
- status: collecting-evidence
- business-logic-changes: none
- instrumentation-changes: added in `ai_agent.py` only

## الأدلة التي تم جمعها
- تم تحديد الشات المستهدف للرقم `201010323484`:
  - `chat_id`: `8c10100a-7ece-4a31-b72d-4354657868e4`
  - `location`: `Hurghada/Cairo`
  - `receiving_phone_id`: `1077199985483939`
- تم اختبار إرسال نص مباشر عبر `https://api.ftstravels.com/api/chats/send`
  - النتيجة: `502`
  - السجل يثبت أن الباك إند أرسل payload نصي صحيح إلى Meta ثم فشل 3 مرات متتالية
- تم اختبار نفس الإرسال مباشرة إلى Graph API خارج الباك إند
  - `v18.0`: فشل `500`
  - `v19.0`: فشل `500`
  - `v20.0`: فشل `500`
  - جسم الرد من Meta:
    - `{"error":{"message":"An unexpected error has occurred. Please retry your request later.","type":"OAuthException","is_transient":true,"code":2,...}}`
- تم اختبار رقم مقارنة آخر `201090005205`
  - عبر Graph API المباشر: فشل أيضًا بنفس `500 / OAuthException / code=2 / is_transient=true`
  - عبر `/api/chats/send`: رجع `400` بسبب غلق نافذة واتساب
  - جسم الرد:
    - `{"code":"WHATSAPP_WINDOW_CLOSED","message":"WhatsApp 24h window closed. Please send a Template to reopen the chat.",...}`
- تم اختبار الإرسال من خط `Sharm`
  - `phone_number_id = 1060037273868859`
  - القالب `hello_world` موجود وموافق عليه لخط Sharm
  - إرسال `text` مباشر إلى `201010323484`: نجح `200`
  - إرسال `hello_world` مباشر إلى `201010323484`: نجح `200`
  - إرسال `hello_world` عبر `/api/chats/send` مع `location=Sharm` و`receiving_phone_id=1060037273868859`: نجح `200`
- تم تحليل العميل `Booking Nr: BR-1408472147` / `393316016829`
  - توجد 3 محادثات لنفس الحجز: محادثة WhatsApp واحدة ومحادثتا Email
  - محادثة WhatsApp الفعلية:
    - `chat_id = 37127c7d-3443-4b6d-8f20-a2d2ea696572`
    - الإرسال عليها الآن نجح `200`
  - محادثات Email:
    - `63a20284-06a1-41be-b903-cca37609ddc2`
    - `1160b288-a6ea-4241-81d1-85c4c3aef5b6`
  - عند إجبار إحدى محادثات Email على `reply_channel=whatsapp` يرجع:
    - `400 NEEDS_COUNTRY_CODE`
    - لأن النظام يستخرج أرقامًا من `sender_identifier` البريدية/OTA بدل رقم العميل الحقيقي

## الإصلاح المطبق محليًا
- تم تعديل منطق استخراج رقم الواتساب في `ai_agent.py`
- إذا كان `sender_identifier` يشبه البريد (`@` أو `::`) فلن نستخدم الأرقام المستخرجة منه كرقم واتساب
- بدلًا من ذلك نرجع إلى رقم العميل الحقيقي من Airtable أو من محادثة واتساب مرتبطة

## حالة التحقق
- الكود المحلي يمر `py_compile` وبدون diagnostics
- الاختبار ضد `api.ftstravels.com` ما زال يظهر السلوك القديم لأنه يعمل على النسخة المنشورة قبل الـ deploy

## تقييم الفرضيات
- H1: confirmed
  - Meta Cloud API نفسها ترجع `OAuthException code=2` و`is_transient=true`
- H2: rejected
  - الطلب استخدم `phone_number_id=1077199985483939` المتوقع للشات المستهدف
- H3: rejected
  - الـ payload النصي كان صحيحًا جدًا وبسيطًا: `type=text`, `to=201010323484`, `body=...`
- H4: confirmed
  - الواجهة كانت ترى أثر الخطأ بشكل `CORS/Failed to fetch` بينما الفشل الحقيقي upstream من Meta ويعود كباك إند `502`
- H5: rejected
  - الشات والـ routing والرقم المستلم تم اختيارهم بشكل صحيح قبل الإرسال

## الاستنتاج الحالي
- المشكلة ليست عامة في Meta Cloud API ولا على كل خطوط الإرسال
- السبب ليس من React frontend
- السبب ليس من endpoint `/api/chats/send`
- السبب ليس من إصدار Graph API المستخدم في التطبيق
- يوجد أيضًا قيد مستقل داخل النظام/واتساب على الرقم `201090005205` وهو غلق نافذة `24h` للرسائل النصية العادية
- المشكلة تبدو محصورة في خط `Hurghada/Cairo` أو في نوع payload/template المستخدمة منه في بعض الحالات

## الإجراء المنفذ
- تمت إضافة retry وتحسين CORS سابقًا في `ai_agent.py`
- تمت إضافة instrumentation جديدة لهذه الجلسة محليًا

## الخطوة التالية المقترحة
- مراجعة حالة رقم الأعمال داخل Meta Business Manager / WhatsApp Manager
- اختبار إرسال من نفس `phone_number_id` إلى رقم آخر معروف
- إذا نجح رقم آخر وفشل هذا الرقم فقط: المشكلة recipient-specific
- إذا فشل الجميع: المشكلة account/phone-number-id/provider-side
