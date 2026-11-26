import os, csv, time, smtplib, asyncio, threading, telebot, sys, re
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

PROCESSED_FILE = "processed_companies.txt"

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def mark_processed(website):
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(f"{website}\n")

async def find_email_on_site(page, url):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    try:
        await page.goto(url, timeout=30000, wait_until="domcontentloaded")
        
        content = await page.content()
        if content: # تأكدنا إنه المحتوى مش فاضي
            emails = re.findall(email_regex, content)
            if emails:
                return emails[0]

        links = await page.eval_on_selector_all("a", "els => els.map(e => e.href)")
        contact_links = [l for l in links if l and any(k in l.lower() for k in ["contact", "اتصل", "about", "من-نحن"])]
        
        for link in contact_links[:2]:
            try:
                await page.goto(link, timeout=15000, wait_until="domcontentloaded")
                content = await page.content()
                if content:
                    emails = re.findall(email_regex, content)
                    if emails:
                        return emails[0]
            except:
                continue
        return None
    except:
        return None

async def scan_site(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            found_email = await find_email_on_site(page, url)
            
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            title = await page.title()
            has_contact = "contact" in (await page.content()).lower() or found_email is not None
            
            issues = []
            if not title: issues.append("عنوان الصفحة مفقود.")
            if not has_contact: issues.append("لا توجد صفحة تواصل واضحة.")
            
            return (issues if issues else ["ملاحظات تقنية لتحسين الموقع."]), found_email
        except Exception:
            return [], None
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
            print(f"✅ تم إرسال إيميل لـ: {company_name} على {to_email}")
    except Exception as e:
        print(f"❌ فشل إرسال الإيميل: {e}")

async def run_scan():
    print("🚀 الوكيل بدأ المسح والصيد...")
    processed = load_processed()
    try:
        with open("companies.csv", "r", encoding="utf-8") as f:
            companies = list(csv.DictReader(f))
        for comp in companies:
            if not comp.get('website'): continue
            if comp['website'] in processed:
                print(f"⏩ تم تخطي {comp['name']} (تم مسحه سابقاً).")
                continue
                
            print(f"🔍 جاري فحص: {comp['name']}...")
            issues, found_email = await scan_site(comp['website'])
            
            target_email = comp.get('email', '')
            if target_email:
                target_email = target_email.strip() or found_email
            else:
                target_email = found_email
            
            if issues and target_email:
                send_email(target_email, comp['name'], issues)
            elif not target_email:
                print(f"⚠️ لم يتم العثور على إيميل لـ {comp['name']}")
                
            mark_processed(comp['website'])
            await asyncio.sleep(5)
        print("✅ انتهى المسح بنجاح.")
    except Exception as e:
        print(f"Loop error: {e}")

# --- بوت التلغرام ---
if bot:
    @bot.message_handler(func=lambda message: True)
    def handle_message(message):
        user_text = message.text
        if not ai_client:
            bot.reply_to(message, "أهلاً بك! أنا جهاد آي من AgentScan.")
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

if __name__ == "__main__":
    asyncio.run(run_scan())
    if bot:
        t = threading.Thread(target=bot.polling, kwargs={'none_stop': True}, daemon=True)
        t.start()
        time.sleep(60)
    print("🎉 انتهى كل شيء بنجاح.")
    sys.exit(0)
