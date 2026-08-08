// ✅ CONFIG: إعدادات التطبيق والمفاتيح
const CONFIG = {
  KEYS: {
  AIRTABLE: 'patPlKVK4bsSNcUY1.6a0bc7165b9eac5ee3050a58ccbeaf1f91517593c9e62a246e70dbae29d679f9',
  DEEPSEK: 'sk-1785f7a14ac84291b785fe5eb374004b' // يجب استبدالها بمفتاح API حقيقي لـ Deepsek
},

  AIRTABLE: {
    BASE_ID: 'appTp5YgSp9DV2HYc',
    TABLE_NAME: 'List',
    get URL() {
      return `https://api.airtable.com/v0/${this.BASE_ID}/${this.TABLE_NAME}`;
    }
  },
DEEPSEK: {
  MODEL: 'deepseek-coder', // نموذج Deepsek المستخدم
  ENDPOINT: 'https://api.deepseek.com/v1/chat/completions', // نقطة نهاية واجهة API لـ Deepsek
  TEMPERATURE: 0
},

  
  PROCESSING: {
    LABEL: "All booking  & Cancelation",
    MAX_THREADS: 500,
    ALERT_EMAIL: 'Ahmadyeladawy@gmail.com'
  },
  
  BOOKING_STATUS: {
    ACTIVE: 'Active',
    CANCELED: 'Canceled',
    UPDATED: 'Changed'
  }
};

// 2. تعريف الحقول والهيكل البياني - Data Structure Definitions
// --------------------------------------------------------

const BOOKING_FIELDS = {
  // الحقول الأساسية المطلوبة
  CRITICAL: [
    "reference_number",
    "date_trip",
    "Adult",
    "tour_option",
    "Pickup location",
    "tour_name",
    "product_id"
  ],
  
  // الحقول الثانوية
  SECONDARY: [
    "Tour_language",
    "email",
    "main_Customer",
    "real_product_name",
    "Total price EUR",
    "Total price USD",
    "Google Map"
  ],
  
  // الحقول الرقمية
  NUMERIC: ['Adult', 'Student', 'Child', 'Infant', 'youth'],
  
  // الحقول النصية
  TEXT: ['tour_option', 'Pickup location', 'tour_name', 'product_id'],
  
  // الحقول المحمية من الكتابة
  PROTECTED: [
    "trip Name",
    "Option",
    "des",
    "Customer Email",
    "Product ID",
    "Customer Phone",
    "ADT", "STD", "CHD", "Inf", "Youth",
    "Real Product Name",
    "Customer Name",
    "Guide"
  ],
  
  // الحقول ذات الحماية الشرطية
  CONDITIONALLY_PROTECTED: {
    "Booking Status": ["Canceled"] // لا يتم تحديث إذا كانت القيمة "Canceled"
  }
};

