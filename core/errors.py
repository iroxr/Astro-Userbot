# Astro Userbot
# © جميع الحقوق محفوظة
import html
import re

from . import lang


class PluginError(Exception):
    """Raised by the core with a ready, human readable message."""


# Reasons are matched by class name through the MRO, so a missing class in an
# older library version can never break the import.
REASONS = {
    "ChatWriteForbiddenError": "ما عندك صلاحية الكتابة في هذه المحادثة",
    "ChatSendPlainForbiddenError": "ارسال الرسائل النصية ممنوع في هذه المحادثة",
    "ChatSendMediaForbiddenError": "ارسال الوسائط ممنوع في هذه المحادثة",
    "ChatSendPhotosForbiddenError": "ارسال الصور ممنوع في هذه المحادثة",
    "ChatSendVideosForbiddenError": "ارسال الفيديو ممنوع في هذه المحادثة",
    "ChatRestrictedError": "هذه المحادثة مقيدة ولا يمكن الارسال فيها",
    "ChatAdminRequiredError": "العملية تحتاج صلاحية ادمن وحسابك مش ادمن هنا",
    "ChatAdminInviteRequiredError": "العملية تحتاج صلاحية دعوة الاعضاء",
    "UserBannedInChannelError": "حسابك محظور من الكتابة في هذه المحادثة",
    "ChannelBannedError": "القناة محظورة من تيليجرام",
    "ChannelPrivateError": "القناة خاصة وحسابك مش عضو فيها او تم طردك منها",
    "ChannelInvalidError": "القناة غير صالحة او تم حذفها",
    "ChannelsTooMuchError": "حسابك وصل للحد الاقصى من القنوات والمجموعات المسموحة",
    "ChannelsAdminPublicTooMuchError": "حسابك وصل للحد الاقصى من القنوات العامة",
    "PeerIdInvalidError": "المعرف غير صحيح او حسابك ما شاف هذه المحادثة من قبل",
    "InputUserDeactivatedError": "حساب المستخدم محذوف",
    "UserIsBlockedError": "المستخدم حاظر حسابك",
    "UserPrivacyRestrictedError": "اعدادات خصوصية المستخدم تمنع هذه العملية",
    "UserDeactivatedError": "حساب المستخدم محذوف",
    "UserDeactivatedBanError": "الحساب محظور من تيليجرام",
    "UsernameNotOccupiedError": "اسم المستخدم غير موجود",
    "UsernameInvalidError": "اسم المستخدم غير صحيح",
    "AuthKeyUnregisteredError": "الجلسة SESSION انتهت او تم الغاؤها، اعمل جلسة جديدة بـ gen_session.py",
    "SessionRevokedError": "تم انهاء الجلسة من اعدادات الاجهزة في تيليجرام",
    "SessionExpiredError": "الجلسة منتهية، اعمل جلسة جديدة بـ gen_session.py",
    "MessageIdInvalidError": "رقم الرسالة غير صحيح او الرسالة انحذفت",
    "MessageDeleteForbiddenError": "ما عندك صلاحية حذف الرسالة (لازم تكون ادمن بصلاحية حذف الرسائل)",
    "MessageNotModifiedError": "نص الرسالة الجديد نفس القديم",
    "MessageTooLongError": "الرسالة اطول من 4096 حرف",
    "MessageEmptyError": "الرسالة فاضية",
    "MediaEmptyError": "الوسائط غير صالحة او غير موجودة",
    "MediaCaptionTooLongError": "التعليق على الوسائط اطول من المسموح",
    "WebpageCurlFailedError": "تيليجرام ما قدر يحمل رابط الصفحة",
    "WebpageMediaEmptyError": "رابط الصفحة ما فيه وسائط صالحة",
    "FileReferenceExpiredError": "مرجع الملف انتهت صلاحيته",
    "ChatForwardsRestrictedError": "المصدر محمي من النسخ والتحويل",
    "TopicClosedError": "الموضوع مغلق ولا يمكن الكتابة فيه",
    "SlowModeWaitError": "الوضع البطيء مفعل في المجموعة",
    "FloodWaitError": "تيليجرام فرض انتظار مؤقت بسبب كثرة الطلبات",
    "FloodError": "تيليجرام فرض انتظار مؤقت بسبب كثرة الطلبات",
    "TimeoutError": "انتهت مهلة الاتصال بالخادم",
    "ConnectionError": "انقطع الاتصال بالانترنت او بالخادم",
    "ClientConnectorError": "تعذر الاتصال بالخادم",
    "ServerDisconnectedError": "الخادم قطع الاتصال",
    "ClientResponseError": "الخادم رد برد غير صالح",
    "FileNotFoundError": "الملف غير موجود",
    "PermissionError": "ما في صلاحية للوصول للملف",
    "UnicodeDecodeError": "الملف غير مكتوب بترميز UTF-8",
    "JSONDecodeError": "ملف JSON تالف او غير صالح",
    "KeyError": "بيانات ناقصة او تالفة في الاعدادات",
    "ForbiddenError": "تيليجرام رفض العملية لانها غير مسموحة لحسابك",
    "BadRequestError": "تيليجرام رفض الطلب لان فيه بيانات غير صحيحة",
    "ServerError": "خطأ مؤقت من خوادم تيليجرام، جرب بعد قليل",
    "RPCError": "تيليجرام رد بخطأ",
    "CancelledError": "تم الغاء العملية",
}

