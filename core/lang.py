# Astro Userbot
# © جميع الحقوق محفوظة

ROOT_TITLE = "قائمة اوامر Astro"
GROUP_TITLE = "قائمة اوامر"
MENU_WORD = "اوامر"
NOT_FOUND = "❌ القائمة غير موجودة\nالسبب: ما في مجموعة اوامر بهذا الاسم، اكتب {menu} لعرض كل المجموعات"

GROUP_SYSTEM = "النظام"

CMD_MENU = "الاوامر"
CMD_STATUS = "الحالة"
CMD_SYSTEM_STATUS = "حالة النظام"
CMD_UPDATE = "تحديث"
CMD_RESTART = "اعادة تشغيل"
CMD_ADD_FILE = "اضافة ملف"

# menu decoration
DECO_TITLE = "꧁ {} ꧂"
DECO_LINE = "✦ ━━━━━ ◈ ━━━━━ ✦"
DECO_BULLET = "⟡"

# events channel
EVENTS_TITLE = "قناة الاحداث"
EVENTS_ABOUT = "سجل اوامر واشعارات Astro Userbot"
EVENTS_CREATED = "✅ تم انشاء قناة الاحداث لانها ما كانت موجودة، من الان كل الاوامر والاشعارات رح توصل هون"
EVENTS_FALLBACK = "⚠️ تعذر الوصول لقناة الاحداث فتم ارسال هذا الاشعار للرسائل المحفوظة مؤقتا\nالسبب: {reason}\n\n"

# generic labels
LBL_REASON = "السبب"
LBL_DETAILS = "التفاصيل التقنية"
LBL_HINT = "الحل"
LBL_ON = "✅ مفعل"
LBL_OFF = "⛔ متوقف"
LBL_YES = "نعم"
LBL_NO = "لا"
LBL_NONE = "لا يوجد"
LBL_UNKNOWN = "غير معروف"

# durations
UNIT_SECOND = "ثانية"
UNIT_MINUTE = "دقيقة"
UNIT_HOUR = "ساعة"
AND = "و"
AGO = "قبل {}"
IN = "بعد {}"
NEVER = "لم يحدث بعد"

# command flow
CMD_FAILED = "❌ فشل تنفيذ الامر {cmd}"
CMD_FAILED_HINT = "جرب الامر مرة ثانية، واذا تكرر الخطأ ارسل نص هذه الرسالة لتصليحه"

# restart / start
RESTARTING = "⏳ جاري اعادة تشغيل البوت..."
RESTART_DONE = "✅ تم اعادة التشغيل بنجاح"
UPDATE_DONE = "✅ تم تحديث الاضافات واعادة التشغيل بنجاح"
START_DONE = "✅ تم تشغيل البوت بنجاح"
TOOK = "المدة"
SECONDS = "ثانية"
HELP_LINE = "اكتب {cmd} لعرض قائمة الاوامر"

# update
UPDATING = "⏳ جاري سحب الاضافات من المستودع..."
UPDATE_SYNCED = "✅ تم سحب الاضافات: {changed} ملف جديد او محدث من اصل {total}"
UPDATE_NOTHING = "ℹ️ الاضافات محدثة مسبقا، ما في ملفات جديدة"
UPDATE_FAILED = "❌ فشل سحب الاضافات من المستودع"
UPDATE_ABORT = "تم الغاء اعادة التشغيل حتى لا يضيع شغلك، صلح المشكلة وجرب مرة ثانية"

# add file
ADD_ATTACH = "❌ ما في ملف مرفق\nالسبب: ارفق ملف بايثون مع الامر او رد به على رسالة فيها الملف"
ADD_BAD_NAME = "❌ اسم الملف غير صالح: {name}\nالسبب: الاسم لازم يبدأ بحرف انجليزي ويحتوي حروف انجليزية وارقام وشرطة سفلية فقط وينتهي بـ .py\nالحل: اكتب الاسم الصحيح بعد الامر مثل {example}"
ADD_TOO_BIG = "❌ الملف كبير جدا\nالسبب: حجم الملف {size} كيلوبايت والحد الاقصى {limit} كيلوبايت"
ADD_CHECKING = "⏳ جاري فحص الملف {name}..."
ADD_REJECTED = "❌ تم رفض الملف {name}\nالسبب: {reason}"
ADD_UTF8 = "الملف غير مكتوب بترميز UTF-8"
ADD_SYNTAX = "خطأ في كتابة الكود في السطر {line}: {text}"
ADD_SAVING = "⏳ جاري حفظ الملف {name} في المستودع..."
ADD_SAVE_FAILED = "❌ فشل حفظ الملف {name} في المستودع"
ADD_ADDED = "✅ تمت اضافة الاضافة {name}\nاكتب {update} لتفعيلها"
ADD_UPDATED = "✅ تم تحديث الاضافة {name}\nاكتب {update} لتفعيلها"