/**
 * تحميل قوائم توحيد الرحلات
 * وظائف مساعدة لتحميل قوائم توحيد الرحلات
 */
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
  { "Product ID": "686037", "Title": "Hurghada: Orange Bay island With Parachute Adventure &amp; Lunch" },
  { "Product ID": "677972", "Title": "Sharm El-Sheikh: Albatros Aqua Park with Lunch & Transfers" },
  { "Product ID": "443016", "Title": "Hurghada: Red Sea & Desert Horse Riding Tour with Swimming" },
  { "Product ID": "305063", "Title": "Hurghada: Giza Pyramids Day Trip with Nile Boat Tour Option" },
  { "Product ID": "96537", "Title": "Hurghada: Dolphin & Coral Reef Snorkeling Tour with Lunch" },
  { "Product ID": "48112", "Title": "Hurghada: Morning or Sunset Sights Guided Tour with Shopping" },
  { "Product ID": "844930", "Title": "Sharm El-Sheikh: City & Shopping Tour With Old Market Visit" },
  { "Product ID": "21224", "Title": "From Hurghada: Full-Day Trip to Cairo by Plane" },
  { "Product ID": "686022", "Title": "Orange Island, Grand Safari, Dolphin House Package" },
  { "Product ID": "844926", "Title": "Sharm El Sheikh: Mount Sinai & St. Catherine Monastery Tour" },
  { "Product ID": "830640", "Title": "Hurghada: Dolphin Watching Boat Tour with Snorkeling & Lunch" },
  { "Product ID": "28456", "Title": "From Hurghada: Majestic Cairo & Giza Highlights Tour By Van" },
  { "Product ID": "22274", "Title": "Hurghada: Desert Quad Bike and Buggy Adventure with Transfer" },
  { "Product ID": "648980", "Title": "Sharm El-Sheikh: ATV and Camel Ride with BBQ Dinner and Show" },
  { "Product ID": "503557", "Title": "From Sharm: Ras Muhammed & White Island By Boat & intro Dive" },
  { "Product ID": "437716", "Title": "Sharm El-Sheikh: Camel Riding, Stargazing, BBQ Dinner & Show" },
  { "Product ID": "648929", "Title": "Hurghada: Makadi Water World with Lunch & Transfers" },
  { "Product ID": "297555", "Title": "Hurghada: Full-Day Trip to Cairo by Plane" },
  { "Product ID": "28459", "Title": "Hurghada: Guided City Highlights Tour with Shopping Stops" },
  { "Product ID": "361285", "Title": "Hurghada: Sea and Mountains Quad or Buggy Family Tour" },
  { "Product ID": "768763", "Title": "Cairo: Sound and Light Show at Giza Pyramids" },
  { "Product ID": "654789", "Title": "Hurghada: Desert & Sea Horse Riding with + 360° Photos" },
  { "Product ID": "208317", "Title": "Sharm El-Sheikh: Ras Mohamed Half Day Tour & Allah's gate" },
  { "Product ID": "648919", "Title": "Hurghada: Jungle Aqua Park With Lunch & Transfer (Optional)" },
  { "Product ID": "690891", "Title": "Citadel of Salahdin & Mohamed Ali Mosque QR Ticket" },
  { "Product ID": "515712", "Title": "Sharm El-Sheikh: Desert Buggy Safari Adventure" },
  { "Product ID": "515155", "Title": "National Museum of Egypt Skip-the-Line QR Ticket" },
  { "Product ID": "1015784", "Title": "Sharm El-Sheikh : Horse Riding on the Beach" },
  { "Product ID": "305108", "Title": "Hurghada: 2-Day Luxor Tour with Hotel, Balloon, & Nile Boat" },
  { "Product ID": "502836", "Title": "Sharm El-Sheikh: Cairo Full-Day Meet The Pharaohs by Flight" },
  { "Product ID": "22269", "Title": "Hurghada: Quad, Jeep, Camel and Buggy Safari with BBQ Dinner" },
  { "Product ID": "767761", "Title": "Karnak Temple Sound & Light Show QR Ticket with Transfer" },
  { "Product ID": "447583", "Title": "From Port Said: Pyramids and Egyptian Museum Full-Day Tour" },
  { "Product ID": "318107", "Title": "From Cairo: Small-Group Day Trip to Luxor by Plane" },
  { "Product ID": "690891", "Title": "Citadel of Salahdin & Mohamed Ali Mosque QR Ticket" },
  { "Product ID": "648929", "Title": "Hurghada: Makadi Water World with Lunch & Transfers" },
  { "Product ID": "325593", "Title": "From Sharm ElSheikh: The Lost City (Petra) Day Tour by Ferry" },
  { "Product ID": "278712", "Title": "Cairo: Customized Full-Day Private Tour" },
  { "Product ID": "437602", "Title": "Sharm El-Sheikh: Morning Desert ATV Quad or Buggy Adventure" },
  { "Product ID": "485051", "Title": "Hurghada: Dolphin Watching Cruise, Snorkeling & Lunch" },
  { "Product ID": "768763", "Title": "Cairo: Sound and Light Show at Giza Pyramids" },
  { "Product ID": "648919", "Title": "Hurghada: Jungle Aqua Park With Lunch & Transfer (Optional)" },
  { "Product ID": "503045", "Title": "Sharm El-Sheikh: Airport One-Way Private Hotel Transfer" },
  { "Product ID": "432713", "Title": "Hurghada: Eden Island Day Trip with Water Sports and Lunch" },
  { "Product ID": "484822", "Title": "Hurghada: Sharm El Naga Tour with Snorkeling & Lunch" },
  { "Product ID": "829928", "Title": "Full-Day To Luxor Adventure with Valley of the Kings & Lunch" },
  { "Product ID": "829928", "Title": "Luxor: Small Group Adventure, Valley of the Kings, and Lunch" },
  { "Product ID": "829928", "Title": "Luxor: Valley of the Kings and Hatshepsut Temple W/Nile Boat" },
  { "Product ID": "463817", "Title": "Hurghada: Magician plus, VIP Cruise to Orange Bay & Seafood" },
  { "Product ID": "408737", "Title": "Hurghada: Neverland Musical Show Entry Tickets with Pickup" },
  { "Product ID": "318107", "Title": "From Cairo: Small-Group Day Trip to Luxor by Plane" },
  { "Product ID": "188934", "Title": "Marsa Alam: Ancient Cairo & Giza Pyramids Day Trip by Plane" },
  { "Product ID": "614551", "Title": "Marsa Alam:Sataya Reefs Dolphin Snorkeling Cruise with Lunch" },
  { "Product ID": "346421", "Title": "Luxor: Private Full-Day Customized Tour" },
  { "Product ID": "575994", "Title": "Sharm El Sheikh: ATV Dunes & Waves Adventure with Lunch" },
  { "Product ID": "521373", "Title": "Cairo: Giza Pyramids & Sphinx Half-Day Guided Tour" },
  { "Product ID": "521373", "Title": "Private Half-Day Adventure: Giza Pyramids & Sphinx" },  
  { "Product ID": "444195", "Title": "Red Sea: SCUBA Diving Experience & Snorkeling Boot Tour" },
  { "Product ID": "686042", "Title": "Marsa Alam: Snorkeling with Sea Turtles Marsa Mubarak" },
  { "Product ID": "305108", "Title": "Hurghada: 2-Day Luxor Tour with Hotel, Balloon, & Nile Boat" },
  { "Product ID": "325593", "Title": "From Sharm ElSheikh: The Lost City (Petra) Day Tour by Ferry" },
  { "Product ID": "484807", "Title": "Marsa Alam: Hamata Island Snorkeling Trip with Lunch" },
  { "Product ID": "767764", "Title": "Edfu Temple Sound Light Show Entry Ticket with Transfer" },
  { "Product ID": "767767", "Title": "Abu Simbel Sound & light Show - QR Ticket" },
  { "Product ID": "502836", "Title": "Sharm El-Sheikh: Cairo Full-Day Meet The Pharaohs by Flight" },
  { "Product ID": "829926", "Title": "Hurghada: Luxor, Karnak, Hatshepsut and Valley of the Kings" },
  { "Product ID": "829926", "Title": "Small Group Luxor Day Trip with Karnak & Valley of the Kings" },
  { "Product ID": "407665", "Title": "from Hurghada: Abydos, Osireion, and Dendera Day Tour" },
  { "Product ID": "447583", "Title": "From Port Said: Pyramids and Egyptian Museum Full-Day Tour" },
  { "Product ID": "598778", "Title": "Hurghada: Unique Bedouin Craft, Handmade and Star Watching" },
  { "Product ID": "684322", "Title": "Hurghada: Glass Boat and Parasailing Trip with Snorkeling" },
  { "Product ID": "188418", "Title": "Marsa Alam: Valley of the Kings & Karnak Temples Luxor Tour" },
  { "Product ID": "26770", "Title": "Hurghada: Full-Day Tour to Cairo by Plane with Egyptologist" },
  { "Product ID": "408766", "Title": "Cairo: Egyptian Museum and National Museum Private Tour" },
  { "Product ID": "291325", "Title": "From Marsa Alam: Private Day Trip to Luxor by Car" },
  { "Product ID": "592824", "Title": "Cairo: Private Jet Sightseeing Tour" },
  { "Product ID": "447809", "Title": "From Sharm El-Sheikh: Giza Day Trip with Lunch and Transfer" },
  { "Product ID": "506697", "Title": "Cairo: 5-Day Egypt Itinerary for Cairo and the Pyramids" },
  { "Product ID": "686036", "Title": "Hurghada: Neverland Aqua Park with Transfers (Optional)" },
  { "Product ID": "446349", "Title": "Giza: Grand Egyptian Museum, Old Cairo and Khan Al-khalili" },
  { "Product ID": "654616", "Title": "Hurghada: Mega Jeep safari, ATV & Camel & with Bedouin vibe" },
  { "Product ID": "654715", "Title": "Sharm El-Sheikh: Ras Mohammed & White Island Cruise" },
  { "Product ID": "844932", "Title": "Sharm El Sheikh: Private City Tour with Seafood Dinner" },
  { "Product ID": "684287", "Title": "Hurghada: Grand Aquarium & Zoo Tickets with Hotel Transfers" },
  { "Product ID": "521722", "Title": "Cairo: Nile Dinner Cruise with Belly Dancer Show and Music" },
  { "Product ID": "449263", "Title": "Cairo: 4-Day Nile Cruise Aswan to Luxor with Balloon Flight" },
  { "Product ID": "444061", "Title": "Marsa Alam: Desert Stargazing Tour with Camel Ride & Dinner" },
  { "Product ID": "522810", "Title": "13-Day Egypt: Cairo, Nile Cruise, Luxor & Hurghada Escape" },
  { "Product ID": "767742", "Title": "Luxor: Caravanserai private Day Tour" },
  { "Product ID": "767751", "Title": "Cairo: Eat with Egyptian families at a Local Restaurant" },
  { "Product ID": "623948", "Title": "Trip from Cairo to Luxor by Sleeper Train with Shared group" },
  { "Product ID": "447572", "Title": "Safaga Port: Private Sightseeing Day Trip to Luxor w/ Guide" },
  { "Product ID": "447572", "Title": "From Hurghada: 2-Day Private Tour of Luxor and Abu Simbel" },
  { "Product ID": "767757", "Title": "Cairo: Oriental Breakfast (Fatir)or Lunch in arabian village" },
  { "Product ID": "507460", "Title": "8-Day Private Egypt Tour: Cairo, Luxor & Nile Cruise Trip" },
  { "Product ID": "432718", "Title": "Private Half-Day Sightseeing Tour to El Gouna from Hurghada" },
  { "Product ID": "521786", "Title": "Cairo: Trip Pyramids, Sakkara, & Memphis Tour with Lunch" },
  { "Product ID": "773864", "Title": "Abu Simbel Temple QR Tickets" },
  { "Product ID": "767749", "Title": "Cairo: Siwa Oasis & Shali Fortress All inclusive 3 days Tour" },
  { "Product ID": "686021", "Title": "Cairo: Private Day Tour to Pharaonic Village" },
  { "Product ID": "558321", "Title": "Pyramids, Nile Cruise & Lake Nasser Cruise" },
  { "Product ID": "528973", "Title": "All-inclusive private Trip Pyramids Sphinx, Camel, VIP Lunch" },
  { "Product ID": "686040", "Title": "Cairo: Quad Bike Adventure at Giza Pyramids W/ Camel Ride" },
  { "Product ID": "622230", "Title": "Cairo: Private Day Tour to Luxor with Sleeper train" },
  { "Product ID": "463750", "Title": "Temple of Hatshepsut QR Ticket - Skip The Line" },
  { "Product ID": "513680", "Title": "Hurghada: Scenic Submarine Tour with Snorkeling and Transfer" },
  { "Product ID": "686033", "Title": "Sharm El-Sheikh: Ghibli Raceway Day Trip" },
  { "Product ID": "463535", "Title": "Skip-the-Line Valley of the Kings Tombs QR Ticket" },
  { "Product ID": "551826", "Title": "Hurghada: Luxury VIP La Rock Spa & Beauty Salon" },
  { "Product ID": "611893", "Title": "Hurghada: Orange Island Snorkeling, Diving, and Water Sports" },
  { "Product ID": "686029", "Title": "VIP Cairo Experience: Pyramids, ATV Adventure and Camel ride" },
  { "Product ID": "682017", "Title": "Cairo: Private Pyramids Tour with Photographer and Transfer" },
  { "Product ID": "649011", "Title": "Luxor: Luxor Museum Entry Tickets or Guided Tour" },
  { "Product ID": "654658", "Title": "One-Way Journey from Sharm El Sheikh to Hurghada" },
  { "Product ID": "272627", "Title": "Luxor: Half Day Motor Boat Ride with Banana Island Visit" },
  { "Product ID": "686026", "Title": "Cairo: Sound and light show with Dinner with Pyramids view" },
  { "Product ID": "592787", "Title": "Hurghada: Safari 5*1 Quad, Stargazing, Horse ride w/ Dinner" },
  { "Product ID": "767769", "Title": "Philae Temple Sound & Light Show in Aswan" },
  { "Product ID": "829925", "Title": "Hurghada to Cairo: Full-Day Tour one way Bus & Flight Return" },
  { "Product ID": "767770", "Title": "Cairo: Nile Pharaoh Dinner Cruise on the Nile with Show" },
  { "Product ID": "442999", "Title": "HRG:Private City Tour with Seafood at Barbouni Restaurant" },
  { "Product ID": "407577", "Title": "From Giza/Cairo: Pyramids, Sphinx, and NMEC Tour with Lunch" },
  { "Product ID": "767747", "Title": "Luxor: Qurna Village in luxor tour and transfer" },
  { "Product ID": "150248", "Title": "Cairo Day Trip: Museum, Pyramids, Sphinx & Authentic Lunch" },
  { "Product ID": "829930", "Title": "Makadi Airport transfer with option meet & assist" },
  { "Product ID": "437746", "Title": "Sharm el-Sheikh Museum Entry Ticket & Private Hotel Transfer" },
  { "Product ID": "686034", "Title": "Cairo: Pyramids Arabian Horse or Camel Ride with Bedouin Tea" },
  { "Product ID": "515721", "Title": "Sharm El Sheikh: Cleopatra Bath with Deluxe Spa Treatments" },
  { "Product ID": "611893", "Title": "Hurghada:4in1 Orange Island Diving,Snorkeling & water sports" },
  { "Product ID": "446329", "Title": "Cairo: Giza Pyramids Tour & Grand Egyptian Museum" },
  { "Product ID": "521725", "Title": "From Cairo & Giza: Pyramids, Camel Ride, & Museum Day Trip" },
  { "Product ID": "521725", "Title": "Giza: Half-Day Tour with Pyramids & Camel Experience" },
  { "Product ID": "767732", "Title": "Chatby Tombs Alexandria Day Tour from Cairo" },
  { "Product ID": "523251", "Title": "Cairo: Egypt & Lake Nasser Tour Package: 12 Days" },
  { "Product ID": "508923", "Title": "6-Day Private Egypt Tour: Cairo, Nile Cruise & Luxor by Air" },
  { "Product ID": "447813", "Title": "Cairo: Grand Egyptian Museum Guided Tour and Lunch" },
  { "Product ID": "246912", "Title": "Hurghada: Empire Submarine Boat Trip with Snorkel and Drinks" },
  { "Product ID": "683259", "Title": "Sharm El-Sheikh:King Tut Museum QR Ticket with Optional Tour" },
  { "Product ID": "829931", "Title": "Safaga Airport transfer with option meet & assist" },
  { "Product ID": "149345", "Title": "From Cairo: El-Tahrir Museum & Pyramids with lunch" },
  { "Product ID": "383140", "Title": "Hurghada: Jeep & Camel Safari with Dinner & Desert Fire Show" },
  { "Product ID": "844940", "Title": "Sharm El Sheikh: Private City Tour W Water Sports Adventure" },
  { "Product ID": "686031", "Title": "Mummification Museum QR Ticket or Guided tour" },
  { "Product ID": "686028", "Title": "ATV Quad Bike Ride At GIZA Pyramids & BBQ Dinner." },
  { "Product ID": "844942", "Title": "Sharm El Sheikh: Swimming With Dolphin & Show" },
  { "Product ID": "523349", "Title": "Private Customizable Day Tour to Alexandria from Cairo" },
  { "Product ID": "281802", "Title": "Aswan: Private Nile Boat Cruise and Botanical Garden Visit" },
  { "Product ID": "522328", "Title": "Cairo: Giza Pyramids, sphinx and National Museum with Lunch" },
  { "Product ID": "654599", "Title": "From Hurghada: Historical Tour to Luxor with Hotel Transfer" },
  { "Product ID": "676958", "Title": "Prince Mohamed Ali Palace Manial QR Tickets" },
  { "Product ID": "686035", "Title": "Hurghada Orange Bay Island Cruise with Snorkeling and Lunch" },
  { "Product ID": "686035", "Title": "Hurghada: Orange Island Yacht Trip with Lunch & Water Sports" },
  { "Product ID": "686024", "Title": "Cairo: The Coptic Museum QR ticket - Skip The Line" },
  { "Product ID": "476224", "Title": "Hurghada: Jerusalem day tour from Hurghada by flight" },
  { "Product ID": "510878", "Title": "Sharm El-Sheikh Port to Ras Mohamed National Park by Car" },
  { "Product ID": "686027", "Title": "Cairo: Museum of Islamic Arts QR Tickets & Skip Line" },
  { "Product ID": "829929", "Title": "Hurghada: Private Airport Arrival/Departure One Way Transfer" },
  { "Product ID": "844927", "Title": "From Sharm El-Sheikh: Cairo Day Tour to Pyramids By Bus" },
  { "Product ID": "684180", "Title": "Hurghada: Diving & Snorkeling Cruise Tour w Lunch & Drinks" },
  { "Product ID": "611823", "Title": "Hurghada: Giftun Island with breakfast, lunch & Water Sports" },
  { "Product ID": "322233", "Title": "Sharm El Sheikh: Trip to Luxor & Tutankhamun Tomb by Plane" },
  { "Product ID": "325628", "Title": "From Sharm El-Sheikh: Colored Canyoun , Blue Hole & Dahab" },
  { "Product ID": "829932", "Title": "El Gouna Lagoon, Diving with Dolphin, Snorkeling & Lunch" },
  { "Product ID": "559540", "Title": "Sharm El-Sheikh: Cafe & restaurant - Farsha or New Panorama" },
  { "Product ID": "461744", "Title": "Cairo: Pyramids of Giza Plateau Entrance QR Ticket" },
  { "Product ID": "22629", "Title": "From Sharm El-Sheikh: Cairo's Pyramids: Full-Day Journey" },
  { "Product ID": "447577", "Title": "From Sokhna Port: Cairo & Pyramids New Passage Day-Tour" },
  { "Product ID": "829926", "Title": "Luxor Day Trip: Karnak & Valley of the Kings & Nile Boat" }
    // تم اختصار القائمة لتوفير المساحة
    // يمكنك إضافة المزيد من العناصر حسب الحاجة
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
    "529200": "Eden Island Xtreme, Parasail, Dive & Water Sports",
    "408766": "Egyptian Museum and National Museum Private Tour",
    "160502": "Egyptian Museum of Antiquities online QR Ticket",
    "521373": "Giza Pyramids & Sphinx Half-Day Guided Tour",
    "446295": "Grand Egyptian Museum QR Ticket",
    "515155": "National Museum of Egypt Skip-the-Line QR Ticket",
    "521722": "Nile Dinner Cruise with Belly Dancer Show and Music",
    "622230": "Private Day Tour to Luxor with Sleeper train",
    "461744": "Pyramids of Giza Plateau QR Ticket - Skip The Line",
    "768763": "Sound and Light Show at Giza Pyramids",
    "686026": "Sound and Light Show with Dinner with Pyramids view",
    "318107": "Luxor Valley of the Kings Full-Day Trip by Plane Cairo",
    "447583": "Pyramids and Egyptian Museum Full-Day Tour",
    "844927": "Cairo Day Tour to Pyramids By Bus",
    "325593": "The Lost City (Petra) Day Tour by Ferry",
    "442999": "Private City Tour with Seafood at Barbouni Restaurant 5*",
    "829925": "Full-Day Tour one way Bus & Flight Return",
    "305108": "2-Day Luxor Tour with Hotel, Balloon, & Nile Boat",
    "654616": "3 Hour Camel Riding with Bedouin vibe",
    "767767": "Abu Simbel Sound & Light Show - QR Ticket",
    "686036": "Hurghada: Neverland",
    "408737": "Hurghada: Neverland",
    "21224": "Cairo Pyramids day tour by plane Hurghada",
    "1015784": "Sharm El-Sheikh : Horse Riding on the Beach",
    "150248": "Museum, Pyramids, Sphinx & Authentic Lunch",
    "297555": "Cairo Pyramids day tour by plane Hurghada",
    "26770": "Cairo Pyramids day tour by plane Hurghada",
    "28456": "Cairo by Bus Hurghada",
    "305063": "Cairo by Bus Hurghada",
    "361285": "Sea and Mountains Quad or Buggy Family Tour",
    "654789": "Desert & Sea Horse Riding",
    "686022": "Orange Island, Grand Safari, Dolphin House Package",
    "443016": "Desert & Sea Horse Riding",
    "22274": "Hurghada Desert Quad Bike Safari",
    "575994": "ATV Dunes & Waves with Lunch",
    "96546": "ATV Quad Safari, Camel Ride & Bedouin Village Tour",
    "48112": "Morning or Sunset Sights Guided Tour with Shopping",
    "28459": "Morning or Sunset Sights Guided Tour with Shopping",
    "521725": "Giza: Half-Day Tour with Pyramids & Camel Experience",
    "551826": "Luxor by Bus Hurghada",
    "829926": "Luxor by Bus Hurghada",
    "654599": "Luxor by Bus Hurghada",
    "829928": "Luxor by Bus Hurghada",
    "829926": "Luxor by Bus Hurghada",
    "22357": "Luxor by Bus Hurghada",
    "322233": "Luxor Valley of the Kings Full-Day Trip by Plane Sharm",
    "432704": "Stargazing with Candlelight Dinner",
    "513680": "Semi-Submarine Cruise with Snorkeling",
    "246912": "Semi-Submarine Cruise with Snorkeling",
    "684322": "Semi-Submarine Cruise with Snorkeling",
    "444195": "Diving & Snorkeling Cruise Tour",
    "684180": "Diving & Snorkeling Cruise Tour",
    "612422": "1-Hour Dolphin Show at Dolphin World",
    "829932": "Dolphin Watching & Snorkeling",
    "830640": "Dolphin Watching & Snorkeling",
    "485051": "Dolphin Watching & Snorkeling",
    "96537": "Dolphin Watching & Snorkeling",
    "484786": "Orange Bay Day Trip",
    "611893": "Orange Bay Day Trip",
    "686030": "Orange Bay Day Trip",
    "463817": "Orange Bay Day Trip",
    "611893": "Orange Bay Day Trip",
    "686035": "Orange Bay Day Trip",
    "611823": "Orange Bay Day Trip",
    "686037": "Orange Bay Day Trip",
    "829929": "Private Airport Arrival/Departure One Way Transfer",
    "596660": "Jeep Adventure to Blue Hole, Canyon & Dahab",
	  "437576": "Ultimate ATV Quad, Stargazing & BBQ Dinne",
    "844942": "Sharm El Sheikh: Swimming With Dolphin & Show",
	  "648980": "Sharm El-Sheikh: Stargazing",
	  "437716": "Sharm El-Sheikh: Stargazing",
	  "22629": "Sharm El-Sheikh - Cairo Flight",
	  "502836": "Sharm El-Sheikh - Cairo Flight",
	  "447809": "Sharm El-Sheikh - Cairo Flight",
	  "208317": "Sharm El-Sheikh: Ras Mohammed National Park",
	  "407583": "Sharm El-Sheikh: Ras Mohammed National Park",
	  "503557": "Sharm El-Sheikh: Ras Mohammed National Park",
	  "654715": "Sharm El-Sheikh: Ras Mohammed National Park",
	  "437602": "Sharm ElSheikh: Desert Safari 3 Hours Trip",
	  "596633": "Sharm ElSheikh: Desert Safari 3 Hours Trip",
    "515712": "Sharm ElSheikh: Desert Safari 3 Hours Trip",
	  "844932": "Sharm El Sheikh: City & Shopping Tour",
    "325628": "Jeep Adventure to Blue Hole, Canyon & Dahab",
    "844926": "Mount Sinai & St. Catherine Monastery Tour",
	  "844930": "Sharm El Sheikh: City & Shopping Tour",
    "559540": "Cafe & restaurant - Farsha or New Panorama",
    "872063": "Moses Mountain & Saint Catherine from Dahab",
    // تم اختصار القائمة لتوفير المساحة
    // يمكنك إضافة المزيد من العناصر حسب الحاجة
    '14976P1': 'Cairo Pyramids day tour by plane Sharm El-Sheikh',
    '14976P2': 'Cairo Pyramids day tour by plane Hurghada',
    '14976P3': 'Luxor by Bus Hurghada',
    '14976P7': 'Cairo by Bus Hurghada',
    '14976P9': 'Hurghada Desert Quad Bike Safari',
    '14976P17': 'Hurghada: Eden Island Serena VIP Boat Snorkeling Trip',
    '14976P21': 'Hurghada: Private Sightseeing Tour in El Gouna with Transfer',
    '14976P22': 'Hurghada: Red Sea Coast Horseback Riding Tour',
    '14976P24': 'Ultimate ATV Quad, Stargazing & BBQ Dinner',
    '14976P43': 'Sharm El Sheikh: Desert Safari with Quad Biking & Stargazing',
    '14976P45': 'Cafe & Restaurant Included Shisha & Drink',
    '14976P51': 'Diving Day Trip by Boat at Ras Mohamed & White Island',
    '14976P53': 'Quad Tour Along the Sea and Mountains in Hurghada',
    '14976P54': 'Ghibli Raceway Day Trip',
    '14976P57': 'Jeep Adventure to Blue Hole, Canyon & Dahab',
    '14976P61': 'Jeep Adventure to Blue Hole, Canyon & Dahab',
    '14976P73': 'Evening Dinner Nile Cruise in Cairo with Private Transportation',
    '14976P74': 'Desert Buggy Safari Adventure',
    '14976P79': 'Orange Bay Day Trip',
    '14976P109': 'Hurghada: Glass Boat and Parasailing Trip with Snorkeling',
    '14976P83': 'Hurghada Desert Sunset & Stargazing Tour with Dinner by Jeep',
    '14976P86': 'Makadi Water World with Lunch',
    '14976P88': 'Egyptian Museum of Antiquities Online QR Ticket',
    '14976P49': 'Sharm El-Sheikh: Stargazing',
    '14976P104': 'Hurghada Morning or Sunset Sights Guided Tour with Shopping'
  };
}

