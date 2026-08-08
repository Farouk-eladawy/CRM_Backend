// ================================================
// معالج الحجوزات المحسّن - Headout مع استخراج من الرابط
// الإصدار: 2.0 - مصحح ومحسّن
// ================================================

// ✅ CONFIG: إعدادات التطبيق والمفاتيح
const CONFIG = {
  KEYS: {
    AIRTABLE: 'patNTCvlFWAr3DQbq.e2d2d93b35a9f39df01a08d48f09f4c45410af204fda4b691e8b6343167ceaab',
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
    LABEL: "Booking Headout",
    MAX_THREADS_PER_RUN: 20,
    MAX_MESSAGES_PER_RUN: 50,
    SEARCH_TIME_WINDOW: "newer_than:30m",
    ALERT_EMAIL: 'Ahmadyeladawy@gmail.com',
    USE_AI_FOR_ALL_FIELDS: true,
    DEFAULT_DESTINATION: "Cairo",
    TIMEZONE: "Africa/Cairo",
    LOCK_TIMEOUT_MS: 300000,
    BATCH_SIZE: 10
  },
  
  BOOKING_STATUS: {
    ACTIVE: 'Active',
    CANCELED: 'Canceled',
    UPDATED: 'Changed'
  },

  DEDUPLICATION: {
    CACHE_KEY_PREFIX: 'PROCESSED_MSG_',
    CACHE_EXPIRY_SECONDS: 86400,
    LAST_RUN_KEY: 'LAST_PROCESSING_RUN',
    PROCESSED_IDS_KEY: 'PROCESSED_MESSAGE_IDS'
  },

  HEADOUT: {
    USER_AGENT: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    FETCH_TIMEOUT_MS: 10000,
    MAX_FETCH_RETRIES: 3
  }
};

// ================================================
// 🔒 نظام القفل ومنع التداخل
// ================================================

/**
 * ✅ الدالة الرئيسية مع نظام القفل
 */
function sendEmailsToAirtable() {
  const lock = LockService.getScriptLock();
  
  try {
    const hasLock = lock.tryLock(CONFIG.PROCESSING.LOCK_TIMEOUT_MS);
    
    if (!hasLock) {
      Logger.log('⚠️ معالجة أخرى قيد التشغيل - تم التخطي');
      return;
    }
    
    Logger.log('🔒 تم الحصول على القفل - بدء المعالجة');
    processBookingEmails();
    
  } catch (error) {
    Logger.log(`❌ خطأ في النظام: ${error.message}`);
    sendAlertEmail('خطأ في النظام', error.message);
  } finally {
    lock.releaseLock();
    Logger.log('🔓 تم تحرير القفل');
  }
}

/**
 * ✅ المعالجة الرئيسية مع التحكم في الحِمل
 */
function processBookingEmails() {
  const startTime = new Date().getTime();
  const maxRunTime = 240000;
  
  const lastRunTime = getLastRunTime();
  Logger.log(`📅 آخر تشغيل: ${lastRunTime ? new Date(lastRunTime).toISOString() : 'لا يوجد'}`);
  
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
  
  for (let i = 0; i < threads.length; i += CONFIG.PROCESSING.BATCH_SIZE) {
    if (new Date().getTime() - startTime > maxRunTime) {
      Logger.log('⏱️ تم الوصول لحد الوقت - إيقاف المعالجة');
      break;
    }
    
    const batch = threads.slice(i, i + CONFIG.PROCESSING.BATCH_SIZE);
    processBatchOfThreads(batch, results);
    
    if (results.processed >= CONFIG.PROCESSING.MAX_MESSAGES_PER_RUN) {
      Logger.log(`📊 تم الوصول للحد الأقصى (${CONFIG.PROCESSING.MAX_MESSAGES_PER_RUN} رسالة)`);
      break;
    }
  }
  
  saveProcessedMessages(results.processedIds);
  updateLastRunTime();
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
  
  let searchQuery = `label:${CONFIG.PROCESSING.LABEL}`;
  
  if (lastRunTime) {
    const minutesAgo = Math.floor((Date.now() - lastRunTime) / 60000);
    if (minutesAgo < 1440) {
      searchQuery += ` newer_than:${minutesAgo}m`;
    }
  } else {
    searchQuery += ` ${CONFIG.PROCESSING.SEARCH_TIME_WINDOW}`;
  }
  
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
        
        if (isMessageProcessed(messageId, processedCache)) {
          Logger.log(`⏭️ رسالة معالجة مسبقاً: ${messageId}`);
          results.skipped++;
          continue;
        }
        
        if (message.isStarred()) {
          Logger.log('⭐ تم تجاهل الرسالة المميزة');
          results.skipped++;
          continue;
        }
        
        const success = processMessageSafely(message);
        
        if (success) {
          results.processed++;
          results.processedIds.push(messageId);
          message.star();
        } else {
          results.errors++;
        }
        
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

// ================================================
// 🗄️ نظام إدارة التكرار والكاش
// ================================================

/**
 * ✅ التحقق من معالجة الرسالة مسبقاً
 */
function isMessageProcessed(messageId, cache) {
  if (cache && cache[messageId]) {
    return true;
  }
  
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
  
  cache.putAll(entries, CONFIG.DEDUPLICATION.CACHE_EXPIRY_SECONDS);
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
    allIds = allIds.concat(newIds);
    
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
// 🌐 استخراج البيانات من رابط Headout
// ================================================

/**
 * ✅ استخراج رابط Voucher من الإيميل
 */
function extractVoucherLink(emailBody) {
  const patterns = [
    /voucher[^]*?HERE[^]*?\((https:\/\/www\.headout\.com\/voucher\/[^)]+)\)/i,
    /voucher[^]*?HERE[^]*?<(https:\/\/www\.headout\.com\/voucher\/[^>]+)>/i,
    /https:\/\/www\.headout\.com\/voucher\/\d+\?[^\s\)>\]]+/gi
  ];
  
  for (const pattern of patterns) {
    const match = emailBody.match(pattern);
    if (match) {
      const url = match[1] || match[0];
      return url.replace(/[)\]>]$/, '').trim();
    }
  }
  
  return null;
}

