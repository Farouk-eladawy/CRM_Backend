// ================================================
// معالج الحجوزات المحسّن - منع التكرار والتداخل
// ================================================

// ✅ CONFIG: إعدادات التطبيق والمفاتيح
const CONFIG = {
  KEYS: {
    AIRTABLE: 'patPlKVK4bsSNcUY1.6a0bc7165b9eac5ee3050a58ccbeaf1f91517593c9e62a246e70dbae29d679f9',
    DEEPSEK: 'sk-1785f7a14ac84291b785fe5eb374004b'
  },

  AIRTABLE: {
    BASE_ID: 'appTp5YgSp9DV2HYc',
    TABLE_NAME: 'List',
    get URL() {
      return `https://api.airtable.com/v0/${this.BASE_ID}/${this.TABLE_NAME}`;
    }
  },

  DEEPSEK: {
    MODEL: 'deepseek-coder',
    ENDPOINT: 'https://api.deepseek.com/v1/chat/completions',
    TEMPERATURE: 0,
    MAX_RETRIES: 3,
    RETRY_DELAY_MS: 2000
  },

  PROCESSING: {
    LABEL: "Booking Tiqets",
    MAX_THREADS_PER_RUN: 20,  // ✅ تقليل العدد لتجنب الضغط
    MAX_MESSAGES_PER_RUN: 50, // ✅ حد أقصى للرسائل في كل تشغيل
    SEARCH_TIME_WINDOW: "newer_than:30m", // ✅ نافذة زمنية للبحث
    ALERT_EMAIL: 'Ahmadyeladawy@gmail.com',
    USE_AI_FOR_ALL_FIELDS: true,
    DEFAULT_DESTINATION: "Cairo",
    TIMEZONE: "Africa/Cairo",
    LOCK_TIMEOUT_MS: 300000, // 5 دقائق timeout للقفل
    BATCH_SIZE: 10 // معالجة 10 رسائل في كل دفعة
  },
  
  BOOKING_STATUS: {
    ACTIVE: 'Active',
    CANCELED: 'Canceled',
    UPDATED: 'Changed'
  },

  // ✅ إعدادات منع التكرار
  DEDUPLICATION: {
    CACHE_KEY_PREFIX: 'PROCESSED_MSG_',
    CACHE_EXPIRY_SECONDS: 86400, // 24 ساعة
    LAST_RUN_KEY: 'LAST_PROCESSING_RUN',
    PROCESSED_IDS_KEY: 'PROCESSED_MESSAGE_IDS'
  }
};

// ================================================
// 🔒 نظام القفل ومنع التداخل
// ================================================

/**
 * ✅ الدالة الرئيسية مع نظام القفل
 * يتم استدعاؤها من الـ Trigger
 */
function sendEmailsToAirtable() {
  const lock = LockService.getScriptLock();
  
  try {
    // محاولة الحصول على القفل مع timeout
    const hasLock = lock.tryLock(CONFIG.PROCESSING.LOCK_TIMEOUT_MS);
    
    if (!hasLock) {
      Logger.log('⚠️ معالجة أخرى قيد التشغيل - تم التخطي');
      return;
    }
    
    Logger.log('🔒 تم الحصول على القفل - بدء المعالجة');
    
    // تنفيذ المعالجة الفعلية
    processBookingEmails();
    
  } catch (error) {
    Logger.log(`❌ خطأ في النظام: ${error.message}`);
    sendAlertEmail('خطأ في النظام', error.message);
  } finally {
    // تحرير القفل في جميع الأحوال
    lock.releaseLock();
    Logger.log('🔓 تم تحرير القفل');
  }
}

/**
 * ✅ المعالجة الرئيسية مع التحكم في الحِمل
 */
function processBookingEmails() {
  const startTime = new Date().getTime();
  const maxRunTime = 240000; // 4 دقائق كحد أقصى للتشغيل
  
  // الحصول على آخر وقت معالجة
  const lastRunTime = getLastRunTime();
  Logger.log(`📅 آخر تشغيل: ${lastRunTime ? new Date(lastRunTime).toISOString() : 'لا يوجد'}`);
  
  // البحث عن الرسائل الجديدة فقط
  const threads = searchNewThreads(lastRunTime);
  
  if (threads.length === 0) {
    Logger.log('✅ لا توجد رسائل جديدة للمعالجة');
    updateLastRunTime();
    return;
  }
  
  Logger.log(`📧 وجدت ${threads.length} محادثة للمعالجة`);
  
  const results = {
    processed: 0,
    skipped: 0,
    errors: 0,
    errorMessages: [],
    processedIds: []
  };
  
  // معالجة بالدفعات
  for (let i = 0; i < threads.length; i += CONFIG.PROCESSING.BATCH_SIZE) {
    // التحقق من timeout
    if (new Date().getTime() - startTime > maxRunTime) {
      Logger.log('⏱️ تم الوصول لحد الوقت - إيقاف المعالجة');
      break;
    }
    
    const batch = threads.slice(i, i + CONFIG.PROCESSING.BATCH_SIZE);
    processBatchOfThreads(batch, results);
    
    // التحقق من حد الرسائل
    if (results.processed >= CONFIG.PROCESSING.MAX_MESSAGES_PER_RUN) {
      Logger.log(`📊 تم الوصول للحد الأقصى (${CONFIG.PROCESSING.MAX_MESSAGES_PER_RUN} رسالة)`);
      break;
    }
  }
  
  // حفظ الرسائل المعالجة
  saveProcessedMessages(results.processedIds);
  
  // تحديث آخر وقت تشغيل
  updateLastRunTime();
  
  // إنشاء التقرير
  generateProcessingReport(results);
  
  Logger.log(`✅ انتهت المعالجة: ${results.processed} معالج، ${results.skipped} متخطى، ${results.errors} خطأ`);
}