function loadDestinationMap() {
  return {
	"407583": "Sharm El-Sheikh",
  "325628": "Sharm El-Sheikh",
  "985803": "Sharm El-Sheikh",
  "437716": "Sharm El-Sheikh",
  "529200": "Hurghada",
  "611823": "Hurghada",
  "844927": "Sharm El-Sheikh",
  "529200": "Hurghada",
  "686037": "Hurghada",
  "872063": "Sharm El-Sheikh",
  "322233": "Sharm El-Sheikh",
  "22629": "Sharm El-Sheikh",
	"596660": "Sharm El-Sheikh",
	"437576": "Sharm El-Sheikh",
	"22357": "Hurghada",
	"596633": "Sharm El-Sheikh",
	"446295": "Cairo",
  "461744": "Cairo",
	"432704": "Hurghada",
  "686022": "Hurghada",
	"160502": "Cairo",
	"484786": "Hurghada",
	"677972": "Sharm El-Sheikh",
	"443016": "Hurghada",
	"305063": "Hurghada",
	"96537": "Hurghada",
	"48112": "Hurghada",
	"844930": "Sharm El-Sheikh",
	"21224": "Hurghada",
	"844926": "Sharm El-Sheikh",
	"830640": "Hurghada",
	"28456": "Hurghada",
	"22274": "Hurghada",
	"648980": "Sharm El-Sheikh",
	"503557": "Sharm El-Sheikh",
	"648929": "Hurghada",
	"297555": "Hurghada",
	"28459": "Hurghada",
	"361285": "Hurghada",
	"768763": "Cairo",
	"654789": "Hurghada",
	"208317": "Sharm El-Sheikh",
	"648919": "Hurghada",
	"690891": "Cairo",
	"515712": "Sharm El-Sheikh",
	"515155": "Cairo",
	"305108": "Hurghada",
	"503557": "Sharm El-Sheikh",
	"502836": "Sharm El-Sheikh",
	"22269": "Hurghada",
	"767761": "Luxor",
	"447583": "Cairo",
	"318107": "Cairo",
	"690891": "Cairo",
	"648929": "Hurghada",
	"325593": "Sharm El-Sheikh",
	"278712": "Cairo",
	"437602": "Sharm El-Sheikh",
  "559540": "Sharm El-Sheikh",
	"485051": "Hurghada",
	"768763": "Cairo",
	"648919": "Hurghada",
	"503045": "Sharm El-Sheikh",
  "1015784": "Sharm El-Sheikh",
	"432713": "Hurghada",
	"484822": "Hurghada",
	"829928": "Hurghada",
	"463817": "Hurghada",
	"408737": "Hurghada",
	"318107": "Cairo",
	"188934": "Marsa Alam",
	"614551": "Marsa Alam",
	"346421": "Luxor",
	"575994": "Sharm El-Sheikh",
	"521373": "Cairo",
	"444195": "Hurghada",
	"686042": "Marsa Alam",
	"305108": "Hurghada",
	"325593": "Sharm El-Sheikh",
	"484807": "Marsa Alam",
	"767764": "Hurghada",
	"767767": "Cairo",
	"502836": "Sharm El-Sheikh",
	"829926": "Hurghada",
	"407665": "Hurghada",
	"447583": "Port Said",
	"598778": "Hurghada",
	"684322": "Hurghada",
	"188418": "Marsa Alam",
	"26770": "Hurghada",
	"408766": "Cairo",
	"291325": "Marsa Alam",
	"592824": "Cairo",
	"447809": "Sharm El-Sheikh",
	"506697": "Cairo",
	"686036": "Hurghada",
	"446349": "Cairo",
	"654616": "Hurghada",
	"654715": "Sharm El-Sheikh",
	"844932": "Sharm El-Sheikh",
	"684287": "Hurghada",
	"521722": "Cairo",
	"449263": "Cairo",
	"444061": "Marsa Alam",
	"522810": "Cairo",
	"767742": "Luxor",
	"767751": "Cairo",
	"623948": "Cairo",
	"447572": "Hurghada",
	"767757": "Cairo",
	"507460": "Cairo",
	"432718": "Hurghada",
	"521786": "Cairo",
	"773864": "Cairo",
	"767749": "Cairo",
	"686021": "Cairo",
	"558321": "Cairo",
	"528973": "Cairo",
	"686040": "Cairo",
	"622230": "Cairo",
	"463750": "Luxor",
	"513680": "Hurghada",
	"686033": "Sharm El-Sheikh",
	"463535": "Luxor",
	"551826": "Hurghada",
	"611893": "Hurghada",
	"686029": "Cairo",
	"682017": "Cairo",
	"684180": "Hurghada",
	"649011": "Luxor",
	"654658": "Sharm El-Sheikh",
	"272627": "Luxor",
	"686026": "Cairo",
	"592787": "Hurghada",
	"767769": "Aswan",
	"829925": "Hurghada",
	"767770": "Cairo",
	"442999": "Hurghada",
	"407577": "Cairo",
	"767747": "Luxor",
	"150248": "Cairo",
	"829930": "Hurghada",
	"437746": "Sharm El-Sheikh",
	"686034": "Cairo",
	"515721": "Sharm El-Sheikh",
	"446329": "Cairo",
	"521725": "Cairo",
	"767732": "Alexandria",
	"523251": "Cairo",
	"508923": "Cairo",
	"447813": "Cairo",
	"246912": "Hurghada",
	"683259": "Sharm El-Sheikh",
	"829931": "Hurghada",
	"149345": "Cairo",
	"383140": "Hurghada",
	"844940": "Sharm El-Sheikh",
	"686031": "Cairo",
	"686028": "Cairo",
	"844942": "Sharm El-Sheikh",
	"523349": "Cairo",
	"281802": "Aswan",
	"522328": "Cairo",
	"654599": "Hurghada",
	"676958": "Cairo",
	"686035": "Hurghada",
	"686024": "Cairo",
	"476224": "Hurghada",
	"510878": "Sharm El-Sheikh",
	"686027": "Cairo",
	"447577": "Sokhna",
  "96546" : "Hurghada",
	"829932": "Hurghada",
    // تم اختصار القائمة لتوفير المساحة
    // يمكنك إضافة المزيد من العناصر حسب الحاجة
    '14976P1': 'Cairo',
    '14976P2': 'Hurghada',
    '14976P3': 'Hurghada',
    '14976P7': 'Hurghada',
    '14976P9': 'Hurghada',
    '14976P17': 'Hurghada',
    '14976P21': 'Hurghada',
    '14976P22': 'Hurghada',
    '14976P24': 'Sharm El-Sheikh',
    '14976P43': 'Sharm El-Sheikh',
    '14976P45': 'Sharm El-Sheikh',
    '14976P51': 'Sharm El-Sheikh',
    '14976P53': 'Hurghada',
    '14976P54': 'Sharm El-Sheikh',
    '14976P57': 'Sharm El-Sheikh',
    '14976P61': 'Sharm El-Sheikh',
    '14976P73': 'Cairo',
    '14976P74': 'Sharm El-Sheikh',
    '14976P49': 'Sharm El-Sheikh',
    '14976P79': 'Hurghada',
    '14976P83': 'Hurghada',
    '14976P86': 'Hurghada',
    '14976P88': 'Cairo',
    '14976P109': 'Hurghada',
    '14976P104': 'Hurghada'
  };
}

// تحميل البيانات المرجعية
const productTitlesList = loadProductTitles();
const productCodeMap = loadProductCodes();
const destinationMap = loadDestinationMap();

// 4. الدوال الرئيسية للمعالجة - Main Processing Functions
// --------------------------------------------------------

/**
 * الدالة الرئيسية - معالجة الإيميلات وإرسالها إلى Airtable
 */
function sendEmailsToAirtable() {
  try {
    const label = GmailApp.getUserLabelByName(CONFIG.PROCESSING.LABEL);
    if (!label) {
      throw new Error(`التصنيف "${CONFIG.PROCESSING.LABEL}" غير موجود.`);
    }

    const threads = label.getThreads(0, CONFIG.PROCESSING.MAX_THREADS);
    Logger.log(`ℹ️ جاري معالجة ${threads.length} من المحادثات`);

    const results = processAllThreads(threads);
    generateProcessingReport(results);
    
  } catch (error) {
    Logger.log(`❌ خطأ في النظام: ${error.message}`);
    sendAlertEmail('خطأ في النظام', error.message);
  }
}

/**
 * معالجة جميع المحادثات
 * @param {GmailThread[]} threads مصفوفة المحادثات
 * @return {Object} نتائج المعالجة
 */
function processAllThreads(threads) {
  const results = {
    processed: 0,
    errors: 0,
    errorMessages: []
  };

  for (const thread of threads) {
    try {
      processThread(thread);
      results.processed++;
    } catch (err) {
      results.errors++;
      results.errorMessages.push({
        subject: thread.getFirstMessageSubject(),
        error: err.message
      });
      Logger.log(`❌ خطأ في معالجة المحادثة: ${err.message}`);
    }
  }
  
  return results;
}

/**
 * معالجة محادثة واحدة
 * @param {GmailThread} thread المحادثة
 */
function processThread(thread) {
  const messages = thread.getMessages().sort((a, b) => a.getDate() - b.getDate());
  const startIndex = findStartIndex(messages);

  for (let j = startIndex; j < messages.length; j++) {
    const message = messages[j];
    
    if (message.isStarred()) {
      Logger.log("⭐ تم تجاهل الرسالة المميزة بنجمة");
      continue;
    }

    processMessage(message);
  }
}

/**
 * إيجاد نقطة البداية للمعالجة - البحث عن آخر نجمة زمنياً
 * @param {GmailMessage[]} messages الرسائل
 * @return {number} الفهرس
 */
function findStartIndex(messages) {
  // البحث عن آخر رسالة تم وضع نجمة عليها
  let lastStarIndex = -1;
  for (let k = 0; k < messages.length; k++) {
    if (messages[k].isStarred()) {
      lastStarIndex = k;
    }
  }
  
  // البدء من الرسالة التالية لآخر نجمة
  return lastStarIndex + 1;
}

/**
 * معالجة رسالة واحدة
 * @param {GmailMessage} message الرسالة
 */
function processMessage(message) {
  const subject = message.getSubject() || "";
  const body = [subject, (message.getPlainBody() || message.getBody())].join("\n");
  let bookingData = extractBookingData(body);

  if (!bookingData.reference_number) {
    Logger.log("⚠️ تم تجاهل الإيميل لعدم وجود رقم حجز");
    return;
  }

  // استكمال البيانات الناقصة
  bookingData = enhanceBookingData(bookingData, body);
  
  // تنقيح البيانات
  bookingData = sanitizeAirtableData(bookingData);
  
  // إرسال إلى Airtable
  sendDataToAirtable(bookingData);
  
  // وضع علامة نجمة
  message.star();
  Logger.log(`✅ تمت معالجة الحجز: ${bookingData.reference_number}`);
}

// 5. دوال استخراج البيانات - Data Extraction Functions
// --------------------------------------------------------

/**
 * استخراج بيانات الحجز من نص الإيميل
 * @param {string} emailBody محتوى الإيميل
 * @return {Object} بيانات الحجز
 */
function extractBookingData(emailBody) {
  // محاولة أولى: استخراج شامل بالذكاء الاصطناعي
  try {
    const aiData = extractBookingDataWithAI(emailBody);
    if (aiData && aiData.reference_number) {
      Logger.log(`🤖 تم استخراج البيانات بواسطة AI: ${aiData.agency || 'Unknown'} - الحالة: ${aiData.cancellation_status || 'Active'}`);
      return aiData;
    } else {
      Logger.log("ℹ️ AI لم يُرجع رقم حجز — سنستخدم القواعد التقليدية");
    }
  } catch (err) {
    Logger.log(`⚠️ فشل استخراج AI: ${err.message} — سنستخدم القواعد التقليدية`);
  }

  // احتياطي: قواعد الاستخراج الحالية
  if (isGetYourGuideEmail(emailBody)) {
    return extractGetYourGuideData(emailBody);
  } else if (isViatorEmail(emailBody)) {
    return extractViatorData(emailBody);
  } else {
    Logger.log("⚠️ نوع إيميل غير معروف");
    return {};
  }
}

/**
 * ✅ استخراج جميع بيانات الحجز باستخدام الذكاء الاصطناعي
 * يحدّد النوع والحالة (Active/Changed/Canceled) ويستخرج الحقول المطلوبة
 */