HTTP = {
    "401": "التوكن GITHUB_TOKEN غير صالح او منتهي",
    "403": "التوكن ما عنده صلاحية Contents قراءة وكتابة على المستودع او تم تجاوز حد الطلبات",
    "404": "المستودع او الملف غير موجود، تأكد من GITHUB_REPO و GITHUB_BRANCH",
    "409": "تعارض في حفظ الملف، حاول مرة ثانية",
    "422": "GitHub رفض الملف، غالبا تعارض في النسخة",
    "429": "تم تجاوز حد الطلبات على GitHub، انتظر قليلا",
}


def _names(exc):
    return [cls.__name__ for cls in type(exc).__mro__]


def _span(seconds):
    from . import ui

    return ui.span(seconds)


def reason(exc):
    """Short Arabic cause for an exception."""
    if isinstance(exc, PluginError):
        return str(exc)
    names = _names(exc)
    if "StorageError" in names:
        found = re.search(r"HTTP (\d{3})", str(exc))
        if found and found[1] in HTTP:
            return HTTP[found[1]]
        return "فشل التواصل مع مستودع GitHub"
    if isinstance(exc, SyntaxError):
        return lang.ADD_SYNTAX.format(line=exc.lineno or "?", text=exc.msg)
    if isinstance(exc, ModuleNotFoundError):
        return f"مكتبة ناقصة: {exc.name}"
    if isinstance(exc, ImportError):
        return f"فشل استيراد جزء من مكتبة: {exc}"
    seconds = getattr(exc, "seconds", None)
    for name in names:
        if name in REASONS:
            base = REASONS[name]
            if seconds and name in ("FloodWaitError", "SlowModeWaitError", "FloodError"):
                return f"{base}، المدة المطلوبة {_span(seconds)}"
            return base
    if isinstance(exc, ValueError):
        return "تعذر تحديد الهدف: المحادثة او المستخدم غير موجود او الحساب ما شافه من قبل"
    return "خطأ غير متوقع في البوت"


def technical(exc):
    text = str(getattr(exc, "message", "") or exc).strip()
    text = " ".join(text.split())[:300]
    name = type(exc).__name__
    return f"{name}: {text}" if text else name


def describe(exc, hint=None):
    """Arabic block: cause, technical detail and an optional hint."""
    lines = [
        f"{lang.LBL_REASON}: {html.escape(reason(exc))}",
        f"{lang.LBL_DETAILS}: <code>{html.escape(technical(exc))}</code>",
    ]
    if hint:
        lines.append(f"{lang.LBL_HINT}: {html.escape(hint)}")
    return "\n".join(lines)


def kind(exc):
    """Class name of the most specific known error, for grouping failures."""
    for name in _names(exc):
        if name in REASONS:
            return name
    return type(exc).__name__