/**
 * ✅ البحث عن المحادثات الجديدة فقط
 */
function searchNewThreads(lastRunTime) {
  const label = GmailApp.getUserLabelByName(CONFIG.PROCESSING.LABEL);
  if (!label) {
    throw new Error(`التصنيف "${CONFIG.PROCESSING.LABEL}" غير موجود`);
  }
  
  // بناء استعلام البحث
  let searchQuery = `label:${CONFIG.PROCESSING.LABEL}`;
  
  // إضافة فلترة زمنية
  if (lastRunTime) {
    const minutesAgo = Math.floor((Date.now() - lastRunTime) / 60000);
    if (minutesAgo < 1440) { // أقل من 24 ساعة
      searchQuery += ` newer_than:${minutesAgo}m`;
    }
  } else {
    searchQuery += ` ${CONFIG.PROCESSING.SEARCH_TIME_WINDOW}`;
  }
  
  // إضافة فلترة للرسائل غير المميزة
  searchQuery += ' -is:starred';
  
  Logger.log(`🔍 استعلام البحث: ${searchQuery}`);
  
  const threads = GmailApp.search(searchQuery, 0, CONFIG.PROCESSING.MAX_THREADS_PER_RUN);
  
  return threads;
}

/**
 * ✅ معالجة دفعة من المحادثات
 */
function processBatchOfThreads(threads, results) {
  const processedCache = getProcessedMessagesCache();
  
  for (const thread of threads) {
    try {
      const messages = thread.getMessages();
      
      for (const message of messages) {
        const messageId = message.getId();
        
        // التحقق من التكرار
        if (isMessageProcessed(messageId, processedCache)) {
          Logger.log(`⏭️ رسالة معالجة مسبقاً: ${messageId}`);
          results.skipped++;
          continue;
        }
        
        // التحقق من النجمة
        if (message.isStarred()) {
          Logger.log('⭐ تم تجاهل الرسالة المميزة');
          results.skipped++;
          continue;
        }
        
        // معالجة الرسالة
        const success = processMessageSafely(message);
        
        if (success) {
          results.processed++;
          results.processedIds.push(messageId);
          
          // وضع نجمة للإشارة للمعالجة
          message.star();
        } else {
          results.errors++;
        }
        
        // التحقق من حد الرسائل
        if (results.processed >= CONFIG.PROCESSING.MAX_MESSAGES_PER_RUN) {
          return;
        }
      }
    } catch (err) {
      results.errors++;
      results.errorMessages.push({
        subject: thread.getFirstMessageSubject(),
        error: err.message
      });
      Logger.log(`❌ خطأ في معالجة المحادثة: ${err.message}`);
    }
  }
}

/**
 * ✅ معالجة رسالة واحدة بأمان
 */
function processMessageSafely(message) {
  try {
    const body = message.getPlainBody() || message.getBody();
    
    // استخراج البيانات بالذكاء الاصطناعي
    let bookingData = extractBookingDataWithAI(body);
    
    if (!bookingData.reference_number) {
      Logger.log('⚠️ لا يوجد رقم حجز - تخطي الرسالة');
      return false;
    }
    
    // التحقق من عدم وجود الحجز في Airtable
    if (isBookingExists(bookingData.reference_number)) {
      Logger.log(`📋 الحجز ${bookingData.reference_number} موجود مسبقاً`);
      return true; // نعتبرها معالجة بنجاح
    }
    
    // تحسين وتنقيح البيانات
    bookingData = enhanceBookingDataWithFallback(bookingData, body);
    bookingData = enforceDefaultDestination(bookingData);
    bookingData = sanitizeAirtableData(bookingData);
    
    // إرسال إلى Airtable مع retry
    const sent = sendDataToAirtableWithRetry(bookingData);
    
    if (sent) {
      Logger.log(`✅ تمت معالجة الحجز: ${bookingData.reference_number}`);
      return true;
    } else {
      Logger.log(`⚠️ فشل إرسال الحجز: ${bookingData.reference_number}`);
      return false;
    }
    
  } catch (error) {
    Logger.log(`❌ خطأ في معالجة الرسالة: ${error.message}`);
    return false;
  }
}

