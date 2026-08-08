# Debug Session: duplicate-pickup-send

- Status: OPEN
- Symptom: نفس الحجز يظهر عليه إرسال Email وWhatsApp أكثر من مرة داخل نفس المحادثة.
- Scope: `Unified Booking Communications` + تسجيل الرسائل داخل الشات + أي مسار تلقائي إضافي قد يعيد الإرسال.

## Hypotheses

1. الـ workflow الموحدة تُشغَّل أكثر من مرة على نفس السجل لأن تحديث Airtable للحالة لا يتم أو لا يمنع إعادة الالتقاط من نفس الـ View.
2. يوجد أكثر من trigger أو workflow أو scheduler يلتقط نفس الحجز، فينتج عنه إرسال مكرر حقيقي.
3. يوجد إرسال واحد فقط لكن تسجيل الرسائل داخل `chat_db` يحدث أكثر من مرة من أكثر من مسار.
4. بعد تأكيد العميل (`Confirm Pickup`) يوجد مسار آخر يرسل `Pickup Email Sent` أو يعيد تدوين نفس الإجراء داخل المحادثة.
5. منطق deduplication / idempotency غير موجود في الـ runner، لذلك أي إعادة تشغيل يدوية أو schedule تعيد الإرسال بالكامل.

## Plan

1. فحص مسارات التشغيل والإرسال والتسجيل المرتبطة بالـ workflow.
2. إضافة instrumentation فقط في نقاط التنفيذ الحساسة.
3. طلب إعادة إنتاج الحالة وقراءة الأدلة.
4. تحديد السبب المؤكد ثم تطبيق أقل تعديل ممكن.

## Progress

- تمت إضافة instrumentation في:
  - `unified_booking_communications.py`
  - `automation_engine.py`
  - `ai_agent.py` داخل `process_pickup_details`
- تم تطبيق تقليل التداخل تشغيليًا عبر:
  - تعطيل `Unified Booking Communications`
  - إنشاء workflows مستقلة لكل View
  - إيقاف جدولة `process_new_bookings()` افتراضيًا إلا إذا فُعلت من `config`
