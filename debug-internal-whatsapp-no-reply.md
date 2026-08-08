# [OPEN] internal-whatsapp-no-reply

## Symptom
- Internal assistant on `fts_internal_notifications` does not reply to inbound WhatsApp messages from `201010323484` after server restart.

## Expected
- The internal webhook receives the inbound WhatsApp event, recognizes the admin phone, builds a reply, and sends the reply back through Evolution.

## Hypotheses
1. Evolution is connected, but inbound message events are not being posted to `/api/internal_notifications/whatsapp/webhook`.
2. The webhook receives events, but the payload shape differs from the parser, so `sender_phone` or `incoming_text` is not extracted.
3. The webhook receives and parses the message, but the sender phone does not match the configured admin phone after normalization.
4. The assistant builds a reply, but the outbound `sendText` request to Evolution fails at runtime.
5. The webhook route is not being hit on the running server instance because the active internal WhatsApp config points to a different webhook URL or stale instance settings.

## Evidence Log
- `internal_whatsapp_notifications_config` موجود ويشير إلى:
  - `instanceName = fts_internal_notifications`
  - `webhookUrl = http://127.0.0.1:5001/api/internal_notifications/whatsapp/webhook`
  - `connectionStatus = connected`
- من الكود في `ai_agent.py` كان إعداد الـ webhook يشترك فقط في:
  - `QRCODE_UPDATED`
  - `CONNECTION_UPDATE`
  وهذا يفسر عدم وصول أحداث الرسائل الواردة للـ webhook الداخلي.
- تم تعديل الكود ليوسّع الاشتراك إلى:
  - `MESSAGES_UPSERT`
  - `MESSAGES_UPDATE`
  - `SEND_MESSAGE`
  إضافة إلى الأحداث القديمة.
- تم تفعيل إعادة فرض webhook عند `status refresh`.
- اختبار الإرسال المباشر إلى الرقم `201010323484` عبر:
  - `POST /message/sendText/fts_internal_notifications`
  عاد بحالة `500`.
- سجلات Evolution (`embedded_evolution.log`) أظهرت:
  - `stream errored out` مع `code 515`
  - وأحياناً `conflict type=device_removed`
  - وأيضاً `error in handling message` لرسائل واردة على نفس instance
  ما يشير إلى أن instance نفسها غير مستقرة أو جلسة الربط بها مشكلة.
- بعد إعادة إنشاء الجلسة، الإرسال المباشر من Evolution إلى الرقم `201010323484` نجح بحالة `201`.
- فحص `agent_log.txt` أظهر أن أحداث `POST /api/internal_notifications/whatsapp/webhook` كانت تصل صباح `2026-07-09` لكنها ترجع `500`.
- سبب الـ `500` لم يكن من business logic الخاص بالرد الداخلي، بل من نقاط الـ instrumentation نفسها:
  - الاستثناء كان `urlopen error [WinError 10061] No connection could be made because the target machine actively refused it`
  - الوجهة الفاشلة كانت `http://127.0.0.1:7777/event`
  - هذا يعني أن Debug Server لم يكن شغالاً بينما الكود كان يعامل إرسال debug logs كاستدعاء إلزامي.
- تم تعديل نقاط الـ debug داخل `api_internal_notifications_whatsapp_webhook` لتصبح non-blocking:
  - إذا كان Debug Server غير متاح، يتم تجاهل فشل الإرسال ولا يتعطل webhook.
  - تمت إضافة `timeout=1` مع `try/except` حول كل نقطة من `A/B/C`.
- تحقق ما بعد التعديل:
  - `py_compile ai_agent.py` نجح.
  - لا توجد diagnostics على الملف.

## Status
- Webhook subscription bug in app code: confirmed and fixed.
- Evolution session health was previously a blocker, ثم تحسن الإرسال بعد إعادة إنشاء الجلسة.
- Current confirmed blocker that caused the latest failure: debug instrumentation crashed the webhook when Debug Server was offline.
- Next verification needed: user sends `مرحبا` again to confirm the webhook now completes and the assistant replies automatically.