// ================================================
// 🗄️ نظام إدارة التكرار والكاش
// ================================================

/**
 * ✅ التحقق من معالجة الرسالة مسبقاً
 */
function isMessageProcessed(messageId, cache) {
  // التحقق في الكاش المحلي أولاً
  if (cache && cache[messageId]) {
    return true;
  }
  
  // التحقق في CacheService
  const cacheKey = CONFIG.DEDUPLICATION.CACHE_KEY_PREFIX + messageId;
  const cached = CacheService.getScriptCache().get(cacheKey);
  
  return cached !== null;
}

/**
 * ✅ حفظ الرسائل المعالجة
 */
function saveProcessedMessages(messageIds) {
  if (messageIds.length === 0) return;
  
  const cache = CacheService.getScriptCache();
  const entries = {};
  
  for (const id of messageIds) {
    entries[CONFIG.DEDUPLICATION.CACHE_KEY_PREFIX + id] = '1';
  }
  
  // حفظ في الكاش (مع مدة صلاحية)
  cache.putAll(entries, CONFIG.DEDUPLICATION.CACHE_EXPIRY_SECONDS);
  
  // حفظ في PropertiesService للاحتفاظ طويل المدى
  saveToProperties(messageIds);
  
  Logger.log(`💾 تم حفظ ${messageIds.length} رسالة معالجة`);
}

/**
 * ✅ الحصول على كاش الرسائل المعالجة
 */
function getProcessedMessagesCache() {
  try {
    const props = PropertiesService.getScriptProperties();
    const stored = props.getProperty(CONFIG.DEDUPLICATION.PROCESSED_IDS_KEY);
    
    if (stored) {
      const ids = JSON.parse(stored);
      const cache = {};
      
      // تحويل لـ object للبحث السريع
      for (const id of ids) {
        cache[id] = true;
      }
      
      return cache;
    }
  } catch (error) {
    Logger.log(`⚠️ خطأ في قراءة الكاش: ${error.message}`);
  }
  
  return {};
}

/**
 * ✅ حفظ في PropertiesService
 */
function saveToProperties(newIds) {
  try {
    const props = PropertiesService.getScriptProperties();
    const stored = props.getProperty(CONFIG.DEDUPLICATION.PROCESSED_IDS_KEY);
    
    let allIds = stored ? JSON.parse(stored) : [];
    
    // إضافة الجديد
    allIds = allIds.concat(newIds);
    
    // الاحتفاظ بآخر 1000 معرّف فقط (لتجنب تضخم البيانات)
    if (allIds.length > 1000) {
      allIds = allIds.slice(-1000);
    }
    
    props.setProperty(CONFIG.DEDUPLICATION.PROCESSED_IDS_KEY, JSON.stringify(allIds));
    
  } catch (error) {
    Logger.log(`⚠️ خطأ في حفظ المعرفات: ${error.message}`);
  }
}

/**
 * ✅ حفظ آخر وقت تشغيل
 */
function updateLastRunTime() {
  const now = Date.now();
  PropertiesService.getScriptProperties().setProperty(
    CONFIG.DEDUPLICATION.LAST_RUN_KEY, 
    now.toString()
  );
  Logger.log(`⏰ تم تحديث آخر وقت تشغيل: ${new Date(now).toISOString()}`);
}

/**
 * ✅ الحصول على آخر وقت تشغيل
 */
function getLastRunTime() {
  const stored = PropertiesService.getScriptProperties().getProperty(
    CONFIG.DEDUPLICATION.LAST_RUN_KEY
  );
  return stored ? parseInt(stored) : null;
}

// ================================================
// 🤖 استخراج البيانات بالذكاء الاصطناعي
// ================================================

/**
 * ✅ استخراج بيانات الحجز بالذكاء الاصطناعي
 */
function extractBookingDataWithAI(emailBody) {
  Logger.log('🤖 بدء استخراج البيانات بالذكاء الاصطناعي...');
  
  const emailType = determineEmailType(emailBody);
  Logger.log(`📧 نوع الإيميل: ${emailType}`);
  
  const aiExtractedData = extractAllFieldsViaAI(emailBody, emailType);
  
  aiExtractedData.agency = emailType !== 'Unknown' ? emailType : 'Unknown';
  
  const enhancedData = applyBusinessLogicWithCairoDefault(aiExtractedData);
  
  Logger.log(`✅ تم استخراج ${Object.keys(enhancedData).length} حقل`);
  
  return enhancedData;
}

/**
 * ✅ تحديد نوع الإيميل
 */
function determineEmailType(emailBody) {
  const indicators = {
    'GetYourGuide': ['getyourguide.com', 'GetYourGuide Team', 'booking detail change'],
    'Viator': ['viator.com', 'Viator Booking Confirmation', 'Booking Reference'],
    'Tiqets': ['Tiqets.com', 'tiqets.com', 'Booking notification from Tiqets', 'order number:']
  };
  
  for (const [type, keywords] of Object.entries(indicators)) {
    if (keywords.some(keyword => emailBody.includes(keyword))) {
      return type;
    }
  }
  
  return 'Unknown';
}

