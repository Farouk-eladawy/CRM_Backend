[OPEN] Debug Session: internal-attachments-send

## Symptom
- Internal WhatsApp assistant receives requests like:
  - "هاتلي تذكرة الطيران اللي علي الحجز ده 546980816555"
  - "ابعتلي الملف المرفوع داخل حقل Attachments للحجز التالي 546980816555"
  - "ما هي قيمة حقل Attachments للحجز التالي 546980816555"
- Instead of returning or sending attachment info/files, the assistant falls back to booking summary.
- In one path, the system also emits `All AI providers failed ... openai 401`, which suggests an unintended fallback to AI.

## Expected
- Attachment/ticket requests should resolve the booking, inspect Airtable attachment fields, and either:
  - return attachment metadata/URLs, or
  - send the file/link through the internal channel as requested,
  without falling back to generic booking summary.

## Hypotheses
- H1: Intent classification does not recognize attachment/ticket requests, so they fall through to `booking_summary`.
- H2: The attachment field resolver is not mapped into the internal assistant execution path, even when booking is resolved.
- H3: The assistant tries an AI fallback for these requests; when provider auth fails, the response path collapses and defaults to summary behavior.
- H4: Attachment field values exist in Airtable, but the formatter/sender path cannot serialize Airtable attachment arrays correctly for internal WhatsApp delivery.
- H5: The same response sanitizer that produced malformed links with `\1` is also corrupting attachment/link output.

## Evidence Plan
- Instrument: internal intent classification, routing decision, booking summary fallback trigger, attachment request parser, Airtable attachment field extraction, and internal send path.
- Reproduce with the exact Arabic requests provided by the user against booking `546980816555`.

## Status
- Awaiting instrumentation and reproduction logs.