/**
 * ✅ جلب محتوى صفحة Headout
 */
function fetchHeadoutVoucherPage(voucherUrl) {
  Logger.log(`🌐 جلب صفحة Voucher: ${voucherUrl}`);
  
  let retries = 0;
  let lastError = null;
  
  while (retries < CONFIG.HEADOUT.MAX_FETCH_RETRIES) {
    try {
      const options = {
        method: 'GET',
        headers: {
          'User-Agent': CONFIG.HEADOUT.USER_AGENT,
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.5',
          'Accept-Encoding': 'gzip, deflate, br',
          'DNT': '1',
          'Connection': 'keep-alive',
          'Upgrade-Insecure-Requests': '1'
        },
        muteHttpExceptions: true,
        followRedirects: true,
        validateHttpsCertificates: false
      };
      
      const response = UrlFetchApp.fetch(voucherUrl, options);
      const responseCode = response.getResponseCode();
      
      if (responseCode === 200) {
        const html = response.getContentText();
        Logger.log(`✅ تم جلب الصفحة بنجاح (${html.length} حرف)`);
        return html;
      } else if (responseCode === 429) {
        retries++;
        const delay = CONFIG.DEEPSEK.RETRY_DELAY_MS * Math.pow(2, retries);
        Logger.log(`⏳ Rate limit - انتظار ${delay}ms قبل المحاولة ${retries}`);
        Utilities.sleep(delay);
      } else {
        throw new Error(`HTTP ${responseCode}: ${response.getContentText().substring(0, 200)}`);
      }
      
    } catch (error) {
      lastError = error;
      retries++;
      
      if (retries < CONFIG.HEADOUT.MAX_FETCH_RETRIES) {
        const delay = CONFIG.DEEPSEK.RETRY_DELAY_MS * retries;
        Logger.log(`⚠️ خطأ في جلب الصفحة (محاولة ${retries}): ${error.message}`);
        Utilities.sleep(delay);
      }
    }
  }
  
  Logger.log(`❌ فشل جلب الصفحة بعد ${retries} محاولات: ${lastError?.message}`);
  return null;
}

/**
 * ✅ استخراج البيانات من HTML الصفحة - مُصحح
 */
function extractDataFromHeadoutHTML(html, voucherUrl) {
  Logger.log('📄 استخراج البيانات من صفحة Headout...');
  
  const bookingIdMatch = voucherUrl.match(/voucher\/(\d+)/);
  const referenceNumber = bookingIdMatch ? bookingIdMatch[1] : null;
  
  const bookingData = {
    reference_number: referenceNumber,
    agency: 'Headout',
    cancellation_status: 'Active',
    voucher_link: voucherUrl
  };
  
  // استخدام دوال منفصلة لاستخراج كل حقل
  bookingData.real_product_name = extractFieldFromHTML(html, 'product_name');
  bookingData.main_Customer = extractFieldFromHTML(html, 'customer_name');
  bookingData.email = extractFieldFromHTML(html, 'email');
  bookingData.phone = extractFieldFromHTML(html, 'phone');
  bookingData.date_trip = extractFieldFromHTML(html, 'date');
  bookingData.time_trip = extractFieldFromHTML(html, 'time');
  bookingData.Pickup_location = extractFieldFromHTML(html, 'pickup');
  
  // استخراج الأعداد
  const guestsInfo = extractGuestsFromHTML(html);
  bookingData.Adult = guestsInfo.adults;
  bookingData.Child = guestsInfo.children;
  
  // استخراج السعر
  bookingData['Total price USD'] = extractPriceFromHTML(html);
  
  // استخراج الوجهة من اسم الرحلة
  if (bookingData.real_product_name) {
    bookingData.destination = extractDestinationFromTourName(bookingData.real_product_name);
  }
  
  // دمج التاريخ والوقت إذا وُجدا
  if (bookingData.date_trip && bookingData.time_trip) {
    try {
      const combinedDateTime = `${bookingData.date_trip} ${bookingData.time_trip}`;
      const parsedDate = new Date(combinedDateTime);
      if (!isNaN(parsedDate.getTime())) {
        bookingData.date_trip = parsedDate.toISOString();
      }
    } catch (error) {
      Logger.log(`⚠️ خطأ في معالجة التاريخ: ${error.message}`);
    }
    delete bookingData.time_trip;
  }
  
  return bookingData;
}

/**
 * ✅ دالة مساعدة لاستخراج حقل من HTML
 */
function extractFieldFromHTML(html, fieldType) {
  const patterns = {
    'product_name': [
      /<h1[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)/i,
      /<div[^>]*class="[^"]*product-name[^"]*"[^>]*>([^<]+)/i,
      /<title>([^<]+)<\/title>/i
    ],
    'customer_name': [
      /(?:Customer Name|Name|Guest Name)[:\s]*<[^>]+>([^<]+)/i,
      /(?:Lead Traveler|Primary Guest)[:\s]*([^<\n]+)/i,
      /Name:\s*([^\n<]+)/i
    ],
    'email': [
      /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/
    ],
    'phone': [
      /(?:Phone|Mobile|Contact)[:\s]*([+\d\s\-()]+)/i,
      /\+\d{1,3}[\s\-]?\d{6,14}/
    ],
    'date': [
      /(?:Date|Visit Date|Experience Date)[:\s]*([^<\n]+)/i,
      /<span[^>]*class="[^"]*date[^"]*"[^>]*>([^<]+)/i
    ],
    'time': [
      /(?:Time|Start Time|Visit Time)[:\s]*([^<\n]+)/i,
      /<span[^>]*class="[^"]*time[^"]*"[^>]*>([^<]+)/i
    ],
    'pickup': [
      /(?:Pickup|Hotel|Meeting Point)[:\s]*([^<\n]+)/i
    ]
  };
  
  const fieldPatterns = patterns[fieldType] || [];
  
  for (const pattern of fieldPatterns) {
    const match = html.match(pattern);
    if (match && match[1]) {
      return match[1].trim();
    }
  }
  
  return null;
}