function extractBookingDataWithAI(emailBody) {
  Logger.log('🤖 بدء استخراج البيانات بالذكاء الاصطناعي...');
  const emailType = determineEmailType(emailBody);
  Logger.log(`📧 نوع الإيميل المبدئي: ${emailType}`);

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
  if (responseCode !== 200) {
    Logger.log(`⚠️ فشل طلب AI: ${responseCode}`);
    return {};
  }

  const json = JSON.parse(res.getContentText());
  const reply = json.choices?.[0]?.message?.content;
  if (!reply) {
    Logger.log("⚠️ استجابة AI فارغة");
    return {};
  }

  const jsonMatch = reply.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    Logger.log("⚠️ لم يتم العثور على JSON في استجابة AI");
    return {};
  }

  let extractedData = {};
  try {
    extractedData = JSON.parse(jsonMatch[0]);
  } catch (parseError) {
    Logger.log(`⚠️ خطأ في تحليل JSON من AI: ${parseError.message}`);
    return {};
  }

  const sanitized = sanitizeAIResponse(extractedData, emailType);
  return sanitized;
}

/**
 * ✅ إنشاء prompt شامل للاستخراج
 */
function createComprehensiveExtractionPrompt(emailBody, emailType) {
  const fieldsList = [
    'agency', 'cancellation_status', 'reference_number', 'product_id', 'main_Customer', 'email', 'phone',
    'traveler_name', 'special_request', 'tour_name', 'real_product_name', 'tour_option', 'destination', 'date_trip',
    'Pickup location', 'Tour_language', 'Adult', 'Student', 'Child', 'Infant', 'youth', 'add_ons', 'customer_country',
    'Google Map', 'Total price EUR', 'Total price USD', 'net_rate'
  ];

  const instructions = `You are an assistant that extracts travel booking data from emails.\n\n` +
    `Classify cancellation_status strictly as one of: Active, Changed, Canceled.\n` +
    `Detect agency among: GetYourGuide, Viator, Tiqets, Headout, Unknown. Use the provided type hint but override it if the content indicates otherwise.\n` +
    `Return ONLY JSON with these fields: ${fieldsList.join(', ')}.\n` +
    `Rules:\n` +
    `- Prices: numbers only (e.g., 250.50).\n` +
    `- Dates: use format YYYY-MM-DD HH:MM when possible.\n` +
    `- Counts: Adult/Student/Child/Infant/youth are integers (default 0).\n` +
    `- If a field does not exist, omit it.\n` +
    `- Reference number: return exact booking/reference code as appears (e.g., GYGN6FKNVRMV, BR-ABC123).`;

  const content = `Type hint: ${emailType}\n\nEmail content:\n"""${emailBody.substring(0, 15000)}"""`;
  return `${instructions}\n\n${content}`;
}

/**
 * ✅ تنقيح استجابة AI وضبط القيم لأنماط النظام
 */
function sanitizeAIResponse(aiData, emailType) {
  const data = initializeBookingData(aiData.agency || emailType || 'Unknown');

  const copyIf = (k) => { if (aiData[k] !== undefined && aiData[k] !== null && aiData[k] !== '') data[k] = aiData[k]; };
  [
    'product_id','reference_number','main_Customer','email','phone','traveler_name','special_request','tour_name',
    'real_product_name','tour_option','destination','date_trip','Pickup location','Tour_language','add_ons',
    'customer_country','Google Map','net_rate'
  ].forEach(copyIf);

  const toInt = (v) => { const n = parseInt(String(v).replace(/[^0-9-]/g, '')); return isNaN(n) ? 0 : n; };
  const toFloat = (v) => { const n = parseFloat(String(v).replace(/[^0-9.,-]/g, '').replace(',', '.')); return isNaN(n) ? null : n; };

  data.Adult = toInt(aiData.Adult);
  data.Student = toInt(aiData.Student);
  data.Child = toInt(aiData.Child);
  data.Infant = toInt(aiData.Infant);
  data.youth = toInt(aiData.youth);

  const eur = toFloat(aiData["Total price EUR"]);
  const usd = toFloat(aiData["Total price USD"]);
  if (eur !== null) data["Total price EUR"] = eur;
  if (usd !== null) data["Total price USD"] = usd;

  // ضبط الحالة وفق الثوابت المطلوبة
  let status = (aiData.cancellation_status || '').toString().trim().toLowerCase();
  if (/cancel/i.test(status)) status = 'Canceled';
  else if (/chang|amend|update/i.test(status)) status = 'Changed';
  else status = 'Active';
  data.cancellation_status = status;

  // في حال عدم وجود مرجع، حاول التقاطه من النص مباشرة كاحتياط
  if (!data.reference_number) {
    const refMatch = (aiData.raw_text || '')
      .match(/(GYG[A-Z0-9]{6,}|BR-[A-Z0-9\-]+|BOOKING[\s:-]?(\d{6,}))/i);
    if (refMatch) data.reference_number = refMatch[1] || refMatch[0];
  }

  return data;
}

/**
 * ✅ تحديد نوع الإيميل بالقرائن (مساعدة للـ Prompt)
 */
function determineEmailType(emailBody) {
  const indicators = {
    'GetYourGuide': [
      'getyourguide.com', 'GetYourGuide Team', 'booking detail change', 'your booking has been updated',
      'the date of your activity has been changed'
    ],
    'Viator': [
      'viator.com', 'Viator Booking Confirmation', 'Booking Reference', 'Amended', 'Cancellation'
    ],
    'Tiqets': [
      'Tiqets.com', 'tiqets.com', 'Booking notification from Tiqets', 'order number:', 'Tiqets for venues'
    ],
    'Headout': [
      'headout.com', 'Greetings from Headout', 'Team Headout', 'Headout reference number', 'reservation has been confirmed'
    ]
  };

  const text = (emailBody || '').toLowerCase();
  for (const [type, keywords] of Object.entries(indicators)) {
    if (keywords.some(keyword => text.includes(keyword.toLowerCase()))) {
      return type;
    }
  }
  return 'Unknown';
}

/**
 * تحسين بيانات الحجز باستخدام Deepsek
 * @param {Object} bookingData البيانات الأولية
 * @param {string} emailBody محتوى الإيميل
 * @return {Object} البيانات المحسنة
 */
function enhanceBookingData(bookingData, emailBody) {
  let missingFields = identifyMissingFields(bookingData);
  
  // إذا كان لدينا USD أو Net Rate، نزيل EUR من الحقول المفقودة
  if ((bookingData["Total price USD"] || bookingData.net_rate) && 
      missingFields.includes("Total price EUR")) {
    missingFields = missingFields.filter(field => field !== "Total price EUR");
    Logger.log("ℹ️ تم تجاهل استخراج EUR لأن USD موجود");
  }
  
  if (missingFields.length === 0) {
    return bookingData;
  }
  
  // معالجة الحقول الناقصة على دفعات
  for (let i = 0; i < missingFields.length; i += 2) {
    const fieldBatch = missingFields.slice(i, i + 2);
    Logger.log(`🔍 استخراج ${fieldBatch.length} حقول: ${fieldBatch.join(', ')}`);
    
    // نستدعي الدالة بالاسم الصحيح
    const additionalData = extractMissingFieldsViaDeepsek(
      bookingData, 
      emailBody, 
      fieldBatch
    );
    
    Object.assign(bookingData, additionalData);
  }
  
  return bookingData;
}

/**
 * إرسال البيانات إلى Airtable
 * @param {Object} bookingData بيانات الحجز
 */
function sendDataToAirtable(bookingData) {
  const fields = mapFieldsToAirtable(bookingData);
  
  // التحقق من وجود حقول للإرسال
  if (!fields || Object.keys(fields).length === 0) {
    Logger.log(`⚠️ لا توجد بيانات صالحة للإرسال للحجز: ${bookingData.reference_number}`);
    return;
  }
  
  const payload = { fields: fields };
  
  // تسجيل البيانات للتدقيق
  logDataForAudit(bookingData.reference_number, payload.fields);
  
  sendToAirtable(bookingData.reference_number, payload);
}

// 6. دوال التحقق من نوع الإيميل - Email Type Detection
// --------------------------------------------------------

/**
 * فحص ما إذا كان البريد من GetYourGuide
 * @param {string} emailBody محتوى الإيميل
 * @return {boolean} النتيجة
 */
function isGetYourGuideEmail(emailBody) {
  const indicators = [
    "getyourguide.com",
    "the following booking has been canceled",
    "GetYourGuide Team",
    "booking detail change",
    "your booking has been updated",
    "the date of your activity has been changed"
  ];
  const text = (emailBody || "").toLowerCase();
  return indicators.some(indicator => text.includes(indicator.toLowerCase()));
}

/**
 * فحص ما إذا كان البريد من Viator
 * @param {string} emailBody محتوى الإيميل
 * @return {boolean} النتيجة
 */
function isViatorEmail(emailBody) {
  const indicators = [
    "viator.com",
    "Viator Booking Confirmation"
  ];
  const text = (emailBody || "").toLowerCase();
  return indicators.some(indicator => text.includes(indicator.toLowerCase()));
}

// 7. دوال استخراج بيانات GetYourGuide
// --------------------------------------------------------

/**
 * استخراج بيانات GetYourGuide
 * @param {string} emailBody محتوى الإيميل
 * @return {Object} البيانات المستخرجة
 */
function extractGetYourGuideData(emailBody) {
  const data = initializeBookingData("GetYourGuide");
  
  // تحديد حالة الحجز
  const status = determineGetYourGuideStatus(emailBody);
  data.cancellation_status = status;
  
  switch (status) {
    case "Canceled":
      extractGetYourGuideCanceledData(data, emailBody);
      break;
    case "Changed":
      extractGetYourGuideChangedData(data, emailBody);
      break;
    default:
      extractGetYourGuideActiveData(data, emailBody);
  }
  
  // استخراج السعر - GetYourGuide عادة يستخدم EUR
  const extractedPrice = extractPriceGetYourGuide(emailBody);
  if (extractedPrice !== null) {
    data["Total price EUR"] = extractedPrice;
  }
  
  // معالجة البيانات الإضافية
  processGetYourGuideExtras(data, emailBody);
  
  return data;
}

/**
 * تحديد حالة حجز GetYourGuide
 * @param {string} emailBody محتوى الإيميل
 * @return {string} الحالة
 */
function determineGetYourGuideStatus(emailBody) {
  if (emailBody.includes("booking has been canceled") || 
      emailBody.includes("Cancellation confirmed") ||
      emailBody.includes("Booking canceled")) {
    return "Canceled";
  }
  
  if (emailBody.match(/booking has changed/i) ||
      emailBody.match(/booking detail change/i) ||
      emailBody.match(/your booking has been updated/i)) {
    return "Changed";
  }
  
  return "Active";
}

/**
 * استخراج بيانات حجز GetYourGuide الملغي
 */
function extractGetYourGuideCanceledData(data, emailBody) {
  const extract = createExtractor(emailBody);
  
  data.reference_number = extract(/Reference Number:\s*([^\n]+)/i);
  data.main_Customer = extract(/Name:\s*([^\n]+)/i);
  data.date_trip = extract(/Date:\s*([^\n]+)/i);
  data.tour_option = extract(/Tour Option:\s*([^\n]+)/i);
  data.cancellation_date = extract(/Cancellation date:\s*([^\n]+)/i);
  data.real_product_name = extract(/Product Name:\s*([^\n]+)/i) || 
                           extract(/Tour Name:\s*([^\n]+)/i);
}

/**
 * استخراج بيانات حجز GetYourGuide المعدل
 */
function extractGetYourGuideChangedData(data, emailBody) {
  const extract = createExtractor(emailBody);
  
  data.reference_number = extract(/(GYG[A-Z0-9]{6,})/i);
  data.tour_option = extract(/Tour Option:\s*([^\n]+)/i);
  data.date_trip = extract(/Date:\s*([^\n]+)/i);
  data["Tour_language"] = extract(/Language:\s*([^\n]+)/i);
  data["Pickup location"] = extract(/Pickup location:\s*([^\n<]+)/i);
  data["Google Map"] = extract(/Open in Google Maps\s+<([^>]+)>/i);
  data.Adult = parseInt(extract(/Number of participants:\s*(\d+)/i)) || 0;
  data.real_product_name = extract(/Product Name:\s*([^\n]+)/i) || 
                           extract(/Tour Name:\s*([^\n]+)/i);
}

/**
 * استخراج بيانات حجز GetYourGuide النشط
 */
function extractGetYourGuideActiveData(data, emailBody) {
  const extract = createExtractor(emailBody);
  
  // البيانات الأساسية
  data.real_product_name = extract(/booked:\s+\*([^\*]+)\*/i) || 
                           extract(/Activity:\s+\*([^\*]+)\*/i) || 
                           extract(/Activity:\s+([^\n]+)/i);
  data.tour_name = data.real_product_name;
  data.tour_option = extract(/Option:\s+\*([^*]+)\*/i) || 
                     extract(/Option:\s+([^\n]+)/i);
  data.date_trip = extract(/Date:\s+\*([^*]+)\*/i) || 
                   extract(/Date:\s+([^\n]+)/i);
  data.reference_number = extract(/Reference number:\s+\*([^*]+)\*/i) || 
                          extract(/Reference number:\s+([^\n]+)/i) || 
                          extract(/(GYG[A-Z0-9]{6,})/i);
  
  // بيانات العميل
  data.main_Customer = extract(/Main customer:\s+([^\n]+)/i) || 
                       extract(/Customer name:\s+([^\n]+)/i);
  data.email = extract(/(customer-[^\s]+@reply\.getyourguide\.com)/i) || 
               extract(/Email:\s+([^\n]+)/i);
  data.phone = extract(/Phone:\s+(\+?\d+[0-9\s()-]*)/i);
  
  // تفاصيل الجولة
  data["Tour_language"] = extract(/Tour language:\s+\*([^*]+)\*/i) || 
                          extract(/Tour language:\s+([^\n]+)/i) || 
                          extract(/Language:\s+([^\n]+)/i);
  
  // موقع الالتقاط
  let pickupRaw = extract(/Pickup location:\s*(.+?)\s*(?:Open in Google Maps|View booking|Best regards)/is);
  if (pickupRaw) {
    data["Pickup location"] = pickupRaw
      .replace(/\n+/g, ',')
      .replace(/\s+/g, ' ')
      .replace(/\s*,\s*/g, ',')
      .trim();
  }
  
  data["Google Map"] = extract(/Open in Google Maps\s+<([^>]+)>/i);
  
  // أعداد المشاركين
  data.Adult = parseInt(extract(/(\d+)\s+x\*?\s*Adults?/i)) || 0;
  data.Student = parseInt(extract(/(\d+)\s+x\*?\s*Students?/i)) || 0;
  data.Child = parseInt(extract(/(\d+)\s+x\*?\s*Child(?:ren)?/i)) || 0;
  data.Infant = parseInt(extract(/(\d+)\s+x\*?\s*Infants?/i)) || 0;
  data.youth = parseInt(extract(/(\d+)\s+x\*?\s*Youth?/i)) || 0;
  
  // طلبات خاصة
  data.traveler_name = extract(/Notes:\s*(.+)/i) || 
                       extract(/Special Requests:\s*(.+)/i);
}

