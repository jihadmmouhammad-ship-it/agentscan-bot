import os, csv, time, smtplib, asyncio, threading, telebot, sys
from email.mime.text import MIMEText
from email.utils import formataddr
from playwright.async_api import async_playwright
from openai import OpenAI

# --- 1. الإعدادات ---
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_TELEGRAM = "@jihad_ai_2_bot"
AGENT_EMAIL = "jihadmmouhammad@gmail.com"

ai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
bot = telebot.TeleBot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

# ملف لحفظ الشركات اللي انمسحت عشان ما نكرر الإيميل
PROCESSED_FILE = "processed_companies.txt"

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def mark_processed(website):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{website}\n")

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

async def run_scan():
    print("🚀 الوكيل بدأ المسح...")
    processed = load_processed()
    try:
        with open("companies.csv", "r", encoding="utf-8") as f:
            companies = list(csv.DictReader(f))
        for comp in companies:
            if not comp.get('website'): continue
            
            # إذا الشركة انمسحت من قبل، تخطاها
            if comp['website'] in processed:
                print(f"⏩ تم تخطي {comp['name']} (تم مسحه سابقاً).")
                continue
                
            print(f"🔍 جاري فحص: {comp['name']}...")
            issues = await scan_site(comp['website'])
            if issues and comp.get('email'):
                send_email(comp['email'], comp['name'], issues)
                
            mark_processed(comp['website']) # حفظ إنه انمسح
            await asyncio.sleep(5)
        print("✅ انتهى المسح بنجاح.")
    except Exception as e:
        print(f"Loop error: {e}")

# --- 3. وكيل الصيد (AliExpress Hunter) ---
async def hunt_aliexpress():
    print("🕵️‍♂️ الوكيل الصياد بدأ البحث...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto("https://www.aliexpress.com/category/100003070/consumer-electronics.html", timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            items = await page.query_selector_all('.multi--titleText--nXeOvyr') 
            prices = await page.query_selector_all('.multi--price-sale--U-S0jtG')
            msg = "🔥 *أفضل المنتجات مبيعاً اليوم:*\n\n"
            for i in range(min(3, len(items), len(prices))):
                title = await items[i].inner_text()
                price = await prices[i].inner_text()
                msg += f"{i+1}. *{title}*\n💰 السعر: {price}\n\n"
            if bot and TELEGRAM_CHAT_ID:
                bot.send_message(TELEGRAM_CHAT_ID, msg, parse_mode='Markdown')
                print("✅ تم إرسال التقرير للتلغرام.")
        except Exception as e:
            print(f"❌ خطأ بالصيد: {e}")
        finally:
            await browser.close()

# --- 4. إدارة التلغرام ---
if bot:
    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        user_text = message.text
        if "صيد" in user_text or "منتجات" in user_text:
            bot.reply_to(message, "تمام، جاري البحث عن منتجات رابحة... استنى شوي.")
            asyncio.run(hunt_aliexpress())
            return

        if not ai_client:
            bot.reply_to(message, "أهلاً بك! أنا جهاد آي. للبحث عن المنتجات اكتب: صيد")
            return
        
        prompt = f"""
        أنت "جهاد آي"، وكيل ذكي ومبيعات من منصة AgentScan.
        الزبون يقول: "{user_text}"
        قواعد:
        1. ممنوع ذكر أسعار.
        2. أسلوبك راقٍ، دافئ، ومقنع.
        3. اختم بـ "معك جهاد."
        """
        try:
            response = ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )
            bot.reply_to(message, response.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, "عذراً، حدث خطأ تقني بسيط.")

# --- 5. التشغيل ---
if __name__ == "__main__":
    asyncio.run(run_scan())
    
    threading.Thread(target=lambda: asyncio.run(hunt_aliexpress()), daemon=True).start()
    
    if bot:
        print("📱 بوت التلغرام يقرأ الرسائل لمدة دقيقة...")
        t = threading.Thread(target=bot.polling, kwargs={'none_stop': True}, daemon=True)
        t.start()
        time.sleep(60)
    
    print("🎉 انتهى كل شيء بنجاح.")
    sys.exit(0)