/**
 * ✅ استخراج معلومات الضيوف من HTML
 */
function extractGuestsFromHTML(html) {
  const result = { adults: 0, children: 0 };
  
  // البحث عن أنماط مختلفة للضيوف
  const patterns = [
    /(?:Guests?|Travelers?|Pax)[:\s]*([^<\n]+)/i,
    /(\d+)\s*(?:Adult|adults?)/gi,
    /(\d+)\s*(?:Child|children)/gi,
    /Guest Numbers:\s*([^\n]+)/i
  ];
  
  for (const pattern of patterns) {
    const matches = html.match(pattern);
    if (matches) {
      const text = matches[0] || matches[1];
      
      const adultMatch = text.match(/(\d+)\s*adult/i);
      const childMatch = text.match(/(\d+)\s*child/i);
      
      if (adultMatch) result.adults = parseInt(adultMatch[1]) || 0;
      if (childMatch) result.children = parseInt(childMatch[1]) || 0;
      
      if (result.adults > 0 || result.children > 0) break;
    }
  }
  
  return result;
}

/**
 * ✅ استخراج السعر من HTML
 */
function extractPriceFromHTML(html) {
  const patterns = [
    /(?:Total|Amount|Price)[:\s]*(?:USD?\s*)?([0-9,]+\.?\d*)/i,
    /\$\s*([0-9,]+\.?\d*)/
  ];
  
  for (const pattern of patterns) {
    const match = html.match(pattern);
    if (match && match[1]) {
      return parseFloat(match[1].replace(/[,$]/g, '')) || null;
    }
  }
  
  return null;
}

/**
 * ✅ استخراج الوجهة من اسم الرحلة
 */
function extractDestinationFromTourName(tourName) {
  if (!tourName) return CONFIG.PROCESSING.DEFAULT_DESTINATION;
  
  Logger.log(`🗺️ استخراج الوجهة من: ${tourName}`);
  
  // البحث عن "From [Destination]:" في بداية اسم الرحلة
  const fromPattern = /^From\s+([^:]+):/i;
  const fromMatch = tourName.match(fromPattern);
  
  if (fromMatch && fromMatch[1]) {
    const destination = fromMatch[1].trim();
    Logger.log(`✅ الوجهة المستخرجة: ${destination}`);
    return destination;
  }
  
  // البحث عن "in [Destination]" في اسم الرحلة
  const inPattern = /\bin\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b/;
  const inMatch = tourName.match(inPattern);
  
  if (inMatch && inMatch[1]) {
    const destination = inMatch[1].trim();
    Logger.log(`✅ الوجهة المستخرجة: ${destination}`);
    return destination;
  }
  
  // قائمة المدن المصرية الشائعة للبحث عنها
  const egyptianCities = [
    'Cairo', 'Giza', 'Alexandria', 'Luxor', 'Aswan', 
    'Hurghada', 'Sharm El Sheikh', 'Dahab', 'Marsa Alam',
    'Port Said', 'Suez', 'Fayoum', 'Siwa', 'Abu Simbel'
  ];
  
  for (const city of egyptianCities) {
    if (tourName.toLowerCase().includes(city.toLowerCase())) {
      Logger.log(`✅ الوجهة المستخرجة: ${city}`);
      return city;
    }
  }
  
  Logger.log(`⚠️ لم يتم العثور على وجهة - استخدام الافتراضي: ${CONFIG.PROCESSING.DEFAULT_DESTINATION}`);
  return CONFIG.PROCESSING.DEFAULT_DESTINATION;
}

/**
 * ✅ استخراج البيانات بالذكاء الاصطناعي من HTML
 */
function extractDataFromHTMLWithAI(html, referenceNumber) {
  Logger.log('🤖 استخدام AI لاستخراج البيانات من HTML...');
  
  const cleanedHTML = cleanHTMLForAI(html);
  
  const prompt = `
Extract booking information from this Headout voucher HTML page.

REQUIRED FIELDS:
- reference_number: "${referenceNumber}" (already known)
- real_product_name: Full tour/product name
- destination: Extract from tour name (look for "From [City]:" or "in [City]")
- main_Customer: Customer full name
- email: Customer email
- phone: Customer phone with country code
- date_trip: Visit date in ISO format (YYYY-MM-DDTHH:MM:SS.sssZ)
- Adult: Number of adults (integer)
- Child: Number of children (integer)
- Total price USD: Total price in USD (number only)
- Pickup_location: Hotel/pickup address
- tour_name: Simplified tour name or option (extract from "Tour Name on Supplier side" if available)
- Tour_language: Tour language if mentioned

RULES:
1. Return ONLY valid JSON
2. Use exact field names as listed above
3. Omit fields if not found
4. For destination: extract from tour name, look for "From [City]:" or "in [City]"
5. cancellation_status is always "Active"
6. Parse dates to ISO format

HTML CONTENT:
"""
${cleanedHTML}
"""

Return only JSON:`;

  try {
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
    
    if (res.getResponseCode() === 200) {
      const json = JSON.parse(res.getContentText());
      const reply = json.choices?.[0]?.message?.content;
      
      if (reply) {
        const jsonMatch = reply.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          const extractedData = JSON.parse(jsonMatch[0]);
          
          extractedData.reference_number = referenceNumber;
          extractedData.agency = 'Headout';
          extractedData.cancellation_status = 'Active';
          
          if (!extractedData.destination && extractedData.real_product_name) {
            extractedData.destination = extractDestinationFromTourName(extractedData.real_product_name);
          }
          
          return extractedData;
        }
      }
    }
  } catch (error) {
    Logger.log(`⚠️ خطأ في AI: ${error.message}`);
  }
  
  return null;
}