/**
 * معالجة البيانات الإضافية لـ GetYourGuide
 */
function processGetYourGuideExtras(data, emailBody) {
  // توحيد اسم الرحلة والوجهة
  standardizeTourInfo(data);
  
  // استخراج الإضافات
  extractGetYourGuideAddOns(data, emailBody);
  
  // تنسيق التاريخ
  formatGetYourGuideDate(data);
  
  // GetYourGuide يستخدم EUR عادة، لذا نترك USD كـ null إذا لم يكن موجود
  if (!data["Total price USD"]) {
    data["Total price USD"] = null;
  }
}

/**
 * توحيد معلومات الرحلة
 */
function standardizeTourInfo(data) {
  // البحث عن معرف المنتج
  const found = productTitlesList.find(p =>
    data.real_product_name && 
    data.real_product_name.toLowerCase().includes(p.Title.toLowerCase())
  );
  
  if (found) {
    data.product_id = found["Product ID"];
  }
  
  // توحيد اسم الرحلة
  if (data.product_id && productCodeMap[data.product_id]) {
    data.tour_name = productCodeMap[data.product_id];
  }
  
  // تحديد الوجهة
  if (data.product_id && destinationMap[data.product_id]) {
    data.destination = destinationMap[data.product_id];
  }
}

/**
 * استخراج الإضافات من GetYourGuide
 */
function extractGetYourGuideAddOns(data, emailBody) {
  const match = emailBody.match(/Number of participants:[\s\S]+?(?=Main customer:|Language:|Tour language:|$)/i);
  if (!match) return;

  const rawText = match[0]
    .replace(/Number of participants:/gi, '')
    .replace(/\*/g, '')
    .replace(/\n+/g, ',') // دمج الأسطر إلى فواصل
    .trim();

  const parts = rawText.split(',')
    .map(p => p.trim())
    .filter(p => p); // إزالة الفارغات

  const baseParticipantRegex = /\b(Adult|Child|Student|Infant|Youth)s?\b/i;
  const agePattern = /\(Age\s*\d+\s*-\s*\d+\)/i;

  const addons = parts.filter(line => {
    // إذا كانت تحتوي على فئة + (Age ...) فهي ليست إضافة
    if (baseParticipantRegex.test(line) && agePattern.test(line)) {
      return false; // استبعاد
    }
    return true; // إضافة
  });

  const cleanedAddons = addons.join(', ').replace(/^,|,$/g, '').trim();

  if (cleanedAddons) {
    data.add_ons = cleanedAddons;
  }
}


/**
 * تنسيق تاريخ GetYourGuide
 */
function formatGetYourGuideDate(data) {
  if (!data.date_trip) return;
  
  const pattern = /[A-Za-z]+ \d{1,2}, \d{4} at \d{1,2}:\d{2} (AM|PM)/i;
  if (!pattern.test(data.date_trip)) return;
  
  const match = data.date_trip.match(/([A-Za-z]+) (\d{1,2}), (\d{4}) at (\d{1,2}):(\d{2}) (AM|PM)/i);
  if (!match) return;
  
  const [, monthStr, day, year, hour, minute, ampm] = match;
  const months = {
    January: 1, February: 2, March: 3, April: 4, May: 5, June: 6,
    July: 7, August: 8, September: 9, October: 10, November: 11, December: 12
  };
  
  const month = months[monthStr];
  if (!month) return;
  
  const dayFormatted = String(parseInt(day, 10)).padStart(2, '0');
  let hourFormatted = parseInt(hour, 10);
  if (ampm.toUpperCase() === 'PM' && hourFormatted < 12) hourFormatted += 12;
  if (ampm.toUpperCase() === 'AM' && hourFormatted === 12) hourFormatted = 0;
  const hourStr = String(hourFormatted).padStart(2, '0');
  const minuteStr = minute.padStart(2, '0');
  
  data.date_trip = `${year}-${String(month).padStart(2, '0')}-${dayFormatted} ${hourStr}:${minuteStr}`;
}

// 8. دوال استخراج بيانات Viator
// --------------------------------------------------------

/**
 * استخراج بيانات Viator
 * @param {string} emailBody محتوى الإيميل
 * @return {Object} البيانات المستخرجة
 */
function extractViatorData(emailBody) {
  const data = initializeBookingData("Viator");
  const extract = createExtractor(emailBody);
  
  // تحديد حالة الحجز
  const isAmended = emailBody.includes("Amended");
  const isCanceled = emailBody.includes("Cancellation") || emailBody.includes("Canceled");
  
  data.cancellation_status = isAmended ? "Changed" : (isCanceled ? "Canceled" : "Active");
  
  // استخراج البيانات الأساسية
  extractViatorBasicData(data, extract);
  
  // استخراج بيانات المشاركين
  extractViatorParticipantData(data, extract);
  
  // استخراج السعر - Viator عادة يستخدم USD فقط
  const extractedPrice = extractPriceViator(emailBody);
  if (extractedPrice !== null) {
    data["Total price USD"] = extractedPrice;
  }
  
  // معالجة بيانات إضافية
  processViatorExtras(data, extract);
  
  return data;
}

/**
 * استخراج البيانات الأساسية من Viator
 */
