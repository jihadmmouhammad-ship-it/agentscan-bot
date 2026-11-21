import os, csv, time, smtplib, asyncio, re
from email.mime.text import MIMEText
from email.utils import formataddr
from playwright.async_api import async_playwright

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SENDER_NAME = "جهاد آي - AgentScan"

async def scan_site(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=30000)
            title = await page.title()
            content = await page.content()
            has_contact = "contact" in content.lower() or "اتصل" in content
            return {"title": title, "has_contact": has_contact, "status": "OK"}
        except Exception as e:
            return {"title": "", "has_contact": False, "status": "Error"}
        finally:
            await browser.close()

def send_email(to_email, company_name):
    if not to_email: return
    subject = f"ملاحظة تقنية سريعة بخصوص موقع {company_name}"
    body = f"""مرحباً فريق {company_name}،

أنا جهاد آي من منصة AgentScan للمسح الرقمي.
أثناء مسحنا لموقعكم، لاحظنا بعض النقاط التقنية التي قد تؤثر على ظهوركم في محركات البحث وتجربة الزوار.

يسعدنا مشاركة تقرير مختصر معكم دون أي التزام.
هل لديكم دقائق لاستعراض النتائج؟

معك جهاد.
"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((SENDER_NAME, SMTP_USER))
    msg["To"] = to_email
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            print(f"✅ تم إرسال إيميل إلى: {company_name}")
    except Exception as e:
        print(f"❌ فشل إرسال الإيميل إلى {company_name}: {e}")

async def main():
    print("🚀 الوكيل بدأ العمل...")
    while True:
        try:
            with open("companies.csv", "r", encoding="utf-8") as f:
                companies = list(csv.DictReader(f))
            
            for comp in companies:
                print(f"🔍 جاري مسح: {comp['name']}...")
                result = await scan_site(comp['website'])
                if result['status'] == "OK":
                    print(f"   - الموقع يعمل. العنوان: {result['title'][:30]}...")
                    send_email(comp.get('email', '').strip(), comp['name'])
                
                time.sleep(10)
                
            print("⏳ انتهت الدورة. انتظار 24 ساعة للدورة القادمة...")
            time.sleep(86400)
        except Exception as e:
            print(f"خطأ: {e}")
            time.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
