[OPEN] Debugging Session: server-auto-stop

## Symptom
- النظام يتوقف تلقائيًا بعد فترة (process exits / server stops listening).

## Environment
- OS: Windows
- Backend: ai_agent.py (Flask)
- Port: 5001

## Hypotheses (Falsifiable)
- H1: استثناء غير معالج في الـmain thread أو داخل `app.run()` يؤدي لإغلاق السيرفر.
- H2: Exception داخل Thread (مثل Automation/Email polling) يسبب crash غير متوقع أو `os._exit` في مسار خطأ.
- H3: سبب خارجي يقتل العملية (Windows service / antivirus / memory pressure) ويظهر كـExit بدون stacktrace داخل اللوج.
- H4: deadlock/timeout في Loop/Thread يوقف tick/processing ويبدو “كأنه توقف” بينما العملية ما زالت تعمل.
- H5: Auto-reloader/host config ينهي العملية (اقل احتمال لأن `use_reloader=False`).

## Evidence Plan
- تشغيل Debug Server لجمع أحداث runtime.
- إضافة instrumentation minimal: startup/heartbeat/atexit/sys.excepthook/threading.excepthook + around app.run.
- ترك النظام يعمل حتى يحدث التوقف ثم تحليل logs.

## Status
- Next: Start debug server + add instrumentation.