function extractViatorBasicData(data, extract) {
  // رقم الحجز
  let reference_number = extract(/Booking Reference:\s*(?:#?\s*)?(?:BR-)?([A-Z0-9\-]+)/i);
  if (reference_number && !reference_number.startsWith("BR-")) {
    reference_number = "BR-" + reference_number;
  }
  data.reference_number = reference_number;
  
  // اسم الجولة
  let tour_name = extract(/Amended\s*\n([^\n]+)/i) ||
                  extract(/Tour Name:\s*([^\n]+)/i) ||
                  extract(/Product Name:\s*([^\n]+)/i);
  data.real_product_name = tour_name || "";
  
  // معلومات إضافية
  data.product_id = extract(/Product Code:\s*([^\n]+)/i);
  data.tour_option = extract(/Tour Grade:\s*([^\n]+)/i);
  data.date_trip = extract(/Travel Date:\s*([^\n]+)/i);
  let netRateRaw = extract(/Net Rate:\s*([^\n]+)/i);
  if (netRateRaw) {
    // استخراج علامة العملة والرقم فقط
    const netRateMatch = netRateRaw.match(/(\$|€|£)\s*(\d+(?:[.,]\d+)?)/);
    if (netRateMatch) {
      data.net_rate = netRateMatch[1] + netRateMatch[2];
      Logger.log(`✅ تم استخراج Net Rate: ${data.net_rate}`);
    } else {
      // إذا لم نجد علامة عملة، نحاول استخراج الرقم فقط
      const numberMatch = netRateRaw.match(/(\d+(?:[.,]\d+)?)/);
      if (numberMatch) {
        data.net_rate = numberMatch[1];
        Logger.log(`✅ تم استخراج Net Rate (رقم فقط): ${data.net_rate}`);
      }
    }
  }

  data.cancellation_date = extract(/Cancellation Date:\s*([^\n]+)/i);
  data["Google Map"] = extract(/Google Map:\s*<([^>]+)>/i);
}

/**
 * استخراج بيانات المشاركين من Viator
 */
function extractViatorParticipantData(data, extract) {
  // بيانات العميل
  data.main_Customer = extract(/Lead Traveler Name:\s*([^\n]+)/i);
  data.email = extract(/Customer Email:\s*([^\n]+)/i);
  data.phone = extract(/Phone:\s*(?:\(Alternate Phone\))?[^+]*([\+0-9\s()-]+)/i);
  data.traveler_name = extract(/Traveler Names?:\s*([^\n]+)/i);
  
  // أعداد المشاركين
  data.Adult = parseInt(extract(/(\d+)\s*Adults?/i)) || 0;
  data.Student = parseInt(extract(/(\d+)\s*Students?/i)) || 0;
  data.Child = parseInt(extract(/(\d+)\s*Child?/i)) || 0;
  data.Infant = parseInt(extract(/(\d+)\s*Infants?/i)) || 0;
  data.youth = parseInt(extract(/(\d+)\s*Youth/i)) || 0;
  
  // معلومات إضافية
  const tourLanguage = extract(/Tour Language:\s*([^\n]+)/i);
  if (tourLanguage) {
    data["Tour_language"] = tourLanguage.split(" -")[0].trim();
  }
  data.add_ons = extract(/Tour Grade Description:\s*([^\n]+)/i);
}

/**
 * معالجة البيانات الإضافية لـ Viator
 */
function processViatorExtras(data, extract) {
  // موقع الالتقاط
  let pickupViator = extract(/Hotel Pickup:\s*([^\n]+)/i);
  if (pickupViator) {
    data["Pickup location"] = pickupViator
      .replace(/\n+/g, ',')
      .replace(/\s+/g, ' ')
      .replace(/\s*,\s*/g, ',')
      .trim();
  }
  
  // تنسيق التاريخ
  formatViatorDate(data);
  
  // توحيد اسم الرحلة والوجهة
  if (data.product_id && productCodeMap[data.product_id]) {
    data.tour_name = productCodeMap[data.product_id];
  } else {
    data.tour_name = data.real_product_name;
  }
  
  if (data.product_id && destinationMap[data.product_id]) {
    data.destination = destinationMap[data.product_id];
  }
  
  // معالجة السعر إذا كان موجود في net_rate
  if (!data["Total price USD"] && data.net_rate) {
    // استخراج الرقم من net_rate للاستخدام كسعر USD
    const netRateMatch = data.net_rate.match(/\$?\s*(\d+(?:[.,]\d+)?)/);
    if (netRateMatch) {
      data["Total price USD"] = parseFloat(netRateMatch[1].replace(',', '.'));
      Logger.log(`✅ استخدام Net Rate كسعر USD: ${data["Total price USD"]}`);
    }
  }
  
  // Viator يستخدم USD عادة، لذا نترك EUR كـ null إذا لم يكن موجود
  if (!data["Total price EUR"]) {
    data["Total price EUR"] = null;
  }
}

/**
 * تنسيق تاريخ Viator
 */
function formatViatorDate(data) {
  if (!data.date_trip) return;
  
  const cleanDate = data.date_trip.replace(/^[A-Za-z]+,\s*/, '').trim();
  const parsed = new Date(cleanDate);
  
  if (!isNaN(parsed)) {
    const yyyy = parsed.getFullYear();
    const mm = String(parsed.getMonth() + 1).padStart(2, '0');
    const dd = String(parsed.getDate()).padStart(2, '0');
    data.date_trip = `${yyyy}-${mm}-${dd} 00:00`;
  }
}

// 9. دوال استخراج الأسعار - Price Extraction Functions
// --------------------------------------------------------

/**
 * استخراج السعر من GetYourGuide
 * @param {string} emailBody محتوى الإيميل
 * @return {number|null} السعر المستخرج
 */
function extractPriceGetYourGuide(emailBody) {
  let price = null;
  
  const pricePatterns = [
    /Price:\s*[€€]\s*(\d+(?:[.,]\d+)?)/i,
    /Total:\s*[€€]\s*(\d+(?:[.,]\d+)?)/i,
    /Total price:\s*[€€]\s*(\d+(?:[.,]\d+)?)/i,
    /price[^€€]*[€€]\s*(\d+(?:[.,]\d+)?)/i,
    /EUR\s*(\d+(?:[.,]\d+)?)/i,
    /(\d+(?:[.,]\d+)?)\s*EUR/i,
    /[€€]\s*(\d+(?:[.,]\d+)?)/,
    /Total Amount:\s*(\d+(?:[.,]\d+)?)/i,
    /Grand Total:\s*[€€]?\s*(\d+(?:[.,]\d+)?)/i,
    /Amount:\s*[€€]?\s*(\d+(?:[.,]\d+)?)/i
  ];
  
  for (const pattern of pricePatterns) {
    const match = emailBody.match(pattern);
    if (match) {
      let priceStr = match[1].replace(',', '.');
      price = parseFloat(priceStr);
      Logger.log(`✅ تم العثور على السعر باليورو: €${price}`);
      break;
    }
  }
  
  if (!price) {
    Logger.log(`⚠️ لم يتم العثور على السعر باليورو في إيميل GetYourGuide`);
  }
  
  return price;
}

/**
 * استخراج السعر من Viator
 * @param {string} emailBody محتوى الإيميل
 * @return {number|null} السعر المستخرج
 */
function extractPriceViator(emailBody) {
  let price = null;
  
  const pricePatterns = [
    /Net Rate:\s*USD\s*\$?(\d+(?:[.,]\d+)?)/i,
    /Total:\s*USD\s*\$?(\d+(?:[.,]\d+)?)/i,
    /Total Price:\s*USD\s*\$?(\d+(?:[.,]\d+)?)/i,
    /USD\s*\$?\s*(\d+(?:[.,]\d+)?)/i,
    /\$\s*(\d+(?:[.,]\d+)?)\s*USD/i,
    /price[^$]*\$\s*(\d+(?:[.,]\d+)?)/i,
    /\$\s*(\d+(?:[.,]\d+)?)/,
    /Total Amount:\s*\$?\s*(\d+(?:[.,]\d+)?)/i,
    /Total Due:\s*\$?\s*(\d+(?:[.,]\d+)?)/i,
    /Grand Total:\s*\$?\s*(\d+(?:[.,]\d+)?)/i
  ];
  
  for (const pattern of pricePatterns) {
    const match = emailBody.match(pattern);
    if (match) {
      let priceStr = match[1].replace(',', '.');
      price = parseFloat(priceStr);
      Logger.log(`✅ تم العثور على السعر بالدولار: ${price}`);
      break;
    }
  }
  
  if (!price) {
    Logger.log(`⚠️ لم يتم العثور على السعر بالدولار في إيميل Viator`);
  }
  
  return price;
}

/**
 * استخراج السعر بشكل عام (احتياطي)
 * @param {string} emailBody محتوى الإيميل
 * @return {Object} الأسعار المستخرجة
 */
function extractPriceGeneral(emailBody) {
  const result = {
    EUR: null,
    USD: null
  };
  
  const patterns = {
    EUR: [
      /[€€]\s*(\d+(?:[.,]\d+)?)/,
      /(\d+(?:[.,]\d+)?)\s*EUR/i,
      /EUR\s*(\d+(?:[.,]\d+)?)/i,
      /price.*?[€€]\s*(\d+(?:[.,]\d+)?)/i,
      /total.*?[€€]\s*(\d+(?:[.,]\d+)?)/i,
      /amount.*?[€€]\s*(\d+(?:[.,]\d+)?)/i
    ],
    USD: [
      /\$\s*(\d+(?:[.,]\d+)?)/,
      /(\d+(?:[.,]\d+)?)\s*USD/i,
      /USD\s*\$?\s*(\d+(?:[.,]\d+)?)/i,
      /price.*?\$\s*(\d+(?:[.,]\d+)?)/i,
      /total.*?\$\s*(\d+(?:[.,]\d+)?)/i,
      /amount.*?\$\s*(\d+(?:[.,]\d+)?)/i
    ]
  };
  
  // استخراج EUR
  for (const pattern of patterns.EUR) {
    const match = emailBody.match(pattern);
    if (match && !result.EUR) {
      let priceStr = match[1].replace(',', '.');
      result.EUR = parseFloat(priceStr);
      Logger.log(`✅ تم العثور على سعر اليورو (عام): €${result.EUR}`);
      break;
    }
  }
  
  // استخراج USD
  for (const pattern of patterns.USD) {
    const match = emailBody.match(pattern);
    if (match && !result.USD) {
      let priceStr = match[1].replace(',', '.');
      result.USD = parseFloat(priceStr);
      Logger.log(`✅ تم العثور على سعر الدولار (عام): ${result.USD}`);
      break;
    }
  }
  
  return result;
}

// 10. دوال تنقيح ومعالجة البيانات - Data Sanitization Functions
// --------------------------------------------------------

/**
 * تنقيح البيانات للإرسال إلى Airtable
 * @param {Object} data البيانات الأصلية
 * @return {Object} البيانات المنقحة
 */
function sanitizeAirtableData(data) {
  const result = {...data};
  
  // معالجة الأسعار
  sanitizePrices(result);
  
  // معالجة التواريخ
  sanitizeDates(result);
  
  // معالجة الأرقام
  sanitizeNumbers(result);
  
  // تنظيف النصوص
  sanitizeTextFields(result);
  if (result.product_id !== undefined) {
  result.product_id = ensureProductIdIsString(result.product_id);
  }
  return result;
}

function ensureProductIdIsString(productId) {
  if (productId === null || productId === undefined || productId === "") {
    return "";
  }
  return String(productId).trim();
}

/**
 * تنقيح الأسعار
 */
function sanitizePrices(data) {
  const priceFields = ["Total price EUR", "Total price USD"];
  
  for (const field of priceFields) {
    if (data[field] === undefined || data[field] === null) continue;
    
    if (typeof data[field] === 'string') {
      const cleanPrice = data[field].replace(/[^\d.,]/g, '').replace(',', '.');
      data[field] = parseFloat(cleanPrice) || null;
    } else if (Array.isArray(data[field]) && data[field].length > 0) {
      const priceValue = data[field][0];
      if (typeof priceValue === 'string') {
        const cleanPrice = priceValue.replace(/[^\d.,]/g, '').replace(',', '.');
        data[field] = parseFloat(cleanPrice) || null;
      } else if (typeof priceValue === 'number') {
        data[field] = priceValue;
      } else {
        data[field] = null;
      }
    }
  }
}

/**
 * تنقيح التواريخ
 */
function sanitizeDates(data) {
  if (data.date_trip === undefined || data.date_trip === null) return;
  
  // إذا كان التاريخ مصفوفة، نأخذ العنصر الأول
  if (Array.isArray(data.date_trip)) {
    Logger.log(`⚠️ تم اكتشاف تاريخ كمصفوفة: ${JSON.stringify(data.date_trip)}`);
    data.date_trip = data.date_trip[0];
  }
  
  // تحويل التاريخ إلى صيغة Airtable
  if (typeof data.date_trip === 'string') {
    data.date_trip = formatDateForAirtable(data.date_trip);
  }
}

/**
 * تنسيق التاريخ لـ Airtable
 */
function formatDateForAirtable(dateStr) {
  let formattedDate = null;
  
  // نمط: Month DD, YYYY at HH:MM AM/PM
  const dateMatch = dateStr.match(/([A-Za-z]+) (\d{1,2}), (\d{4}) at (\d{1,2}):(\d{2}) (AM|PM)/i);
  if (dateMatch) {
    const [, monthStr, day, year, hour, minute, ampm] = dateMatch;
    const months = {
      January: 1, February: 2, March: 3, April: 4, May: 5, June: 6,
      July: 7, August: 8, September: 9, October: 10, November: 11, December: 12
    };
    const month = months[monthStr];
    if (month) {
      const dayFormatted = String(parseInt(day, 10)).padStart(2, '0');
      let hourFormatted = parseInt(hour, 10);
      if (ampm.toUpperCase() === 'PM' && hourFormatted < 12) hourFormatted += 12;
      if (ampm.toUpperCase() === 'AM' && hourFormatted === 12) hourFormatted = 0;
      const hourStr = String(hourFormatted).padStart(2, '0');
      const minuteStr = minute.padStart(2, '0');
      formattedDate = `${year}-${String(month).padStart(2, '0')}-${dayFormatted} ${hourStr}:${minuteStr}`;
    }
  }
  
  // نمط: YYYY-MM-DD HH:MM
  const simpleMatch = dateStr.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/);
  if (simpleMatch) {
    formattedDate = dateStr;
  }
  
  // محاولة التحويل باستخدام Date object
  if (!formattedDate) {
    try {
      const parsedDate = new Date(dateStr);
      if (!isNaN(parsedDate.getTime())) {
        const year = parsedDate.getFullYear();
        const month = String(parsedDate.getMonth() + 1).padStart(2, '0');
        const day = String(parsedDate.getDate()).padStart(2, '0');
        const hour = String(parsedDate.getHours()).padStart(2, '0');
        const minute = String(parsedDate.getMinutes()).padStart(2, '0');
        formattedDate = `${year}-${month}-${day} ${hour}:${minute}`;
      }
    } catch (e) {
      Logger.log(`⚠️ خطأ في تحويل التاريخ: ${e.message}`);
    }
  }
  
  return formattedDate || dateStr;
}

/**
 * تنقيح الأرقام
 */
function sanitizeNumbers(data) {
  for (const field of BOOKING_FIELDS.NUMERIC) {
    if (data[field] === undefined || data[field] === null) continue;
    
    if (typeof data[field] === 'string') {
      data[field] = parseInt(data[field], 10) || 0;
    } else if (Array.isArray(data[field])) {
      data[field] = parseInt(data[field][0], 10) || 0;
    }
  }
}

/**
 * تنقيح النصوص
 */
function sanitizeTextFields(data) {
  for (const field of BOOKING_FIELDS.TEXT) {
    if (data[field] === undefined || data[field] === null) continue;
    
    if (Array.isArray(data[field]) && data[field].length > 0) {
      data[field] = data[field][0];
    }
  }
}

// 11. دوال DEEPSEK - DEEPSEK Functions
// --------------------------------------------------------

/**
 * تحديد الحقول الناقصة
 * @param {Object} data بيانات الحجز
 * @return {Array} الحقول الناقصة
 */
function identifyMissingFields(data) {
  // الحقول الحرجة
  const missingCriticalFields = BOOKING_FIELDS.CRITICAL.filter(field => 
    !data[field] || data[field] === "" || 
    (typeof data[field] === 'number' && data[field] === 0)
  );
  
  if (missingCriticalFields.length > 0) {
    Logger.log(`⚠️ حقول أساسية مفقودة: ${missingCriticalFields.join(', ')}`);
    return missingCriticalFields;
  }
  
  // الحقول الثانوية
  const missingSecondaryFields = BOOKING_FIELDS.SECONDARY.filter(field => 
    !data[field] || data[field] === "" || 
    (typeof data[field] === 'number' && data[field] === 0)
  );
  
  if (missingSecondaryFields.length > 0) {
    const fieldsToExtract = missingSecondaryFields.slice(0, 2);
    Logger.log(`ℹ️ محاولة استخراج حقول ثانوية: ${fieldsToExtract.join(', ')}`);
    return fieldsToExtract;
  }
  
  return [];
}

/**
 * استخراج الحقول الناقصة باستخدام Deepsek
 * @param {Object} data البيانات الحالية
 * @param {string} emailBody محتوى الإيميل
 * @param {Array} missingFields الحقول المفقودة
 * @return {Object} البيانات المستخرجة
 */
function extractMissingFieldsViaDeepsek(data, emailBody, missingFields) {
  if (!missingFields || missingFields.length === 0) {
    return {};
  }

  // ملاحظة خاصة حول الأسعار
  let priceInstructions = "";
  if (missingFields.includes("Total price EUR") && (data["Total price USD"] || data.net_rate)) {
    priceInstructions = "\nNOTE: We already have USD price, so skip EUR price extraction.";
  }

  const existingDataContext = Object.entries(data)
    .filter(([key, value]) => value !== undefined && value !== null && value !== "")
    .map(([key, value]) => `${key}: ${value}`)
    .join("\n");

  const prompt = `
I need you to extract ONLY these specific fields from a travel booking email:
${missingFields.join(", ")}

IMPORTANT INSTRUCTIONS:
1. Return ONLY the fields I asked for
2. Return single values, NOT arrays
3. For prices, return numbers only (e.g., 250.50)
4. For dates, use the format: YYYY-MM-DD HH:MM
5. If a field is not found, don't include it
${priceInstructions}

This is the existing data I already extracted:
${existingDataContext}

Full email content:
"""${emailBody.substring(0, 15000)}"""

Return ONLY a JSON object with the requested fields.
`.trim();

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

  try {
    const res = UrlFetchApp.fetch(CONFIG.DEEPSEK.ENDPOINT, options);
    const responseCode = res.getResponseCode();
    
    if (responseCode !== 200) {
      Logger.log(`⚠️ فشل طلب Deepsek: ${responseCode}`);
      return {};
    }
    
    const json = JSON.parse(res.getContentText());
    const reply = json.choices?.[0]?.message?.content;

    if (!reply) {
      Logger.log("⚠️ استجابة Deepsek فارغة");
      return {};
    }

    const jsonMatch = reply.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      Logger.log("⚠️ لم يتم العثور على JSON في استجابة Deepsek");
      return {};
    }
    
    try {
      const extractedData = JSON.parse(jsonMatch[0]);
      
      // تنقيح البيانات المستخرجة
      const sanitizedData = {};
      for (const [key, value] of Object.entries(extractedData)) {
        if (Array.isArray(value) && value.length > 0) {
          Logger.log(`⚠️ تم اكتشاف مصفوفة للحقل ${key}`);
          sanitizedData[key] = value[0];
        } else {
          sanitizedData[key] = value;
        }
      }
      
      const extractedFields = Object.keys(sanitizedData);
      if (extractedFields.length > 0) {
        Logger.log(`✅ تم استخراج الحقول: ${extractedFields.join(', ')}`);
      }
      
      return sanitizedData;
    } catch (parseError) {
      Logger.log(`⚠️ خطأ في تحليل استجابة Deepsek: ${parseError.message}`);
      return {};
    }
  } catch (err) {
    Logger.log(`⚠️ فشل استدعاء Deepsek: ${err.message}`);
    return {};
  }
}

// 12. دوال Airtable - Airtable Functions
// --------------------------------------------------------

/**
 * تخطيط الحقول لـ Airtable
 * @param {Object} data بيانات الحجز
 * @return {Object} الحقول المخططة
 */