/**
 * ✅ تنظيف HTML للـ AI
 */
function cleanHTMLForAI(html) {
  // إزالة السكريبتات والأنماط
  let cleaned = html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  cleaned = cleaned.replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '');
  cleaned = cleaned.replace(/<!--[\s\S]*?-->/g, '');
  
  const importantSections = [];
  const keywords = [
    'booking', 'reference', 'customer', 'name', 'email', 'phone',
    'date', 'time', 'adult', 'child', 'price', 'total', 'pickup',
    'hotel', 'tour', 'product', 'voucher', 'guest', 'traveler'
  ];
  
  const lines = cleaned.split('\n');
  for (const line of lines) {
    const lowerLine = line.toLowerCase();
    if (keywords.some(keyword => lowerLine.includes(keyword))) {
      importantSections.push(line);
    }
  }
  
  const result = importantSections.join('\n');
  return result.length > 5000 ? result.substring(0, 5000) : result;
}

// ================================================
// 🤖 استخراج البيانات بالذكاء الاصطناعي
// ================================================

/**
 * ✅ تحديد نوع الإيميل
 */
function determineEmailType(emailBody) {
  const indicators = {
    'Headout': [
      'headout.com', 
      'Greetings from Headout', 
      'Team Headout', 
      'Headout reference number',
      'reservation has been confirmed'
    ],
    'GetYourGuide': ['getyourguide.com', 'GetYourGuide Team', 'booking detail change'],
    'Viator': ['viator.com', 'Viator Booking Confirmation', 'Booking Reference'],
    'Tiqets': ['Tiqets.com', 'tiqets.com', 'Booking notification from Tiqets']
  };
  
  for (const [type, keywords] of Object.entries(indicators)) {
    if (keywords.some(keyword => emailBody.toLowerCase().includes(keyword.toLowerCase()))) {
      return type;
    }
  }
  
  return 'Unknown';
}

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
 * ✅ استخراج جميع الحقول بواسطة AI
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
    "reference_number": "Booking reference, Headout reference number (e.g., 27028831)",
    "real_product_name": "Full product/tour name exactly as written in 'Tour Name'",
    "tour_name": "Simplified tour name from 'Tour Name on Supplier side' (this will be used as Option)",
    "tour_option": "Tour option, ticket type (if different from tour_name)",
    "date_trip": "Visit date in ISO format (YYYY-MM-DDTHH:MM:SS.sssZ)",
    "main_Customer": "Customer full name",
    "email": "Customer email",
    "phone": "Customer phone with country code",
    "Adult": "Number of adults (integer)",
    "Child": "Number of children (integer)",
    "Total price EUR": "Total in EUR (number only)",
    "Total price USD": "Total in USD (number only)",
    "Tour_language": "Tour language",
    "Pickup location": "Hotel address",
    "destination": "Extract from tour name (From [City]: or in [City])",
    "cancellation_status": "'Active', 'Canceled', or 'Changed'",
    "voucher_link": "Voucher URL if present"
  };
  
  const headoutSpecificInstructions = emailType === 'Headout' ? `
SPECIAL INSTRUCTIONS FOR HEADOUT:
- Extract reference_number from "The Headout reference number for this reservation is [NUMBER]"
- Extract main_Customer from "Name: [NAME]"
- Extract phone from "Phone: [PHONE]"
- Extract real_product_name from "Tour Name: [FULL_TOUR_NAME]" (the complete tour name)
- Extract tour_name from "Tour Name on Supplier side: [SIMPLIFIED_NAME]" (this will be used as Option)
- Extract destination from tour name: look for "From [City]:" or "in [City]"
- Parse "Guest Numbers: X Adult, Y Child" correctly
- Set agency as "Headout"
- IMPORTANT: real_product_name should be the FULL tour name, tour_name should be the simplified version
` : '';

  return `
Extract booking information from this ${emailType} email.

FIELD DEFINITIONS:
${Object.entries(fieldDescriptions).map(([k, v]) => `${k}: ${v}`).join('\n')}

${headoutSpecificInstructions}

RULES:
1. Return ONLY valid JSON
2. Extract destination from tour name (From [City]: or in [City])
3. Dates in ISO format with Cairo timezone (UTC+2)
4. Numbers as integers/floats
5. Omit missing fields

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
    cancellation_status: "Active",
    Adult: 0,
    Child: 0,
    Infant: 0
  };
  
  const patterns = {
    reference_number: [
      /Headout reference number[^0-9]*(\d+)/i,
      /reference number is\s*(\d+)/i
    ],
    main_Customer: [
      /Name:\s*([^\n]+)/i,
      /Customer Name:\s*([^\n]+)/i
    ],
    phone: [
      /Phone:\s*([+\d\s-]+)/i
    ],
    email: [
      /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i
    ],
    real_product_name: [
      /Tour Name:\s*([^\n]+)/i
    ],
    tour_name: [
      /Tour Name on Supplier side:\s*([^\n]+)/i
    ],
    Pickup_location: [
      /Hotel Address\s*:\s*([^\n]+)/i
    ]
  };
  
  for (const [field, regexList] of Object.entries(patterns)) {
    for (const regex of regexList) {
      const match = emailBody.match(regex);
      if (match) {
        data[field] = match[1].trim();
        
        if (field === 'real_product_name') {
          data.destination = extractDestinationFromTourName(match[1]);
        }
        break;
      }
    }
  }
  
  const guestMatch = emailBody.match(/Guest Numbers:\s*([^\n]+)/i);
  if (guestMatch) {
    const guestStr = guestMatch[1];
    const adultMatch = guestStr.match(/(\d+)\s*Adult/i);
    const childMatch = guestStr.match(/(\d+)\s*Child/i);
    
    if (adultMatch) data.Adult = parseInt(adultMatch[1]) || 0;
    if (childMatch) data.Child = parseInt(childMatch[1]) || 0;
  }
  
  if (!data.destination) {
    data.destination = CONFIG.PROCESSING.DEFAULT_DESTINATION;
  }
  
  return data;
}

/**
 * ✅ تطبيق المنطق التجاري
 */
function applyBusinessLogicWithCairoDefault(data) {
  standardizeTourInfo(data);
  formatDateUniversal(data);
  
  if ((!data.destination || data.destination === CONFIG.PROCESSING.DEFAULT_DESTINATION) 
      && data.real_product_name) {
    data.destination = extractDestinationFromTourName(data.real_product_name);
  }
  
  if (!data.cancellation_status) {
    data.cancellation_status = 'Active';
  }
  
  return data;
}

// ================================================
// 🔧 معالجة الرسائل
// ================================================

/**
 * ✅ معالجة رسالة واحدة بأمان
 */
function processMessageSafely(message) {
  try {
    const body = message.getPlainBody() || message.getBody();
    const emailType = determineEmailType(body);
    
    if (emailType === 'Headout') {
      const voucherLink = extractVoucherLink(body);
      
      if (!voucherLink) {
        Logger.log('⚠️ لم يتم العثور على رابط Voucher - محاولة استخراج من الإيميل');
        return processHeadoutFromEmail(body);
      }
      
      Logger.log(`🔗 رابط Voucher: ${voucherLink}`);
      
      const htmlContent = fetchHeadoutVoucherPage(voucherLink);
      
      if (!htmlContent) {
        Logger.log('⚠️ فشل جلب الصفحة - محاولة استخراج من الإيميل');
        return processHeadoutFromEmail(body);
      }
      
      let bookingData = extractDataFromHeadoutHTML(htmlContent, voucherLink);
      
      if (!bookingData.main_Customer || !bookingData.date_trip) {
        Logger.log('📊 البيانات غير كاملة - استخدام AI');
        const aiData = extractDataFromHTMLWithAI(htmlContent, bookingData.reference_number);
        
        if (aiData) {
          bookingData = { ...bookingData, ...aiData };
        }
      }
      
      const emailData = extractBasicDataFromEmail(body);
      for (const [key, value] of Object.entries(emailData)) {
        if (!bookingData[key] && value) {
          bookingData[key] = value;
        }
      }
      
      bookingData = sanitizeAirtableData(bookingData);
      
      if (!bookingData.reference_number) {
        Logger.log('⚠️ لا يوجد رقم حجز');
        return false;
      }
      
      if (isBookingExists(bookingData.reference_number)) {
        Logger.log(`📋 الحجز ${bookingData.reference_number} موجود مسبقاً`);
        return true;
      }
      
      const sent = sendDataToAirtableWithRetry(bookingData);
      
      if (sent) {
        Logger.log(`✅ تمت معالجة الحجز: ${bookingData.reference_number}`);
        return true;
      } else {
        Logger.log(`⚠️ فشل إرسال الحجز: ${bookingData.reference_number}`);
        return false;
      }
      
    } else {
      return processNormalBooking(body);
    }
    
  } catch (error) {
    Logger.log(`❌ خطأ في معالجة الرسالة: ${error.message}`);
    return false;
  }
}

/**
 * ✅ استخراج البيانات الأساسية من الإيميل
 */
function extractBasicDataFromEmail(emailBody) {
  const data = {};
  
  const patterns = {
    main_Customer: /Name:\s*([^\n]+)/i,
    phone: /Phone:\s*([+\d\s-]+)/i,
    email: /([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/,
    reference_number: /Headout reference number[^0-9]*(\d+)/i,
    real_product_name: /Tour Name:\s*([^\n]+)/i,
    tour_name: /Tour Name on Supplier side:\s*([^\n]+)/i
  };
  
  for (const [field, pattern] of Object.entries(patterns)) {
    const match = emailBody.match(pattern);
    if (match && match[1]) {
      data[field] = match[1].trim();
      
      // استخراج الوجهة من اسم الرحلة الكامل
      if (field === 'real_product_name') {
        data.destination = extractDestinationFromTourName(match[1]);
      }
    }
  }
  
  const guestMatch = emailBody.match(/Guest Numbers:\s*([^\n]+)/i);
  if (guestMatch) {
    const guestStr = guestMatch[1];
    const adultMatch = guestStr.match(/(\d+)\s*Adult/i);
    const childMatch = guestStr.match(/(\d+)\s*Child/i);
    
    if (adultMatch) data.Adult = parseInt(adultMatch[1]) || 0;
    if (childMatch) data.Child = parseInt(childMatch[1]) || 0;
  }
  
  return data;
}

/**
 * ✅ معالجة Headout من الإيميل فقط
 */
function processHeadoutFromEmail(emailBody) {
  Logger.log('📧 معالجة من الإيميل مباشرة (طريقة احتياطية)');
  
  let bookingData = extractBookingDataWithAI(emailBody);
  
  if (!bookingData.reference_number) {
    Logger.log('⚠️ لا يوجد رقم حجز');
    return false;
  }
  
  bookingData = enhanceBookingDataWithFallback(bookingData, emailBody);
  bookingData = enforceDefaultDestination(bookingData);
  bookingData = sanitizeAirtableData(bookingData);
  
  if (isBookingExists(bookingData.reference_number)) {
    Logger.log(`📋 الحجز ${bookingData.reference_number} موجود مسبقاً`);
    return true;
  }
  
  const sent = sendDataToAirtableWithRetry(bookingData);
  
  return sent;
}

/**
 * ✅ معالجة الحجوزات العادية
 */
function processNormalBooking(emailBody) {
  let bookingData = extractBookingDataWithAI(emailBody);
  
  if (!bookingData.reference_number) {
    Logger.log('⚠️ لا يوجد رقم حجز');
    return false;
  }
  
  bookingData = enhanceBookingDataWithFallback(bookingData, emailBody);
  bookingData = sanitizeAirtableData(bookingData);
  
  const sent = sendDataToAirtableWithRetry(bookingData);
  
  return sent;
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
  
  Logger.log(`📊 الحقول المرسلة: ${Object.keys(fields).join(', ')}`);
  
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
    updateExistingRecord(data.records[0], payload, headers, baseUrl);
  } else {
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
  
  protectExistingFields(record, payload);
  
  // التحقق من وجود البيانات وتنسيقها بشكل صحيح
  let updatePayload;
  
  if (!payload) {
    Logger.log('⚠️ لا توجد بيانات للتحديث');
    return;
  }
  
  // التأكد من أن البيانات في تنسيق صحيح
  if (payload.fields) {
    updatePayload = payload;
  } else {
    updatePayload = { fields: payload };
  }
  
  // التحقق من أن الحقول موجودة
  if (!updatePayload.fields || Object.keys(updatePayload.fields).length === 0) {
    Logger.log('⚠️ لا توجد حقول للتحديث');
    return;
  }
  
  const updateResponse = UrlFetchApp.fetch(`${baseUrl}/${recordId}`, {
    method: "patch",
    headers,
    payload: JSON.stringify(updatePayload),
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
  
  const createPayload = payload.fields ? payload : { fields: payload.fields || payload };
  
  Logger.log(`📤 البيانات المرسلة: ${JSON.stringify(createPayload).substring(0, 500)}`);
  
  const createResponse = UrlFetchApp.fetch(baseUrl, {
    method: "post",
    headers,
    payload: JSON.stringify(createPayload),
    muteHttpExceptions: true
  });
  
  const responseCode = createResponse.getResponseCode();
  const responseText = createResponse.getContentText();
  
  if (responseCode >= 400) {
    Logger.log(`❌ خطأ في Airtable: ${responseCode}`);
    Logger.log(`📝 التفاصيل: ${responseText}`);
    throw new Error(`API error: ${responseText}`);
  } else {
    Logger.log(`✅ تم إنشاء السجل بنجاح`);
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
  if (!bookingData.destination || bookingData.destination === '') {
    bookingData.destination = CONFIG.PROCESSING.DEFAULT_DESTINATION;
  }
  return bookingData;
}

/**
 * ✅ تنقيح البيانات لـ Airtable
 */
function sanitizeAirtableData(data) {
  const result = {...data};
  
  const priceFields = ["Total price EUR", "Total price USD"];
  for (const field of priceFields) {
    if (result[field] !== undefined && result[field] !== null) {
      if (typeof result[field] === 'string') {
        const cleanPrice = result[field].replace(/[^\d.,]/g, '').replace(',', '.');
        result[field] = parseFloat(cleanPrice) || null;
      }
    }
  }
  
  if (result.date_trip) {
    result.date_trip = formatDateForAirtable(result.date_trip);
  }
  
  if (!result.destination || result.destination === '') {
    if (result.real_product_name) {
      result.destination = extractDestinationFromTourName(result.real_product_name);
    } else {
      result.destination = CONFIG.PROCESSING.DEFAULT_DESTINATION;
    }
  }
  
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
 * ✅ تنسيق التاريخ الشامل
 */
function formatDateUniversal(data) {
  if (!data.date_trip) return;
  
  try {
    const date = new Date(data.date_trip);
    if (!isNaN(date.getTime())) {
      data.date_trip = date.toISOString();
    }
  } catch (error) {
    Logger.log(`⚠️ خطأ في تنسيق التاريخ: ${error.message}`);
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
    "trip Name": data.real_product_name,
    "Real Product Name": data.real_product_name,
    "Net Rate": data.net_rate,
    "Date Trip": data.date_trip,
    "Customer Name": data.main_Customer,
    "Option": data.tour_name,
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
    "Hotel Name": data["Pickup location"] || data.Pickup_location,
    "Booking Status": data.cancellation_status,
    "CXL Date": data.cancellation_date,
    "Google Maps": data["Google Map"],
    "Traveler name": data.traveler_name,
    "Total price EUR": data["Total price EUR"],
    "Total price USD ": data["Total price USD"],
    "Voucher Link": data.voucher_link
  };
  
  const fields = {};
  
  for (const key in allFields) {
    const value = allFields[key];
    
    if (value === undefined || value === null || value === "") {
      continue;
    }
    
    if (typeof value === "number" && value === 0) {
      const optionalNumericFields = ["STD", "CHD", "Inf", "Youth"];
      if (optionalNumericFields.includes(key)) {
        continue;
      }
    }
    
    fields[key] = value;
  }
  
  if (!fields["Booking Nr."]) {
    Logger.log('⚠️ رقم الحجز مطلوب');
    return null;
  }
  
  Logger.log(`📝 عدد الحقول المعدة للإرسال: ${Object.keys(fields).length}`);
  
  return fields;
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
📊 تقرير معالجة الحجوزات Headout
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
      `معالج الحجوزات Headout: ${subject}`,
      body
    );
  } catch (err) {
    Logger.log(`⚠️ فشل إرسال التنبيه: ${err.message}`);
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
    { "Product ID": "484786", "Title": "Hurghada: Orange Bay Day Trip with Water Sports and Lunch" }
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
// 🔧 دوال الأدوات والصيانة
// ================================================

/**
 * ✅ مسح الكاش (للصيانة)
 */
function clearProcessingCache() {
  try {
    const cache = CacheService.getScriptCache();
    cache.removeAll([]);
    
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
// 🧪 دوال الاختبار الشاملة
// ================================================

/**
 * ✅ اختبار استخراج من رابط Headout
 */
function testHeadoutLinkExtraction() {
  const testEmail = `
