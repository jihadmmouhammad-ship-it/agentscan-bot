import os, csv, time, smtplib, asyncio, threading, telebot
from email.mime.text import MIMEText
from email.utils import formataddr
from playwright.async_api import async_playwright
from openai import OpenAI

# --- 1. الإعدادات (رح نحطها بالخزنة لاحقاً) ---
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_TELEGRAM = "@YourTelegramBot"
AGENT_EMAIL = "contact@agentscan.com"

# --- 2. تجهيز الذكاء الاصطناعي والتلغرام ---
ai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
bot = telebot.TeleBot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

# دالة المسح
async def scan_site(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            title = await page.title()
            has_contact = "contact" in (await page.content()).lower()
            issues = []
            if not title: issues.append("عنوان الصفحة مفقود.")
            if not has_contact: issues.append("لا توجد صفحة تواصل واضحة.")
            return issues if issues else ["ملاحظات تقنية لتحسين الموقع."]
        except Exception:
            return []
        finally:
            await browser.close()

# دالة إرسال الإيميل
def send_email(to_email, company_name, issues):
    if not to_email or not SMTP_USER: return
    subject = f"تقرير مسح رقمي سريع — {company_name}"
    report_text = "\n".join([f"- {issue}" for issue in issues])
    body = f"""مرحباً فريق {company_name}،
أنا جهاد آي من منصة AgentScan. قمنا بمسح رقمي لموقعكم، ولاحظنا:
{report_text}

لإعادة الاتصال بنا:
البريد: {AGENT_EMAIL}
تلغرام: {AGENT_TELEGRAM}

معك جهاد."""
    
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = subject, formataddr(("AgentScan", SMTP_USER)), to_email
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            print(f"✅ تم إرسال إيميل لـ: {company_name}")
    except Exception as e:
        print(f"❌ فشل إرسال الإيميل: {e}")

# دورة المسح اليومية
async def scan_loop():
    print("🚀 الوكيل بدأ المسح...")
    while True:
        try:
            with open("companies.csv", "r", encoding="utf-8") as f:
                companies = list(csv.DictReader(f))
            for comp in companies:
                if not comp.get('website'): continue
                issues = await scan_site(comp['website'])
                if issues and comp.get('email'):
                    send_email(comp['email'], comp['name'], issues)
                await asyncio.sleep(10)
            await asyncio.sleep(86400) # انتظار 24 ساعة
        except Exception as e:
            print(f"Loop error: {e}")
            await asyncio.sleep(60)

# --- 3. بوت التلغرام (المبيعات والتفاوض) ---
if bot:
    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        user_text = message.text
        if not ai_client:
            bot.reply_to(message, "أهلاً بك! أنا جهاد آي من AgentScan. كيف بقدر أساعدك؟")
            return
        
        prompt = f"""
        أنت "جهاد آي"، وكيل ذكي ومبيعات من منصة AgentScan للمسح الرقمي.
        الزبون يقول: "{user_text}"
        قواعد صارمة جداً:
        1. ممنوع تماماً ذكر أي أسعار أو أرقام مالية.
        2. أسلوبك راقٍ، دافئ، ومقنع جداً.
        3. إذا سألك عن الخدمات، اشرح بإيجاز إننا نكشف الثغرات التقنية ونحسن التواجد الرقمي.
        4. إذا وافق على الخدمة، اطلب منه تسجيل الدخول للموقع لاختيار الباقة المناسبة (شهري/سنوي) والمساحة المطلوبة.
        5. اجعل الردود قصيرة (لا تتجاوز 3 أسطر).
        6. اختم أي رد بعبارة "معك جهاد."
        """
        try:
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            bot.reply_to(message, response.choices[0].message.content)
        except Exception as e:
            print(f"AI Error: {e}")
            bot.reply_to(message, "عذراً، حدث خطأ تقني بسيط.")

# --- 4. التشغيل الرئيسي ---
if __name__ == "__main__":
    # تشغيل التلغرام في الخلفية
    if bot:
        threading.Thread(target=bot.infinity_polling, daemon=True).start()
        print("📱 بوت التلغرام شغال وجاهز للرد...")
    
    # تشغيل المسح
    asyncio.run(scan_loop())