function mapFieldsToAirtable(data) {
  const allFields = {
    "Agency": data.agency,
    "Product ID": ensureProductIdIsString(data.product_id),
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

  // إزالة الحقول الفارغة
  const fields = {};
  for (const key in allFields) {
    if (
      allFields[key] !== undefined &&
      allFields[key] !== null &&
      allFields[key] !== "" &&
      !(typeof allFields[key] === "number" && allFields[key] === 0)
    ) {
      fields[key] = allFields[key];
    }
  }
  
  return fields;
}

/**
 * إرسال البيانات إلى Airtable
 * @param {string} ref رقم المرجع
 * @param {Object} payload البيانات
 */
function sendToAirtable(ref, payload) {
  const headers = {
    Authorization: `Bearer ${CONFIG.KEYS.AIRTABLE}`,
    'Content-Type': 'application/json'
  };

  try {
    const baseUrl = CONFIG.AIRTABLE.URL;
    Logger.log(`⚡ عنوان Airtable: ${baseUrl}`);
    
    // التحقق من صحة البيانات
    if (!payload || !payload.fields || Object.keys(payload.fields).length === 0) {
      Logger.log(`⚠️ لا توجد حقول للإرسال للحجز ${ref}`);
      Logger.log(`البيانات المستلمة: ${JSON.stringify(payload)}`);
      return;
    }
    
    // البحث عن سجل موجود
    const searchUrl = `${baseUrl}?filterByFormula=${encodeURIComponent(`SEARCH("${ref}", {Booking Nr.})`)}`;
    const response = UrlFetchApp.fetch(searchUrl, { 
      method: "get", 
      headers,
      muteHttpExceptions: true 
    });
    
    const data = JSON.parse(response.getContentText());

    if (data.records && data.records.length > 0) {
      // تحديث سجل موجود
      updateExistingRecord(data.records[0], payload, headers, baseUrl);
    } else {
      // إنشاء سجل جديد
      createNewRecord(payload, headers, baseUrl);
    }
    
    Logger.log(`✅ تم حفظ الحجز: ${ref}`);
  } catch (err) {
    Logger.log(`❌ خطأ في Airtable: ${err.message}`);
    throw new Error(`فشل الحفظ في Airtable: ${err.message}`);
  }
}

/**
 * تحديث سجل موجود في Airtable
 */
function updateExistingRecord(record, payload, headers, baseUrl) {
  const recordId = record.id;
  Logger.log(`📝 تحديث سجل موجود: ${recordId}`);
  
  // حماية الحقول الموجودة
  protectExistingFields(record, payload);
  
  const updateFields = Object.keys(payload.fields);
  Logger.log(`⚡ الحقول التي سيتم تحديثها: ${updateFields.join(', ')}`);
  
  const updateResponse = UrlFetchApp.fetch(`${baseUrl}/${recordId}`, {
    method: "patch",
    headers,
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  if (updateResponse.getResponseCode() >= 400) {
    throw new Error(`خطأ في API: ${updateResponse.getContentText()}`);
  }
}

/**
 * إنشاء سجل جديد في Airtable
 */
function createNewRecord(payload, headers, baseUrl) {
  Logger.log(`🆕 إنشاء سجل جديد`);
  Logger.log(`📤 البيانات المرسلة: ${JSON.stringify(payload)}`);
  
  const createResponse = UrlFetchApp.fetch(baseUrl, {
    method: "post",
    headers,
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  });
  
  const responseCode = createResponse.getResponseCode();
  const responseText = createResponse.getContentText();
  
  Logger.log(`📊 كود الاستجابة: ${responseCode}`);
  
  if (responseCode >= 400) {
    Logger.log(`❌ محتوى الخطأ: ${responseText}`);
    throw new Error(`خطأ في API: ${responseText}`);
  } else {
    Logger.log(`✅ تم إنشاء السجل بنجاح`);
  }
}

/**
 * حماية الحقول الموجودة من الكتابة مع حماية خاصة لحقل Booking Status
 */
function protectExistingFields(record, payload) {
  Logger.log(`🛡️ فحص الحقول المحمية...`);
  
  // حماية الحقول العادية
  for (const field of BOOKING_FIELDS.PROTECTED) {
    if (record.fields[field] !== undefined && 
        record.fields[field] !== null && 
        record.fields[field] !== "") {
      Logger.log(`  - ${field}: موجود (محمي) = "${record.fields[field]}"`);
      delete payload.fields[field];
    } else {
      Logger.log(`  - ${field}: غير موجود أو فارغ`);
    }
  }
  
  // حماية خاصة لحقل Booking Status
  if (record.fields["Booking Status"] === CONFIG.BOOKING_STATUS.CANCELED) {
    Logger.log(`  🚫 Booking Status: القيمة الحالية "Canceled" - محمي من التغيير`);
    delete payload.fields["Booking Status"];
  } else if (payload.fields["Booking Status"]) {
    Logger.log(`  ✅ Booking Status: مسموح بالتحديث من "${record.fields["Booking Status"] || 'فارغ'}" إلى "${payload.fields["Booking Status"]}"`);
  }
  
  // حماية الحقول الشرطية الأخرى
  for (const [field, protectedValues] of Object.entries(BOOKING_FIELDS.CONDITIONALLY_PROTECTED)) {
    if (field === "Booking Status") continue; // تمت معالجته بالأعلى
    
    const currentValue = record.fields[field];
    if (currentValue && protectedValues.includes(currentValue)) {
      Logger.log(`  🚫 ${field}: القيمة الحالية "${currentValue}" محمية`);
      delete payload.fields[field];
    }
  }
}

// 13. دوال مساعدة - Helper Functions
// --------------------------------------------------------

/**
 * إنشاء دالة استخراج نمط
 * @param {string} text النص للبحث فيه
 * @return {Function} دالة الاستخراج
 */
function createExtractor(text) {
  return function(regex) {
    const match = text.match(regex);
    return match ? match[1].replace(/[*<>]/g, '').trim() : "";
  };
}

/**
 * تهيئة بنية بيانات الحجز
 * @param {string} agency اسم الوكالة
 * @return {Object} بنية البيانات الافتراضية
 */
function initializeBookingData(agency) {
  return {
    agency: agency,
    product_id: "",
    reference_number: "",
    main_Customer: "",
    email: "",
    phone: "",
    traveler_name: "",
    special_request: "",
    tour_name: "",
    real_product_name: "",
    tour_option: "",
    destination: "",
    date_trip: "",
    "Pickup location": "",
    "Tour_language": "",
    Adult: 0,
    Student: 0,
    Child: 0,
    Infant: 0,
    youth: 0,
    add_ons: "",
    customer_country: "",
    cancellation_status: "Active",
    cancellation_date: "",
    "Google Map": "",
    "Total price EUR": null,
    "Total price USD": null,
    net_rate: ""
  };
}

/**
 * تسجيل البيانات للتدقيق
 * @param {string} reference رقم المرجع
 * @param {Object} fields الحقول المرسلة
 */
function logDataForAudit(reference, fields) {
  Logger.log(`ℹ️ البيانات المرسلة إلى Airtable للحجز ${reference}:`);
  
  const importantFields = ["Date Trip", "Total price EUR", "Total price USD", "Booking Status"];
  
  for (const key in fields) {
    if (importantFields.includes(key)) {
      Logger.log(`  - ${key}: ${JSON.stringify(fields[key])} (${typeof fields[key]})`);
    }
  }
}

/**
 * إرسال بريد إلكتروني تنبيه
 * @param {string} subject الموضوع
 * @param {string} body المحتوى
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

/**
 * توليد تقرير المعالجة
 * @param {Object} results نتائج المعالجة
 */
function generateProcessingReport(results) {
  if (results.errors === 0) return;
  
  const report = `
تمت المعالجة: ${results.processed}
الأخطاء: ${results.errors}

تفاصيل الأخطاء:
${results.errorMessages.map(e => `- ${e.subject}: ${e.error}`).join('\n')}
  `.trim();
  
  sendAlertEmail(
    `تقرير معالجة - ${results.processed} نجاح، ${results.errors} فشل`,
    report
  );
}

// 14. دوال الإدارة والاختبار - Administration Functions
// --------------------------------------------------------

/**
 * إنشاء trigger زمني للتشغيل التلقائي
 */
function createTrigger() {
  // حذف triggers موجودة
  const triggers = ScriptApp.getProjectTriggers();
  for (const trigger of triggers) {
    if (trigger.getHandlerFunction() === 'sendEmailsToAirtable') {
      ScriptApp.deleteTrigger(trigger);
    }
  }
  
  // إنشاء trigger جديد
  ScriptApp.newTrigger('sendEmailsToAirtable')
    .timeBased()
    .everyHours(1)
    .create();
    
  Logger.log('✅ تم إنشاء مشغل تلقائي للتشغيل كل ساعة');
}

// 15. دوال الاختبار - Testing Functions
// --------------------------------------------------------

/**
 * اختبار الاتصال بـ Airtable
 */
function testAirtableConnection() {
  const headers = {
    Authorization: `Bearer ${CONFIG.KEYS.AIRTABLE}`,
    'Content-Type': 'application/json'
  };
  
  try {
    const url = `${CONFIG.AIRTABLE.URL}?maxRecords=1`;
    Logger.log(`🧪 اختبار الاتصال: ${url}`);
    
    const response = UrlFetchApp.fetch(url, { 
      method: "get", 
      headers,
      muteHttpExceptions: true 
    });
    
    Logger.log(`📊 كود الاستجابة: ${response.getResponseCode()}`);
    
    if (response.getResponseCode() === 200) {
      Logger.log('✅ الاتصال يعمل بشكل صحيح');
    } else {
      Logger.log(`❌ خطأ: ${response.getContentText()}`);
    }
  } catch (err) {
    Logger.log(`❌ خطأ في الاختبار: ${err.message}`);
  }
}

/**
 * اختبار معالجة إيميل واحد
 * @param {string} emailSubject موضوع الإيميل
 */
function testProcessSingleEmail(emailSubject) {
  const query = `subject:"${emailSubject}"`;
  const threads = GmailApp.search(query, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على إيميل مطابق');
    return;
  }
  
  try {
    processThread(threads[0]);
    Logger.log('✅ تمت معالجة الاختبار بنجاح');
  } catch (err) {
    Logger.log(`❌ خطأ: ${err.message}`);
  }
}

/**
 * اختبار معالجة إيميل واحد مع تفاصيل كاملة
 * @param {string} emailSubject موضوع الإيميل
 */
function testProcessSingleEmailDetailed(emailSubject) {
  Logger.log('🧪 اختبار معالجة إيميل بالتفصيل:');
  Logger.log(`البحث عن: "${emailSubject}"`);
  
  const threads = GmailApp.search(`subject:"${emailSubject}"`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على إيميل مطابق');
    return;
  }
  
  const thread = threads[0];
  const messages = thread.getMessages();
  Logger.log(`📧 عدد الرسائل في المحادثة: ${messages.length}`);
  
  const message = messages[0]; // أول رسالة
  Logger.log(`\n📋 معلومات الرسالة:`);
  Logger.log(`  التاريخ: ${message.getDate()}`);
  Logger.log(`  المرسل: ${message.getFrom()}`);
  Logger.log(`  مميزة بنجمة: ${message.isStarred() ? '⭐' : '❌'}`);
  
  if (message.isStarred()) {
    Logger.log('⚠️ الرسالة مميزة بنجمة وسيتم تجاهلها');
    return;
  }
  
  const body = message.getPlainBody() || message.getBody();
  Logger.log(`\n📄 أول 300 حرف من المحتوى:`);
  Logger.log(body.substring(0, 300) + '...');
  
  // المرحلة 1: استخراج البيانات
  Logger.log('\n🔧 المرحلة 1: استخراج البيانات الأساسية');
  const bookingData = extractBookingData(body);
  
  if (!bookingData.reference_number) {
    Logger.log('❌ فشل: لم يتم العثور على رقم الحجز');
    Logger.log('البيانات المستخرجة:');
    Logger.log(JSON.stringify(bookingData, null, 2));
    return;
  }
  
  Logger.log(`✅ رقم الحجز: ${bookingData.reference_number}`);
  Logger.log('البيانات المستخرجة:');
  for (const [key, value] of Object.entries(bookingData)) {
    if (value !== "" && value !== 0 && value !== null && value !== undefined) {
      Logger.log(`  ${key}: ${JSON.stringify(value)}`);
    }
  }
  
  // المرحلة 2: تحسين البيانات
  Logger.log('\n🔧 المرحلة 2: تحسين البيانات');
  const enhancedData = enhanceBookingData(bookingData, body);
  Logger.log('البيانات المحسنة:');
  for (const [key, value] of Object.entries(enhancedData)) {
    if (value !== "" && value !== 0 && value !== null && value !== undefined &&
        JSON.stringify(value) !== JSON.stringify(bookingData[key])) {
      Logger.log(`  ${key}: ${JSON.stringify(value)} (محدث)`);
    }
  }
  
  // المرحلة 3: تنقيح البيانات
  Logger.log('\n🔧 المرحلة 3: تنقيح البيانات');
  const sanitizedData = sanitizeAirtableData(enhancedData);
  
  // المرحلة 4: تحويل إلى حقول Airtable
  Logger.log('\n🔧 المرحلة 4: تحويل إلى حقول Airtable');
  const airtableFields = mapFieldsToAirtable(sanitizedData);
  
  if (Object.keys(airtableFields).length === 0) {
    Logger.log('❌ لا توجد حقول صالحة للإرسال!');
    return;
  }
  
  Logger.log('الحقول النهائية:');
  for (const [key, value] of Object.entries(airtableFields)) {
    Logger.log(`  ${key}: ${JSON.stringify(value)}`);
  }
  
  // اختبار الإرسال (اختياري)
  const userResponse = Browser.msgBox(
    'اختبار الإرسال',
    'هل تريد إرسال البيانات إلى Airtable؟',
    Browser.Buttons.YES_NO
  );
  
  if (userResponse === Browser.Buttons.YES) {
    try {
      sendDataToAirtable(sanitizedData);
      message.star();
      Logger.log('\n✅ تم إرسال البيانات بنجاح ووضع نجمة على الرسالة');
    } catch (err) {
      Logger.log(`\n❌ خطأ في الإرسال: ${err.message}`);
    }
  } else {
    Logger.log('\n⏭️ تم تخطي الإرسال');
  }
}

/**
 * اختبار استخراج الأسعار
 */
function testPriceExtraction() {
  const samples = [
    // GetYourGuide samples
    "Price: €123.45",
    "Total price: €200",
    "Total: €99.90",
    "The total amount is EUR 150.50",
    
    // Viator samples  
    "Net Rate: USD $89.99",
    "Total: USD $150.00",
    "Total Price: $200",
    "Total Due: $125.50"
  ];
  
  Logger.log("🧪 اختبار استخراج الأسعار:");
  
  for (const sample of samples) {
    Logger.log(`\nعينة: "${sample}"`);
    
    // اختبار GetYourGuide
    const gygPrice = extractPriceGetYourGuide(sample);
    if (gygPrice) {
      Logger.log(`  GetYourGuide: €${gygPrice}`);
    }
    
    // اختبار Viator
    const viatorPrice = extractPriceViator(sample);
    if (viatorPrice) {
      Logger.log(`  Viator: ${viatorPrice}`);
    }
    
    // اختبار عام
    const generalPrices = extractPriceGeneral(sample);
    if (generalPrices.EUR || generalPrices.USD) {
      Logger.log(`  عام: EUR: €${generalPrices.EUR || '-'}, USD: ${generalPrices.USD || '-'}`);
    }
  }
}

/**
 * اختبار استخراج السعر من إيميل كامل
 */
function testFullEmailPriceExtraction() {
  const threads = GmailApp.search('from:getyourguide.com OR from:viator.com', 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على إيميلات للاختبار');
    return;
  }
  
  const message = threads[0].getMessages()[0];
  const body = message.getPlainBody();
  
  Logger.log('🧪 اختبار استخراج السعر من إيميل حقيقي:');
  Logger.log(`الموضوع: ${message.getSubject()}`);
  
  if (isGetYourGuideEmail(body)) {
    Logger.log('نوع الإيميل: GetYourGuide');
    const data = extractGetYourGuideData(body);
    Logger.log(`السعر: €${data["Total price EUR"] || 'غير موجود'}`);
  } else if (isViatorEmail(body)) {
    Logger.log('نوع الإيميل: Viator');
    const data = extractViatorData(body);
    Logger.log(`السعر: ${data["Total price USD"] || 'غير موجود'}`);
  }
}

/**
 * معاينة محتوى الإيميل لتحديد أماكن الأسعار
 * @param {string} emailSubject موضوع الإيميل
 */
function previewEmailForPrices(emailSubject) {
  const threads = GmailApp.search(`subject:${emailSubject}`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على الإيميل');
    return;
  }
  
  const message = threads[0].getMessages()[0];
  const body = message.getPlainBody();
  
  const pricePatterns = [
    /[€€]\s*(\d+(?:[.,]\d+)?)/g,
    /(\d+(?:[.,]\d+)?)\s*EUR/ig,
    /\$\s*(\d+(?:[.,]\d+)?)/g,
    /(\d+(?:[.,]\d+)?)\s*USD/ig,
    /price[^€$]*([€$]\s*\d+(?:[.,]\d+)?)/ig,
    /total[^€$]*([€$]\s*\d+(?:[.,]\d+)?)/ig
  ];
  
  Logger.log('🔍 مسح الإيميل بحثاً عن الأسعار:');
  
  for (const pattern of pricePatterns) {
    const matches = body.matchAll(pattern);
    for (const match of matches) {
      const start = Math.max(0, match.index - 30);
      const end = Math.min(body.length, match.index + 50);
      const context = body.substring(start, end);
      Logger.log(`📍 تطابق: "${context.trim()}"`);
    }
  }
}

/**
 * الحصول على قائمة الحقول في Airtable
 */
function getAirtableFields() {
  const headers = {
    Authorization: `Bearer ${CONFIG.KEYS.AIRTABLE}`,
    'Content-Type': 'application/json'
  };
  
  try {
    const url = `${CONFIG.AIRTABLE.URL}?maxRecords=1`;
    const response = UrlFetchApp.fetch(url, { 
      method: "get", 
      headers,
      muteHttpExceptions: true 
    });
    
    const data = JSON.parse(response.getContentText());
    if (data.records && data.records.length > 0) {
      const fields = Object.keys(data.records[0].fields);
      Logger.log(`📋 الحقول المتاحة: ${fields.join(', ')}`);
    } else {
      Logger.log('⚠️ لا توجد سجلات في الجدول');
    }
  } catch (err) {
    Logger.log(`❌ خطأ: ${err.message}`);
  }
}

// 16. دوال اختبار حماية حالة الإلغاء والتشخيص
// --------------------------------------------------------

/**
 * اختبار حماية حقل Booking Status
 */
function testBookingStatusProtection() {
  Logger.log('🧪 اختبار حماية حقل Booking Status:');
  
  // سيناريوهات الاختبار
  const testCases = [
    {
      name: "سجل موجود بحالة Canceled",
      existingRecord: { fields: { "Booking Status": "Canceled", "Customer Name": "أحمد" } },
      newPayload: { fields: { "Booking Status": "Active", "Customer Name": "محمد" } },
      expectedStatus: undefined // يجب حذف الحقل
    },
    {
      name: "سجل موجود بحالة Active",
      existingRecord: { fields: { "Booking Status": "Active", "Customer Name": "أحمد" } },
      newPayload: { fields: { "Booking Status": "Canceled", "Customer Name": "محمد" } },
      expectedStatus: "Canceled" // يجب السماح بالتحديث
    },
    {
      name: "سجل موجود بدون حالة",
      existingRecord: { fields: { "Customer Name": "أحمد" } },
      newPayload: { fields: { "Booking Status": "Active", "Customer Name": "محمد" } },
      expectedStatus: "Active" // يجب السماح بالإضافة
    }
  ];
  
  for (const testCase of testCases) {
    Logger.log(`\n📝 ${testCase.name}:`);
    Logger.log(`  قبل: ${JSON.stringify(testCase.existingRecord.fields)}`);
    Logger.log(`  البيانات الجديدة: ${JSON.stringify(testCase.newPayload.fields)}`);
    
    // استنساخ البيانات لتجنب التعديل على الأصل
    const payloadCopy = JSON.parse(JSON.stringify(testCase.newPayload));
    
    // تطبيق الحماية
    protectExistingFields(testCase.existingRecord, payloadCopy);
    
    // التحقق من النتيجة
    const actualStatus = payloadCopy.fields["Booking Status"];
    const passed = actualStatus === testCase.expectedStatus;
    
    Logger.log(`  بعد: ${JSON.stringify(payloadCopy.fields)}`);
    Logger.log(`  النتيجة: ${passed ? '✅ نجح' : '❌ فشل'}`);
    
    if (!passed) {
      Logger.log(`  متوقع: ${testCase.expectedStatus}, فعلي: ${actualStatus}`);
    }
  }
}

/**
 * تشخيص مشكلة استخراج البيانات من إيميل
 * @param {string} emailSubject موضوع الإيميل
 */
function diagnoseEmailExtraction(emailSubject) {
  const threads = GmailApp.search(`subject:"${emailSubject}"`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على الإيميل');
    return;
  }
  
  const message = threads[0].getMessages()[0];
  const body = message.getPlainBody();
  
  Logger.log('🔍 تشخيص استخراج البيانات:');
  Logger.log(`📧 الموضوع: ${message.getSubject()}`);
  Logger.log(`📅 التاريخ: ${message.getDate()}`);
  
  // تحديد نوع الإيميل
  const isGYG = isGetYourGuideEmail(body);
  const isViator = isViatorEmail(body);
  
  Logger.log(`\n📋 نوع الإيميل:`);
  Logger.log(`  GetYourGuide: ${isGYG ? '✅' : '❌'}`);
  Logger.log(`  Viator: ${isViator ? '✅' : '❌'}`);
  
  if (!isGYG && !isViator) {
    Logger.log('⚠️ نوع الإيميل غير معروف');
    Logger.log('📝 أول 500 حرف من الإيميل:');
    Logger.log(body.substring(0, 500));
    return;
  }
  
  // استخراج البيانات
  Logger.log('\n📊 استخراج البيانات:');
  const bookingData = extractBookingData(body);
  
  // عرض البيانات المستخرجة
  Logger.log('\n📦 البيانات المستخرجة:');
  for (const [key, value] of Object.entries(bookingData)) {
    if (value !== "" && value !== 0 && value !== null && value !== undefined) {
      Logger.log(`  ${key}: ${JSON.stringify(value)}`);
    }
  }
  
  // تحديد الحقول الناقصة
  const missingFields = identifyMissingFields(bookingData);
  if (missingFields.length > 0) {
    Logger.log(`\n⚠️ الحقول الناقصة: ${missingFields.join(', ')}`);
  }
  
  // محاولة تحسين البيانات
  Logger.log('\n🔧 محاولة تحسين البيانات...');
  const enhancedData = enhanceBookingData(bookingData, body);
  
  // عرض البيانات المحسنة
  Logger.log('\n📦 البيانات بعد التحسين:');
  for (const [key, value] of Object.entries(enhancedData)) {
    if (value !== "" && value !== 0 && value !== null && value !== undefined) {
      Logger.log(`  ${key}: ${JSON.stringify(value)}`);
    }
  }
  
  // تنقيح البيانات
  const sanitizedData = sanitizeAirtableData(enhancedData);
  
  // تحويل إلى حقول Airtable
  const airtableFields = mapFieldsToAirtable(sanitizedData);
  
  Logger.log('\n📤 الحقول النهائية لـ Airtable:');
  if (Object.keys(airtableFields).length === 0) {
    Logger.log('❌ لا توجد حقول صالحة للإرسال!');
  } else {
    for (const [key, value] of Object.entries(airtableFields)) {
      Logger.log(`  ${key}: ${JSON.stringify(value)}`);
    }
  }
}

/**
 * فحص الحقول المطلوبة والناقصة
 * @param {Object} data بيانات الحجز
 */
function checkRequiredFields(data) {
  Logger.log('\n📋 فحص الحقول المطلوبة:');
  
  // فحص الحقول الحرجة
  Logger.log('\n🔴 الحقول الحرجة:');
  for (const field of BOOKING_FIELDS.CRITICAL) {
    const value = data[field];
    const hasValue = value !== undefined && value !== null && value !== "" && 
                     !(typeof value === 'number' && value === 0);
    
    Logger.log(`  ${field}: ${hasValue ? '✅' : '❌'} ${hasValue ? `(${JSON.stringify(value)})` : 'مفقود'}`);
  }
  
  // فحص الحقول الثانوية
  Logger.log('\n🟡 الحقول الثانوية:');
  for (const field of BOOKING_FIELDS.SECONDARY) {
    const value = data[field];
    const hasValue = value !== undefined && value !== null && value !== "" && 
                     !(typeof value === 'number' && value === 0);
    
    Logger.log(`  ${field}: ${hasValue ? '✅' : '⚠️'} ${hasValue ? `(${JSON.stringify(value)})` : 'اختياري'}`);
  }
  
  // فحص الحقول الرقمية
  Logger.log('\n🔢 الحقول الرقمية:');
  let totalParticipants = 0;
  for (const field of BOOKING_FIELDS.NUMERIC) {
    const value = data[field] || 0;
    if (value > 0) {
      Logger.log(`  ${field}: ${value}`);
      totalParticipants += value;
    }
  }
  Logger.log(`  📊 المجموع: ${totalParticipants} مشارك`);
  
  // الأسعار
  Logger.log('\n💰 الأسعار:');
  const hasEUR = data["Total price EUR"] !== null && data["Total price EUR"] !== undefined;
  const hasUSD = data["Total price USD"] !== null && data["Total price USD"] !== undefined;
  
  Logger.log(`  EUR: ${hasEUR ? `€${data["Total price EUR"]}` : '❌'}`);
  Logger.log(`  USD: ${hasUSD ? `${data["Total price USD"]}` : '❌'}`);
  
  if (!hasEUR && !hasUSD && data.net_rate) {
    Logger.log(`  Net Rate: ${data.net_rate} (سيتم استخدامه كسعر)`);
  }
}

/**
 * اختبار استخراج البيانات بدون إرسال
 * @param {string} emailSubject موضوع الإيميل
 */
function testExtractDataOnly(emailSubject) {
  const threads = GmailApp.search(`subject:"${emailSubject}"`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على الإيميل');
    return;
  }
  
  const message = threads[0].getMessages()[0];
  const body = message.getPlainBody() || message.getBody();
  
  Logger.log('📧 اختبار استخراج البيانات فقط');
  Logger.log(`الموضوع: ${message.getSubject()}`);
  
  // استخراج البيانات
  const bookingData = extractBookingData(body);
  
  if (!bookingData.reference_number) {
    Logger.log('❌ لم يتم العثور على رقم الحجز');
    Logger.log('محاولة عرض أنماط شائعة:');
    
    const patterns = [
      /Reference\s*(?:Number|#|Nr\.?)?\s*:?\s*([A-Z0-9\-]+)/i,
      /Booking\s*(?:Reference|#|Nr\.?)?\s*:?\s*([A-Z0-9\-]+)/i,
      /(GYG[A-Z0-9]{6,})/i,
      /(BR-[A-Z0-9\-]+)/i
    ];
    
    for (const pattern of patterns) {
      const match = body.match(pattern);
      if (match) {
        Logger.log(`  نمط محتمل: ${match[0]}`);
      }
    }
    return;
  }
  
  // تحسين البيانات
  const enhancedData = enhanceBookingData(bookingData, body);
  
  // تنقيح البيانات
  const sanitizedData = sanitizeAirtableData(enhancedData);
  
  // تحويل إلى حقول Airtable
  const airtableFields = mapFieldsToAirtable(sanitizedData);
  
  // عرض النتائج
  Logger.log('\n📊 البيانات المستخرجة والمعالجة:');
  Logger.log('================================');
  
  for (const [key, value] of Object.entries(airtableFields)) {
    Logger.log(`${key}: ${JSON.stringify(value)}`);
  }
  
  Logger.log('================================');
  Logger.log(`📋 عدد الحقول: ${Object.keys(airtableFields).length}`);
  
  // فحص الحقول المطلوبة
  checkRequiredFields(sanitizedData);
}

/**
 * إعادة تعيين النجوم عن الإيميلات للاختبار
 * @param {string} label اسم التصنيف
 * @param {number} count عدد المحادثات
 */
function resetStarsForTesting(label, count = 5) {
  const labelObj = GmailApp.getUserLabelByName(label || CONFIG.PROCESSING.LABEL);
  if (!labelObj) {
    Logger.log(`❌ التصنيف "${label}" غير موجود`);
    return;
  }
  
  const threads = labelObj.getThreads(0, count);
  Logger.log(`🔄 إزالة النجوم من ${threads.length} محادثة...`);
  
  let removedCount = 0;
  for (const thread of threads) {
    const messages = thread.getMessages();
    for (const message of messages) {
      if (message.isStarred()) {
        message.unstar();
        removedCount++;
      }
    }
  }
  
  Logger.log(`✅ تم إزالة ${removedCount} نجمة`);
}

/**
 * اختبار استخراج البيانات بدون إرسال
 * @param {string} emailSubject موضوع الإيميل
 */
function testExtractDataOnly(emailSubject) {
  const threads = GmailApp.search(`subject:"${emailSubject}"`, 0, 1);
  
  if (threads.length === 0) {
    Logger.log('⚠️ لم يتم العثور على الإيميل');
    return;
  }
  
  const message = threads[0].getMessages()[0];
  const body = message.getPlainBody() || message.getBody();
  
  Logger.log('📧 اختبار استخراج البيانات فقط');
  Logger.log(`الموضوع: ${message.getSubject()}`);
  
  // استخراج البيانات
  const bookingData = extractBookingData(body);
  
  if (!bookingData.reference_number) {
    Logger.log('❌ لم يتم العثور على رقم الحجز');
    Logger.log('محاولة عرض أنماط شائعة:');
    
    const patterns = [
      /Reference\s*(?:Number|#|Nr\.?)?\s*:?\s*([A-Z0-9\-]+)/i,
      /Booking\s*(?:Reference|#|Nr\.?)?\s*:?\s*([A-Z0-9\-]+)/i,
      /(GYG[A-Z0-9]{6,})/i,
      /(BR-[A-Z0-9\-]+)/i
    ];
    
    for (const pattern of patterns) {
      const match = body.match(pattern);
      if (match) {
        Logger.log(`  نمط محتمل: ${match[0]}`);
      }
    }
    return;
  }
  
  // تحسين البيانات
  const enhancedData = enhanceBookingData(bookingData, body);
  
  // تنقيح البيانات
  const sanitizedData = sanitizeAirtableData(enhancedData);
  
  // تحويل إلى حقول Airtable
  const airtableFields = mapFieldsToAirtable(sanitizedData);
  
  // عرض النتائج
  Logger.log('\n📊 البيانات المستخرجة والمعالجة:');
  Logger.log('================================');
  
  for (const [key, value] of Object.entries(airtableFields)) {
    Logger.log(`${key}: ${JSON.stringify(value)}`);
  }
  
  Logger.log('================================');
  Logger.log(`📋 عدد الحقول: ${Object.keys(airtableFields).length}`);
  
  // فحص الحقول المطلوبة
  checkRequiredFields(sanitizedData);
}

// ================================================
// نهاية معالج الحجوزات - End of Booking Processor
// ================================================