Hello Team,
Greetings from Headout. The following reservation has been confirmed.
Customer Details:
Name: Juhana Kerppola
Phone: +358408449269
Reservation Details:
Tour Name: From Luxor: Half-Day Karnak Temple and Luxor Temple Shared Guided Tour With Lunch
Tour Name on Supplier side: Karnak and Luxor Temples Tour
Date : September 24, 2025
Time: 07:00 PM
Guest Numbers: 3 Adult
The Headout reference number for this reservation is 27028831.
Please find your voucher issued to the customer HERE.
https://www.headout.com/voucher/27028831?secureBookingId=EOFrjNsPXgkx9J_1OjL-6JfX1NNgZDsdhTUeF5ueZXpCxhr7Fatv42suPg_GvOd0TS63YDX7dh8Hh-4LLCmhGw%3D%3D
Warm regards,
Team Headout
`;

  Logger.log('🧪 اختبار استخراج رابط Headout');
  
  const voucherLink = extractVoucherLink(testEmail);
  Logger.log(`🔗 الرابط المستخرج: ${voucherLink}`);
  
  const tourName1 = "From Luxor: Half-Day Karnak Temple and Luxor Temple Shared Guided Tour With Lunch";
  const destination1 = extractDestinationFromTourName(tourName1);
  Logger.log(`📍 الوجهة من "${tourName1}": ${destination1}`);
  
  const tourName2 = "5-Star Nile Dinner Cruise in Cairo with Live Entertainment (Nile Pharaoh)";
  const destination2 = extractDestinationFromTourName(tourName2);
  Logger.log(`📍 الوجهة من "${tourName2}": ${destination2}`);
  
  if (voucherLink) {
    const html = fetchHeadoutVoucherPage(voucherLink);
    if (html) {
      const data = extractDataFromHeadoutHTML(html, voucherLink);
      Logger.log('📊 البيانات المستخرجة من الصفحة:');
      for (const [key, value] of Object.entries(data)) {
        if (value !== null && value !== undefined && value !== '') {
          Logger.log(`  ${key}: ${value}`);
        }
      }
    } else {
      Logger.log('⚠️ لم يتم جلب الصفحة');
    }
  }
  
  const emailData = extractBasicDataFromEmail(testEmail);
  Logger.log('\n📧 البيانات المستخرجة من الإيميل:');
  for (const [key, value] of Object.entries(emailData)) {
    if (value !== null && value !== undefined && value !== '') {
      Logger.log(`  ${key}: ${value}`);
    }
  }
}

/**
 * ✅ اختبار معالجة إيميل Headout كامل
 */
function testProcessHeadoutEmail() {
  const threads = GmailApp.search(`label:${CONFIG.PROCESSING.LABEL} -is:starred`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لا توجد رسائل Headout للاختبار');
    
    Logger.log('📝 استخدام رسالة اختبار وهمية...');
    
    const testEmailBody = `