/**
 * ✅ استخراج جميع الحقول بواسطة AI مع retry
 */
function extractAllFieldsViaAI(emailBody, emailType) {
  let retries = 0;
  let lastError = null;
  
  while (retries < CONFIG.DEEPSEK.MAX_RETRIES) {
    try {
      const prompt = createComprehensiveExtractionPrompt(emailBody, emailType);
      
      const options = {
        method: "post",
        contentType: "application/json",
        headers: { Authorization: `Bearer ${CONFIG.KEYS.DEEPSEK}` },
        payload: JSON.stringify({
          model: CONFIG.DEEPSEK.MODEL,
          messages: [{ role: "user", content: prompt }],
          temperature: CONFIG.DEEPSEK.TEMPERATURE
        }),
        muteHttpExceptions: true
      };
      
      const res = UrlFetchApp.fetch(CONFIG.DEEPSEK.ENDPOINT, options);
      const responseCode = res.getResponseCode();
      
      // معالجة Rate Limit
      if (responseCode === 429) {
        retries++;
        const delay = CONFIG.DEEPSEK.RETRY_DELAY_MS * Math.pow(2, retries - 1);
        Logger.log(`⏳ Rate limit - انتظار ${delay}ms قبل المحاولة ${retries}`);
        Utilities.sleep(delay);
        continue;
      }
      
      if (responseCode !== 200) {
        throw new Error(`API error: ${responseCode}`);
      }
      
      const json = JSON.parse(res.getContentText());
      const reply = json.choices?.[0]?.message?.content;
      
      if (!reply) {
        throw new Error('Empty AI response');
      }
      
      const jsonMatch = reply.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        throw new Error('No JSON in response');
      }
      
      const extractedData = JSON.parse(jsonMatch[0]);
      const sanitizedData = sanitizeAIResponse(extractedData);
      
      return sanitizedData;
      
    } catch (error) {
      lastError = error;
      retries++;
      
      if (retries < CONFIG.DEEPSEK.MAX_RETRIES) {
        const delay = CONFIG.DEEPSEK.RETRY_DELAY_MS * retries;
        Logger.log(`⚠️ خطأ في AI (محاولة ${retries}): ${error.message} - انتظار ${delay}ms`);
        Utilities.sleep(delay);
      }
    }
  }
  
  Logger.log(`❌ فشل AI بعد ${retries} محاولات: ${lastError?.message}`);
  return createFallbackData(emailBody, emailType);
}

/**
 * ✅ إنشاء prompt شامل للاستخراج
 */
function createComprehensiveExtractionPrompt(emailBody, emailType) {
  const fieldDescriptions = {
    "reference_number": "Booking reference, order number (e.g., GYG123456, BR-789, 655677222)",
    "real_product_name": "Full product/tour name exactly as written",
    "tour_name": "Simplified tour name",
    "tour_option": "Tour option, ticket type (e.g., 'Skip the Line')",
    "date_trip": "Visit date in ISO format (YYYY-MM-DDTHH:MM:SS.sssZ)",
    "main_Customer": "Customer full name",
    "email": "Customer email",
    "phone": "Customer phone with country code",
    "Adult": "Number of adults (integer)",
    "Student": "Number of students (integer)",
    "Child": "Number of children (integer)",
    "Infant": "Number of infants (integer)",
    "youth": "Number of youth (integer)",
    "Total price EUR": "Total in EUR (number only)",
    "Total price USD": "Total in USD (number only)",
    "Tour_language": "Tour language",
    "Pickup location": "Hotel pickup or meeting point",
    "Google Map": "Google Maps URL",
    "product_id": "Product ID",
    "destination": "ALWAYS 'Cairo'",
    "cancellation_status": "'Active', 'Canceled', or 'Changed'",
    "cancellation_date": "Cancellation date if canceled",
    "add_ons": "Additional services",
    "traveler_name": "Traveler names",
    "net_rate": "Net rate or commission"
  };
  
  return `
Extract booking information from this ${emailType} email.

FIELD DEFINITIONS:
${Object.entries(fieldDescriptions).map(([k, v]) => `${k}: ${v}`).join('\n')}

RULES:
1. Return ONLY valid JSON
2. Use exact field names
3. Dates in ISO format with Cairo timezone (UTC+2)
4. Numbers as integers/floats
5. Prices as numbers only
6. Omit missing fields
7. destination ALWAYS "Cairo"

EMAIL CONTENT:
"""
${emailBody.substring(0, 10000)}
"""

Return only JSON:`;
}

/**
 * ✅ تنقيح استجابة AI
 */