# plugin loading
LOAD_FAILED = "❌ فشل تحميل الاضافة {name}"
LOAD_FAILED_HINT = "الاضافة معطلة، باقي البوت يعمل بشكل طبيعي. صلح الملف وارسله من جديد بـ {add} ثم {update}"
HOOK_FAILED = "❌ فشل تشغيل المهمة الخلفية للاضافة {name}"
DUP_COMMAND = "الامر {name} مستخدم مسبقا في الاضافة {plugin}، غير اسمه"
NO_GROUP = "الاضافة ما حددت اسم قائمة، استخدم group(...) في اول الملف"
REG_LOCKED = "التسجيل مسموح فقط اثناء تحميل الاضافة"

# status card
SYS_TITLE = "حالة النظام"
SYS_RUNNING = "✅ يعمل بشكل طبيعي"
SYS_STATE = "حالة البوت"
SYS_UPTIME = "مدة التشغيل"
SYS_EVENTS = "قناة الاحداث"
SYS_EVENTS_OK = "✅ متصلة"
SYS_EVENTS_BAD = "⚠️ غير متاحة، يتم استخدام الرسائل المحفوظة"
SYS_SETTINGS = "حفظ الاعدادات"
SYS_SAVED = "✅ كل التغييرات محفوظة في المستودع"
SYS_PENDING = "⏳ في تغييرات بانتظار الحفظ"
SYS_LAST_SAVE = "آخر حفظ"
SYS_SAVE_ERROR = "آخر خطأ حفظ"
SYS_PLUGINS = "الاضافات المحملة"
SYS_COMMANDS = "عدد الاوامر"
SYS_FAILED = "الاضافات الفاشلة"
SYS_PLUGIN_ROW = "{name} ({count} امر)"

# companion bot
BOT_DESC_START = "بدء البوت"
BOT_DESC_STATUS = "حالة النظام"
BOT_DESC_LIST = "قائمة اوامر البوت"
BOT_WELCOME = "✦ اهلا {name}\nهذا البوت خاص بحسابك وما بيرد على احد غيرك\nاكتب /commands لعرض الاوامر"
BOT_LIST_TITLE = "اوامر البوت"
BOT_UNKNOWN = "❌ امر غير موجود\nالحل: اكتب /commands لعرض الاوامر"
BOT_CMD_FAILED = "❌ فشل تنفيذ امر البوت {cmd}"
BOT_BAD_NAME = "اسم امر البوت {name} غير صالح، لازم يبدأ بحرف انجليزي صغير ويحتوي حروف صغيرة وارقام وشرطة سفلية فقط وبحد اقصى 32 حرف"
BOT_DUP = "امر البوت {name} مستخدم مسبقا في الاضافة {plugin}، غير اسمه"
BOT_NOT_STARTED = "البوت ما يعرف حسابك بعد، افتح البوت في تيليجرام واكتب /start"
BOT_NOT_ENABLED = "بوت التحكم غير مفعل، ما في BOT_TOKEN"
BOT_START_FAILED = "❌ فشل تشغيل بوت التحكم"
BOT_START_HINT = "تأكد من BOT_TOKEN من BotFather، باقي النظام يعمل بدون البوت"
SYS_BOT = "بوت التحكم"
SYS_BOT_OFF = "⛔ غير مفعل (ما في BOT_TOKEN)"
SYS_BOT_ON = "✅ متصل {username}"
SYS_BOT_BAD = "⚠️ فشل التشغيل"
SYS_BOT_OWNER = "ربط الحساب"
SYS_BOT_OWNER_OK = "✅ تم"
SYS_BOT_OWNER_NO = "⚠️ افتح البوت واكتب /start"

# storage channel
VAULT_TITLE = "قناة التخزين"
VAULT_ALT = "التخزين"
VAULT_ABOUT = "ارشيف Astro Userbot: الذاتيات والرسائل المحذوفة والمعدلة"
VAULT_CREATED = "✅ تم انشاء قناة التخزين لانها ما كانت موجودة، من الان الذاتيات والمحذوفات رح تنحفظ فيها"
VAULT_FALLBACK = "⚠️ تعذر الوصول لقناة التخزين فتم الحفظ في الرسائل المحفوظة مؤقتا\nالسبب: {reason}\n\n"
SYS_VAULT = "قناة التخزين"
SYS_VAULT_OK = "✅ متصلة"
SYS_VAULT_BAD = "⚠️ غير متاحة، يتم استخدام الرسائل المحفوظة"