Hello Team,
Greetings from Headout. The following reservation has been confirmed.

Customer Details:
Name: Test Customer
Phone: +1234567890
Email: test@example.com

Reservation Details:
Tour Name: From Luxor: Half-Day Karnak Temple and Luxor Temple Shared Guided Tour With Lunch
Tour Name on Supplier side: Karnak and Luxor Temples Tour
Date : December 15, 2025
Time: 09:00 AM
Guest Numbers: 2 Adult, 1 Child

The Headout reference number for this reservation is 99999999.

Please find your voucher issued to the customer HERE.
https://www.headout.com/voucher/99999999?secureBookingId=TEST

Warm regards,
Team Headout
`;
    
    const bookingData = extractBookingDataWithAI(testEmailBody);
    
    Logger.log('📊 البيانات المستخرجة:');
    for (const [key, value] of Object.entries(bookingData)) {
      if (value !== null && value !== undefined && value !== '' && value !== 0) {
        Logger.log(`  ${key}: ${value}`);
      }
    }
    
    return bookingData;
  }
  
  const message = threads[0].getMessages()[0];
  Logger.log(`📧 معالجة رسالة: ${message.getSubject()}`);
  
  const success = processMessageSafely(message);
  
  Logger.log(`\n📋 نتيجة المعالجة: ${success ? '✅ نجح' : '❌ فشل'}`);
  
  return success;
}

/**
 * ✅ اختبار استخراج الوجهات من أسماء مختلفة
 */
function testDestinationExtraction() {
  const testCases = [
    {
      tour: "From Luxor: Half-Day Karnak Temple and Luxor Temple Shared Guided Tour",
      expected: "Luxor"
    },
    {
      tour: "From Cairo: Full-Day Tour to Giza Pyramids and Egyptian Museum",
      expected: "Cairo"
    },
    {
      tour: "From Aswan: Abu Simbel Temple Day Tour by Road",
      expected: "Aswan"
    },
    {
      tour: "5-Star Nile Dinner Cruise in Cairo with Live Entertainment",
      expected: "Cairo"
    },
    {
      tour: "Snorkeling Trip in Hurghada: Full-Day Red Sea Adventure",
      expected: "Hurghada"
    },
    {
      tour: "From Sharm El Sheikh: Day Trip to St. Catherine's Monastery",
      expected: "Sharm El Sheikh"
    },
    {
      tour: "Alexandria Full-Day Historical Tour from Cairo",
      expected: "Cairo"  // تم التصحيح لأنه من القاهرة
    },
    {
      tour: "Quad Bike Safari Adventure in Dahab Desert",
      expected: "Dahab"
    },
    {
      tour: "Random Tour Without City Name",
      expected: CONFIG.PROCESSING.DEFAULT_DESTINATION
    }
  ];
  
  Logger.log('🧪 اختبار استخراج الوجهات:');
  Logger.log('================================');
  
  let correct = 0;
  let total = testCases.length;
  
  for (const testCase of testCases) {
    const result = extractDestinationFromTourName(testCase.tour);
    const isCorrect = result === testCase.expected;
    
    Logger.log(`\n📍 الرحلة: "${testCase.tour}"`);
    Logger.log(`   المتوقع: ${testCase.expected}`);
    Logger.log(`   النتيجة: ${result}`);
    Logger.log(`   الحالة: ${isCorrect ? '✅ صحيح' : '❌ خطأ'}`);
    
    if (isCorrect) correct++;
  }
  
  Logger.log('\n================================');
  Logger.log(`📊 النتيجة النهائية: ${correct}/${total} صحيح (${Math.round(correct/total*100)}%)`);
}

/**
 * ✅ اختبار نظام القفل
 */
function testLockSystem() {
  const lock = LockService.getScriptLock();
  
  Logger.log('🔒 اختبار نظام القفل...');
  
  const hasLock1 = lock.tryLock(1000);
  Logger.log(`محاولة 1: ${hasLock1 ? '✅ نجح' : '❌ فشل'}`);
  
  if (hasLock1) {
    const lock2 = LockService.getScriptLock();
    const hasLock2 = lock2.tryLock(1000);
    Logger.log(`محاولة 2 (مع قفل نشط): ${hasLock2 ? '✅ نجح' : '❌ فشل'}`);
    
    lock.releaseLock();
    Logger.log('🔓 تم تحرير القفل');
    
    const lock3 = LockService.getScriptLock();
    const hasLock3 = lock3.tryLock(1000);
    Logger.log(`محاولة 3 (بعد التحرير): ${hasLock3 ? '✅ نجح' : '❌ فشل'}`);
    
    if (hasLock3) {
      lock3.releaseLock();
    }
  }
}

/**
 * ✅ اختبار الاتصال بـ Airtable
 */
function testAirtableConnection() {
  Logger.log('🔌 اختبار الاتصال بـ Airtable...');
  
  try {
    const headers = {
      Authorization: `Bearer ${CONFIG.KEYS.AIRTABLE}`,
      'Content-Type': 'application/json'
    };
    
    const response = UrlFetchApp.fetch(CONFIG.AIRTABLE.URL + '?maxRecords=1', {
      method: "get",
      headers,
      muteHttpExceptions: true
    });
    
    const responseCode = response.getResponseCode();
    
    if (responseCode === 200) {
      Logger.log('✅ الاتصال بـ Airtable ناجح');
      const data = JSON.parse(response.getContentText());
      Logger.log(`📊 عدد السجلات: ${data.records ? data.records.length : 0}`);
    } else {
      Logger.log(`❌ فشل الاتصال: HTTP ${responseCode}`);
      Logger.log(response.getContentText());
    }
    
  } catch (error) {
    Logger.log(`❌ خطأ في الاتصال: ${error.message}`);
  }
}

/**
 * ✅ اختبار الاتصال بـ DeepSeek AI
 */
function testDeepSeekConnection() {
  Logger.log('🤖 اختبار الاتصال بـ DeepSeek AI...');
  
  try {
    const options = {
      method: "post",
      contentType: "application/json",
      headers: { Authorization: `Bearer ${CONFIG.KEYS.DEEPSEK}` },
      payload: JSON.stringify({
        model: CONFIG.DEEPSEK.MODEL,
        messages: [{ 
          role: "user", 
          content: "Extract destination from: 'From Cairo: Giza Pyramids Tour'. Return only the city name." 
        }],
        temperature: 0
      }),
      muteHttpExceptions: true
    };
    
    const res = UrlFetchApp.fetch(CONFIG.DEEPSEK.ENDPOINT, options);
    const responseCode = res.getResponseCode();
    
    if (responseCode === 200) {
      Logger.log('✅ الاتصال بـ DeepSeek AI ناجح');
      const json = JSON.parse(res.getContentText());
      const reply = json.choices?.[0]?.message?.content;
      Logger.log(`📝 الاستجابة: ${reply}`);
    } else {
      Logger.log(`❌ فشل الاتصال: HTTP ${responseCode}`);
      Logger.log(res.getContentText());
    }
    
  } catch (error) {
    Logger.log(`❌ خطأ في الاتصال: ${error.message}`);
  }
}

/**
 * ✅ اختبار شامل للنظام
 */
function runCompleteSystemTest() {
  Logger.log('🚀 بدء الاختبار الشامل للنظام');
  Logger.log('=====================================\n');
  
  Logger.log('1️⃣ اختبار الاتصالات:');
  testAirtableConnection();
  testDeepSeekConnection();
  
  Logger.log('\n2️⃣ اختبار نظام القفل:');
  testLockSystem();
  
  Logger.log('\n3️⃣ اختبار استخراج الوجهات:');
  testDestinationExtraction();
  
  Logger.log('\n4️⃣ اختبار معالجة Headout:');
  testHeadoutLinkExtraction();
  
  Logger.log('\n5️⃣ إحصائيات النظام:');
  getSystemStats();
  
  Logger.log('\n=====================================');
  Logger.log('✅ انتهى الاختبار الشامل');
}

// ================================================
// ✅ نهاية معالج الحجوزات المحسّن لـ Headout - الإصدار 2.0
// ================================================