function sanitizeAIResponse(aiData) {
  const sanitized = {};
  const NUMERIC_FIELDS = ['Adult', 'Student', 'Child', 'Infant', 'youth'];
  
  for (const [key, value] of Object.entries(aiData)) {
    if (value === undefined || value === null || value === "") continue;
    
    if (Array.isArray(value) && value.length > 0) {
      sanitized[key] = value[0];
    } else if (NUMERIC_FIELDS.includes(key)) {
      sanitized[key] = parseInt(value, 10) || 0;
    } else if (key.includes('price') && typeof value === 'string') {
      const cleanPrice = value.replace(/[^\d.,]/g, '').replace(',', '.');
      sanitized[key] = parseFloat(cleanPrice) || null;
    } else if (typeof value === 'string') {
      sanitized[key] = value.trim();
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
}

/**
 * ✅ إنشاء بيانات احتياطية
 */
function createFallbackData(emailBody, emailType) {
  Logger.log('🔄 استخدام الاستخراج الاحتياطي...');
  
  const data = {
    agency: emailType,
    destination: CONFIG.PROCESSING.DEFAULT_DESTINATION,
    cancellation_status: "Active",
    Adult: 0,
    Student: 0,
    Child: 0,
    Infant: 0,
    youth: 0
  };
  
  // استخراج بسيط للبيانات الأساسية
  const patterns = {
    reference_number: [
      /order number:\s*(\d+)/i,
      /Reference.*?([A-Z0-9]{6,})/i,
      /(GYG[A-Z0-9]{6,})/i,
      /(BR-[A-Z0-9\-]+)/i
    ],
    email: [/Email.*?([^\s@]+@[^\s@]+\.[^\s@]+)/i],
    Adult: [/Adult.*?(\d+)/i]
  };
  
  for (const [field, regexList] of Object.entries(patterns)) {
    for (const regex of regexList) {
      const match = emailBody.match(regex);
      if (match) {
        data[field] = field === 'Adult' ? parseInt(match[1]) || 0 : match[1];
        break;
      }
    }
  }
  
  return data;
}

/**
 * ✅ تطبيق المنطق التجاري
 */
function applyBusinessLogicWithCairoDefault(data) {
  // توحيد معلومات المنتج
  standardizeTourInfo(data);
  
  // تنسيق التاريخ
  formatDateUniversal(data);
  
  // فرض Cairo كوجهة
  data.destination = CONFIG.PROCESSING.DEFAULT_DESTINATION;
  
  // تعيين الحالة الافتراضية
  if (!data.cancellation_status) {
    data.cancellation_status = 'Active';
  }
  
  return data;
}

// ================================================
// 📊 التكامل مع Airtable
// ================================================

/**
 * ✅ التحقق من وجود الحجز في Airtable
 */
function isBookingExists(referenceNumber) {
  try {
    const headers = {
      Authorization: `Bearer ${CONFIG.KEYS.AIRTABLE}`,
      'Content-Type': 'application/json'
    };
    
    const searchUrl = `${CONFIG.AIRTABLE.URL}?filterByFormula=${encodeURIComponent(
      `SEARCH("${referenceNumber}", {Booking Nr.})`
    )}`;
    
    const response = UrlFetchApp.fetch(searchUrl, {
      method: "get",
      headers,
      muteHttpExceptions: true
    });
    
    const data = JSON.parse(response.getContentText());
    return data.records && data.records.length > 0;
    
  } catch (error) {
    Logger.log(`⚠️ خطأ في التحقق من وجود الحجز: ${error.message}`);
    return false;
  }
}

/**
 * ✅ إرسال البيانات إلى Airtable مع retry
 */
function sendDataToAirtableWithRetry(bookingData) {
  const fields = mapFieldsToAirtable(bookingData);
  
  if (!fields || Object.keys(fields).length === 0) {
    Logger.log(`⚠️ لا توجد بيانات صالحة للإرسال: ${bookingData.reference_number}`);
    return false;
  }
  
  const payload = { fields: fields };
  let retries = 0;
  
  while (retries < CONFIG.DEEPSEK.MAX_RETRIES) {
    try {
      sendToAirtable(bookingData.reference_number, payload);
      return true;
    } catch (error) {
      retries++;
      
      if (retries < CONFIG.DEEPSEK.MAX_RETRIES) {
        const delay = 1000 * retries;
        Logger.log(`⚠️ خطأ في Airtable (محاولة ${retries}): ${error.message} - انتظار ${delay}ms`);
        Utilities.sleep(delay);
      } else {
        Logger.log(`❌ فشل نهائي في Airtable: ${error.message}`);
        return false;
      }
    }
  }
  
  return false;
}

/**
 * ✅ إرسال إلى Airtable
 */
function sendToAirtable(ref, payload) {
  const headers = {
    Authorization: `Bearer ${CONFIG.KEYS.AIRTABLE}`,
    'Content-Type': 'application/json'
  };
  
  const baseUrl = CONFIG.AIRTABLE.URL;
  
  // البحث عن السجل الموجود
  const searchUrl = `${baseUrl}?filterByFormula=${encodeURIComponent(
    `SEARCH("${ref}", {Booking Nr.})`
  )}`;
  
  const response = UrlFetchApp.fetch(searchUrl, {
    method: "get",
    headers,
    muteHttpExceptions: true
  });
  
  const data = JSON.parse(response.getContentText());
  
  if (data.records && data.records.length > 0) {
    // تحديث السجل الموجود
    updateExistingRecord(data.records[0], payload, headers, baseUrl);
  } else {
    // إنشاء سجل جديد
    createNewRecord(payload, headers, baseUrl);
  }
  
  Logger.log(`✅ تم حفظ الحجز: ${ref}`);
}

/**
 * ✅ تحديث سجل موجود
 */
function updateExistingRecord(record, payload, headers, baseUrl) {
  const recordId = record.id;
  Logger.log(`📝 تحديث سجل: ${recordId}`);
  
  // حماية الحقول الموجودة
  protectExistingFields(record, payload);
  
  const updateResponse = UrlFetchApp.fetch(`${baseUrl}/${recordId}`, {
    method: "patch",
    headers,
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  if (updateResponse.getResponseCode() >= 400) {
    throw new Error(`API error: ${updateResponse.getContentText()}`);
  }
}

/**
 * ✅ إنشاء سجل جديد
 */
function createNewRecord(payload, headers, baseUrl) {
  Logger.log('🆕 إنشاء سجل جديد');
  
  const createResponse = UrlFetchApp.fetch(baseUrl, {
    method: "post",
    headers,
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  if (createResponse.getResponseCode() >= 400) {
    throw new Error(`API error: ${createResponse.getContentText()}`);
  }
}

/**
 * ✅ حماية الحقول الموجودة
 */
function protectExistingFields(record, payload) {
  const PROTECTED_FIELDS = [
    "trip Name", "des", "Customer Email", "Product ID",
    "Customer Phone", "ADT", "STD", "CHD", "Inf", "Youth",
    "Real Product Name", "Customer Name"
  ];
  
  for (const field of PROTECTED_FIELDS) {
    if (record.fields[field] !== undefined && 
        record.fields[field] !== null && 
        record.fields[field] !== "") {
      delete payload.fields[field];
    }
  }
  
  if (record.fields["Booking Status"] === CONFIG.BOOKING_STATUS.CANCELED) {
    delete payload.fields["Booking Status"];
  }
}

// ================================================
// 🔧 دوال مساعدة
// ================================================

/**
 * ✅ تحسين البيانات
 */
function enhanceBookingDataWithFallback(bookingData, emailBody) {
  return bookingData;
}

/**
 * ✅ فرض الوجهة الأساسية
 */
function enforceDefaultDestination(bookingData) {
  bookingData.destination = CONFIG.PROCESSING.DEFAULT_DESTINATION;
  return bookingData;
}

/**
 * ✅ تنقيح البيانات لـ Airtable
 */
function sanitizeAirtableData(data) {
  const result = {...data};
  
  // تنقيح الأسعار
  const priceFields = ["Total price EUR", "Total price USD"];
  for (const field of priceFields) {
    if (result[field] !== undefined && result[field] !== null) {
      if (typeof result[field] === 'string') {
        const cleanPrice = result[field].replace(/[^\d.,]/g, '').replace(',', '.');
        result[field] = parseFloat(cleanPrice) || null;
      }
    }
  }
  
  // تنقيح التواريخ
  if (result.date_trip) {
    result.date_trip = formatDateForAirtable(result.date_trip);
  }
  
  // تأكيد الوجهة
  result.destination = CONFIG.PROCESSING.DEFAULT_DESTINATION;
  
  return result;
}

/**
 * ✅ تنسيق التاريخ لـ Airtable
 */
function formatDateForAirtable(dateStr) {
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(dateStr)) {
    return dateStr;
  }
  
  try {
    const date = new Date(dateStr);
    if (!isNaN(date.getTime())) {
      return date.toISOString();
    }
  } catch (e) {
    Logger.log(`⚠️ خطأ في تحويل التاريخ: ${e.message}`);
  }
  
  return dateStr;
}

/**
 * ✅ توحيد معلومات التور
 */
function standardizeTourInfo(data) {
  // تحميل قوائم المنتجات
  const productTitles = loadProductTitles();
  const productCodes = loadProductCodes();
  
  const found = productTitles.find(p =>
    data.real_product_name && 
    data.real_product_name.toLowerCase().includes(p.Title.toLowerCase())
  );
  
  if (found) {
    data.product_id = found["Product ID"];
  }
  
  if (data.product_id && productCodes[data.product_id]) {
    data.tour_name = productCodes[data.product_id];
  }
}

/**
 * ✅ تحويل البيانات لحقول Airtable
 */
function mapFieldsToAirtable(data) {
  const allFields = {
    "Agency": data.agency,
    "Product ID": data.product_id,
    "Booking Nr.": data.reference_number,
    "trip Name": data.tour_name,
    "Real Product Name": data.real_product_name,
    "Net Rate": data.net_rate,
    "Date Trip": data.date_trip,
    "Customer Name": data.main_Customer,
    "Option": data.tour_option,
    "des": data.destination,
    "Guide": data["Tour_language"],
    "ADT": data.Adult,
    "STD": data.Student,
    "CHD": data.Child,
    "Inf": data.Infant,
    "Youth": data.youth,
    "Add - Ons": data.add_ons,
    "Customer Email": data.email,
    "Customer Phone": data.phone,
    "Customer Country": data.customer_country,
    "Hotel Name": data["Pickup location"],
    "Booking Status": data.cancellation_status,
    "CXL Date": data.cancellation_date,
    "Google Maps": data["Google Map"],
    "Traveler name": data.traveler_name,
    "Total price EUR": data["Total price EUR"],
    "Total price USD ": data["Total price USD"]
  };
  
  const fields = {};
  for (const key in allFields) {
    if (allFields[key] !== undefined && 
        allFields[key] !== null && 
        allFields[key] !== "" &&
        !(typeof allFields[key] === "number" && allFields[key] === 0)) {
      fields[key] = allFields[key];
    }
  }
  
  return fields;
}

/**
 * ✅ تنسيق التاريخ الشامل
 */
function formatDateUniversal(data) {
  if (!data.date_trip) return;
  
  try {
    // محاولة تحويل التاريخ لصيغة ISO
    const date = new Date(data.date_trip);
    if (!isNaN(date.getTime())) {
      data.date_trip = date.toISOString();
    }
  } catch (error) {
    Logger.log(`⚠️ خطأ في تنسيق التاريخ: ${error.message}`);
  }
}

// ================================================
// 📧 التقارير والتنبيهات
// ================================================

/**
 * ✅ إنشاء تقرير المعالجة
 */
function generateProcessingReport(results) {
  if (results.errors === 0 && results.processed === 0) return;
  
  const report = `
📊 تقرير معالجة الحجوزات
========================
✅ معالج بنجاح: ${results.processed}
⏭️ متخطى: ${results.skipped}
❌ أخطاء: ${results.errors}

${results.errorMessages.length > 0 ? 
`تفاصيل الأخطاء:
${results.errorMessages.map(e => `- ${e.subject}: ${e.error}`).join('\n')}` : ''}
  `.trim();
  
  Logger.log(report);
  
  if (results.errors > 0) {
    sendAlertEmail(
      `تقرير معالجة - ${results.processed} نجاح، ${results.errors} فشل`,
      report
    );
  }
}

/**
 * ✅ إرسال إيميل تنبيه
 */
function sendAlertEmail(subject, body) {
  if (!CONFIG.PROCESSING.ALERT_EMAIL) return;
  
  try {
    GmailApp.sendEmail(
      CONFIG.PROCESSING.ALERT_EMAIL,
      `معالج الحجوزات: ${subject}`,
      body
    );
  } catch (err) {
    Logger.log(`⚠️ فشل إرسال التنبيه: ${err.message}`);
  }
}

// ================================================
// 🔧 دوال الأدوات والصيانة
// ================================================

/**
 * ✅ مسح الكاش (للصيانة)
 */
function clearProcessingCache() {
  try {
    // مسح من CacheService
    const cache = CacheService.getScriptCache();
    cache.removeAll([]);
    
    // مسح من PropertiesService
    const props = PropertiesService.getScriptProperties();
    props.deleteProperty(CONFIG.DEDUPLICATION.PROCESSED_IDS_KEY);
    props.deleteProperty(CONFIG.DEDUPLICATION.LAST_RUN_KEY);
    
    Logger.log('✅ تم مسح الكاش بنجاح');
  } catch (error) {
    Logger.log(`❌ خطأ في مسح الكاش: ${error.message}`);
  }
}

/**
 * ✅ إحصائيات النظام
 */
function getSystemStats() {
  try {
    const props = PropertiesService.getScriptProperties();
    const lastRun = props.getProperty(CONFIG.DEDUPLICATION.LAST_RUN_KEY);
    const processedIds = props.getProperty(CONFIG.DEDUPLICATION.PROCESSED_IDS_KEY);
    
    const stats = {
      lastRun: lastRun ? new Date(parseInt(lastRun)).toISOString() : 'لا يوجد',
      processedCount: processedIds ? JSON.parse(processedIds).length : 0,
      cacheSize: JSON.stringify(processedIds || '').length,
      maxThreadsPerRun: CONFIG.PROCESSING.MAX_THREADS_PER_RUN,
      maxMessagesPerRun: CONFIG.PROCESSING.MAX_MESSAGES_PER_RUN
    };
    
    Logger.log('📊 إحصائيات النظام:');
    for (const [key, value] of Object.entries(stats)) {
      Logger.log(`  ${key}: ${value}`);
    }
    
    return stats;
  } catch (error) {
    Logger.log(`❌ خطأ في الإحصائيات: ${error.message}`);
  }
}

// ================================================
// 📦 بيانات المنتجات
// ================================================

function loadProductTitles() {
  return [
    { "Product ID": "407583", "Title": "Sharm El-Sheikh: Ras Mohamed & White Island Snorkeling Trip" },
    { "Product ID": "96546", "Title": "Hurghada: Desert Quad Bike Tout with Optional GoPro" },
    { "Product ID": "872063", "Title": "Moses Mountain & Saint Catherine from Dahab" },
    { "Product ID": "985803", "Title": "Sharm El-Sheikh: Stargazing with Luxury Dinner" },
    { "Product ID": "596660", "Title": "Sharm El-Sheikh: Jeep Adventure to Blue Hole, Canyon & Dahab" },
    { "Product ID": "437576", "Title": "Sharm El-Sheikh: Ultimate ATV Quad, Stargazing & BBQ Dinner" },
    { "Product ID": "22357", "Title": "Hurghada: Luxor Valley of the Kings & Tutankhamun Tomb Trip" },
    { "Product ID": "596633", "Title": "Sharm ElSheikh: ATV Quad & Buggy Adventure Sunrise or Sunset" },
    { "Product ID": "529200", "Title": "Hurghada: Eden Island Xtreme, Parasail, Dive & Water Sports" },
    { "Product ID": "446295", "Title": "Grand Egyptian Museum QR Ticket" },
    { "Product ID": "432704", "Title": "Hurghada: Star Watching Desert Adventure by Jeep with Dinner" },
    { "Product ID": "160502", "Title": "Egyptian Museum of Antiquities online QR Ticket" },
    { "Product ID": "484786", "Title": "Hurghada: Orange Bay Day Trip with Water Sports and Lunch" },
    { "Product ID": "686037", "Title": "Hurghada: Orange Bay island With Parachute Adventure & Lunch" },
    { "Product ID": "677972", "Title": "Sharm El-Sheikh: Albatros Aqua Park with Lunch & Transfers" }
  ];
}

function loadProductCodes() {
  return {
    "773864": "Abu Simbel Temple QR Tickets",
    "449263": "4-Day Nile Cruise Aswan to Luxor with Balloon Flight",
    "447572": "2-Day Private Tour of Luxor and Abu Simbel",
    "690891": "Citadel of Salahdin & Mohamed Ali Mosque QR Ticket",
    "278712": "Customized Full-Day Private Tour",
    "985803": "Sharm El-Sheikh: Stargazing with Luxury Dinner",
    "529200": "Eden Island Xtreme, Parasail, Dive & Water Sports"
  };
}

// ================================================
// 🧪 دوال الاختبار
// ================================================

/**
 * ✅ اختبار معالجة إيميل واحد
 */
function testSingleEmail() {
  const threads = GmailApp.search(`label:${CONFIG.PROCESSING.LABEL} -is:starred`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لا توجد رسائل غير معالجة للاختبار');
    return;
  }
  
  const message = threads[0].getMessages()[0];
  const body = message.getPlainBody() || message.getBody();
  
  Logger.log('🧪 اختبار معالجة رسالة واحدة:');
  Logger.log(`📧 الموضوع: ${message.getSubject()}`);
  
  const bookingData = extractBookingDataWithAI(body);
  
  Logger.log('\n📊 البيانات المستخرجة:');
  for (const [key, value] of Object.entries(bookingData)) {
    if (value !== "" && value !== 0 && value !== null) {
      Logger.log(`  ${key}: ${JSON.stringify(value)}`);
    }
  }
  
  return bookingData;
}

/**
 * ✅ اختبار نظام القفل
 */
function testLockSystem() {
  const lock = LockService.getScriptLock();
  
  Logger.log('🔒 اختبار نظام القفل...');
  
  // محاولة الحصول على القفل
  const hasLock1 = lock.tryLock(1000);
  Logger.log(`محاولة 1: ${hasLock1 ? 'نجح' : 'فشل'}`);
  
  if (hasLock1) {
    // محاولة أخرى بدون تحرير القفل
    const lock2 = LockService.getScriptLock();
    const hasLock2 = lock2.tryLock(1000);
    Logger.log(`محاولة 2 (مع قفل نشط): ${hasLock2 ? 'نجح' : 'فشل'}`);
    
    // تحرير القفل
    lock.releaseLock();
    Logger.log('تم تحرير القفل');
    
    // محاولة بعد التحرير
    const lock3 = LockService.getScriptLock();
    const hasLock3 = lock3.tryLock(1000);
    Logger.log(`محاولة 3 (بعد التحرير): ${hasLock3 ? 'نجح' : 'فشل'}`);
    
    if (hasLock3) {
      lock3.releaseLock();
    }
  }
}

// ================================================
// ✅ نهاية معالج الحجوزات المحسّن
// ================================================