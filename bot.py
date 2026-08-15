import asyncio
import json
import random
import time
import logging
import subprocess
import sys
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async
import nest_asyncio

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === CẤU HÌNH ===
BOT_TOKEN = "8663622587:AAFIO8Mvr6hLCqyKvdsD_fQ-hNRxwlyKjNM"
DEFAULT_TARGET = "https://www.facebook.com/profile.php?id=61557730067730"
FB_USER = "0347999535"
FB_PASS = "qhmaicute"
PROXY = None

# === HÀM KIỂM TRA VÀ TỰ ĐỘNG CÀI ĐẶT PLAYWRIGHT BROWSER ===
def ensure_playwright_browser():
    """Kiểm tra xem chromium đã được cài chưa, nếu chưa thì tự động cài"""
    try:
        # Thử khởi tạo playwright và launch chromium để kiểm tra
        import playwright
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        logger.info("✅ Playwright chromium đã có sẵn.")
        return True
    except Exception as e:
        logger.warning(f"⚠️ Playwright chưa cài hoặc lỗi: {e}")
        logger.info("🔄 Đang cài đặt Playwright chromium...")
        try:
            # Chạy lệnh cài đặt
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
            logger.info("✅ Đã cài đặt Playwright chromium thành công.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Cài đặt thất bại: {e.stderr.decode()}")
            return False

# === GỌI HÀM KIỂM TRA KHI BOT KHỞI ĐỘNG ===
if not ensure_playwright_browser():
    logger.critical("❌ Không thể cài đặt Playwright. Vui lòng chạy thủ công: playwright install chromium")
    # Vẫn tiếp tục nhưng sẽ báo lỗi khi attack

# === DANH SÁCH BÁO CÁO ===
REPORT_ITEMS = [
    {"main": "Vấn đề liên quan đến người dưới 18 tuổi", "sub": "Đe dọa chia sẻ hình ảnh khỏa thân của tôi"},
    {"main": "Vấn đề liên quan đến người dưới 18 tuổi", "sub": "Có vẻ giống hành vi bóc lột tình dục"},
    {"main": "Vấn đề liên quan đến người dưới 18 tuổi", "sub": "Chia sẻ ảnh khỏa thân của ai đó"},
    {"main": "Vấn đề liên quan đến người dưới 18 tuổi", "sub": "Bắt nạt hoặc quấy rối"},
    {"main": "Vấn đề liên quan đến người dưới 18 tuổi", "sub": "Ngược đãi thể chất"},
    {"main": "Bắt nạt, quấy rối hoặc lăng mạ/lạm dụng/ngược đãi", "sub": "Đe dọa chia sẻ hình ảnh khỏa thân của tôi"},
    {"main": "Bắt nạt, quấy rối hoặc lăng mạ/lạm dụng/ngược đãi", "sub": "Có vẻ giống hành vi bóc lột tình dục"},
    {"main": "Bắt nạt, quấy rối hoặc lăng mạ/lạm dụng/ngược đãi", "sub": "Có vẻ giống hành vi buôn người"},
    {"main": "Bắt nạt, quấy rối hoặc lăng mạ/lạm dụng/ngược đãi", "sub": "Bắt nạt hoặc quấy rối"},
    {"main": "Tự tử hoặc tự hại bản thân", "sub": "Tự tử hoặc tự gây thương tích"},
    {"main": "Tự tử hoặc tự hại bản thân", "sub": "Ăn uống thất thường"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Mối đe dọa về an toàn có thể xảy ra"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Có vẻ giống hành vi khủng bố"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Kêu gọi hành vi bạo lực"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Có vẻ giống tội phạm có tổ chức"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Cổ xúy hành vi thù ghét"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Thể hiện hành vi bạo lực, tử vong hoặc thương tích nghiêm trọng"},
    {"main": "Nội dung mang tính bạo lực, thù ghét hoặc gây phiền toái", "sub": "Ngược đãi động vật"},
    {"main": "Bán hoặc quảng bá mặt hàng bị hạn chế", "sub": "Chất cấm, chất gây nghiện"},
    {"main": "Bán hoặc quảng bá mặt hàng bị hạn chế", "sub": "Vũ khí"},
    {"main": "Bán hoặc quảng bá mặt hàng bị hạn chế", "sub": "Đồ uống có cồn"},
    {"main": "Bán hoặc quảng bá mặt hàng bị hạn chế", "sub": "Thuốc lá"},
    {"main": "Bán hoặc quảng bá mặt hàng bị hạn chế", "sub": "Đánh bạc"},
    {"main": "Bán hoặc quảng bá mặt hàng bị hạn chế", "sub": "Động vật"},
    {"main": "Nội dung người lớn", "sub": "Đe dọa chia sẻ hình ảnh khỏa thân của tôi"},
    {"main": "Nội dung người lớn", "sub": "Có vẻ giống hành vi mại dâm"},
    {"main": "Nội dung người lớn", "sub": "Hình ảnh khỏa thân của tôi đã bị chia sẻ"},
    {"main": "Nội dung người lớn", "sub": "Có vẻ giống hành vi bóc lột tình dục"},
    {"main": "Nội dung người lớn", "sub": "Ảnh khỏa thân hoặc hoạt động tình dục"},
    {"main": "Thông tin sai sự thật, lừa đảo hoặc gian lận", "sub": "Gian lận hoặc lừa đảo"},
    {"main": "Thông tin sai sự thật, lừa đảo hoặc gian lận", "sub": "Chia sẻ thông tin sai sự thật"},
    {"main": "Thông tin sai sự thật, lừa đảo hoặc gian lận", "sub": "Spam"},
    {"main": "Trang cá nhân giả", "sub": "Tôi"},
    {"main": "Trang cá nhân giả", "sub": "Một người bạn"},
    {"main": "Trang cá nhân giả", "sub": "Một người nổi tiếng hoặc người của công chúng"},
    {"main": "Trang cá nhân giả", "sub": "Một doanh nghiệp"},
    {"main": "Trang cá nhân giả", "sub": "Tài khoản này không phải là của người thật"},
    {"main": "Vấn đề khác", "sub": None}
]

# === BIẾN TOÀN CỤC ===
TARGET_URL = DEFAULT_TARGET
is_running = False
browser = None
current_index = 0
report_count = 0
total_items = len(REPORT_ITEMS)
DELAY_STEP = 0.8
DELAY_SUBMIT = 0.6

# === HÀM TÌM NÚT ===
async def find_more_button(page):
    selectors = [
        'div[aria-label="Hành động"]',
        'div[aria-label="Actions"]',
        'div[role="button"][aria-label*="chọn"]',
        '[data-testid="profile_actions"]',
        'div[class*="action"]',
        'div[class*="overflow"]',
    ]
    for sel in selectors:
        try:
            el = await page.query_selector(sel)
            if el and await el.is_visible():
                return el
        except:
            continue
    return None

async def wait_for_text(page, text, timeout=5):
    try:
        xpath = f'//span[contains(text(), "{text}")]'
        await page.wait_for_selector(xpath, timeout=timeout * 1000)
        return await page.query_selector(xpath)
    except:
        return None

async def perform_report(page, main_reason, sub_reason):
    try:
        more = await find_more_button(page)
        if not more:
            await page.evaluate('document.elementFromPoint(window.innerWidth-80, 120)?.click()')
        else:
            await more.click()
        await asyncio.sleep(DELAY_STEP)

        report_btn = await wait_for_text(page, "Báo cáo", 4) or await wait_for_text(page, "Tìm hỗ trợ", 4)
        if not report_btn:
            return False
        await report_btn.click()
        await asyncio.sleep(DELAY_STEP)

        main_el = await wait_for_text(page, main_reason, 5)
        if not main_el:
            simple = main_reason.replace("lăng mạ/lạm dụng/ngược đãi", "lạm dụng")
            main_el = await wait_for_text(page, simple, 3)
        if not main_el:
            return False
        await main_el.click()
        await asyncio.sleep(DELAY_STEP)

        if sub_reason:
            sub_el = await wait_for_text(page, sub_reason, 3)
            if sub_el:
                await sub_el.click()
                await asyncio.sleep(DELAY_STEP)

        submit_btn = await wait_for_text(page, "Báo cáo ngay", 4) or await wait_for_text(page, "Gửi", 3)
        if not submit_btn:
            return False
        await submit_btn.click()
        await asyncio.sleep(0.3)
        await submit_btn.click()
        await asyncio.sleep(DELAY_SUBMIT)
        return True
    except Exception as e:
        logger.error(f"Lỗi báo cáo: {e}")
        return False

# === LỆNH TELEGRAM ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Auto Report FB (DOM, không tọa độ)*\n"
        "▶️ /attack – Bắt đầu\n"
        "⏹ /stop – Dừng\n"
        "📊 /status – Trạng thái\n"
        "🔗 /settarget <url> – Đổi target\n"
        "⚡ /setdelay <giây> – Điều chỉnh tốc độ",
        parse_mode="Markdown"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, report_count, current_index, TARGET_URL
    txt = f"📊 *Trạng thái*\n🔹 Chạy: {'🟢' if is_running else '🔴'}\n🎯 {TARGET_URL}\n📌 Đã báo: {report_count}/{total_items}\n⏳ Hiện tại: {REPORT_ITEMS[current_index]['main'] if current_index < total_items else 'Hoàn thành'}"
    await update.message.reply_text(txt, parse_mode="Markdown")

async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TARGET_URL
    if not context.args:
        await update.message.reply_text("❌ Cần URL")
        return
    url = context.args[0].strip()
    if url.startswith(("http://", "https://")):
        TARGET_URL = url
        await update.message.reply_text(f"✅ Đã đổi target:\n{TARGET_URL}")
    else:
        await update.message.reply_text("❌ URL không hợp lệ")

async def set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DELAY_STEP, DELAY_SUBMIT
    if not context.args:
        await update.message.reply_text("❌ Cần số giây, ví dụ /setdelay 0.5")
        return
    try:
        d = float(context.args[0])
        if d < 0.1:
            d = 0.1
        DELAY_STEP = d
        DELAY_SUBMIT = d * 0.8
        await update.message.reply_text(f"✅ Delay = {d:.2f}s, submit = {DELAY_SUBMIT:.2f}s")
    except:
        await update.message.reply_text("❌ Sai số")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser, current_index, report_count
    if is_running:
        await update.message.reply_text("⚠️ Đang chạy rồi!")
        return

    # Kiểm tra lại playwright trước khi chạy
    if not ensure_playwright_browser():
        await update.message.reply_text("❌ Playwright chưa được cài. Bot sẽ tự động cài, vui lòng thử lại sau 1 phút.")
        # Thử cài lại một lần nữa trong background
        asyncio.create_task(run_install())
        return

    is_running = True
    current_index = 0
    report_count = 0
    await update.message.reply_text(f"🔥 Bắt đầu báo cáo vào {TARGET_URL}")

    async with async_playwright() as p:
        launch_opts = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,720"
            ]
        }
        if PROXY:
            launch_opts["proxy"] = {"server": PROXY}

        try:
            browser = await p.chromium.launch(**launch_opts)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await ctx.new_page()
            await stealth_async(page)

            cookies = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"), "secure": c.get("secure", True)} for c in FB_COOKIES]
            await ctx.add_cookies(cookies)
            await page.goto("https://facebook.com", timeout=60000)
            if "login" in page.url:
                await update.message.reply_text("⚠️ Cookie hết hạn, đăng nhập thủ công...")
                await page.fill('input[name="email"]', FB_USER)
                await page.fill('input[name="pass"]', FB_PASS)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(5000)
            await page.wait_for_selector('div[role="main"]', timeout=20000)
            await update.message.reply_text("✅ Đăng nhập thành công.")

            while is_running and current_index < total_items:
                item = REPORT_ITEMS[current_index]
                await update.message.reply_text(f"📌 Đang báo: {item['main']} → {item.get('sub', 'không')}")
                try:
                    await page.goto(TARGET_URL, timeout=30000)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                    success = await perform_report(page, item["main"], item.get("sub"))
                    if success:
                        report_count += 1
                        await update.message.reply_text(f"✅ Thành công ({report_count}/{total_items})")
                    else:
                        await update.message.reply_text("❌ Thất bại, thử lại...")
                        continue
                except Exception as e:
                    await update.message.reply_text(f"⚠️ Lỗi: {e}")
                    await asyncio.sleep(2)
                    continue
                current_index += 1
                if is_running and current_index < total_items:
                    await update.message.reply_text("🔄 Reload...")
                    await page.reload()
                    await asyncio.sleep(1)

            await update.message.reply_text("🏁 Hoàn thành tất cả!")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi nghiêm trọng: {e}")
        finally:
            if browser:
                await browser.close()
            is_running = False

async def run_install():
    # Hàm cài đặt nền
    logger.info("Đang cài Playwright chromium trong nền...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True, capture_output=True)
        logger.info("✅ Cài đặt thành công.")
    except Exception as e:
        logger.error(f"❌ Cài đặt thất bại: {e}")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser
    is_running = False
    if browser:
        try:
            await browser.close()
        except:
            pass
    await update.message.reply_text("🛑 Đã dừng.")

# === MAIN ===
def main():
    app = Application.builder().token(BOT_TOKEN).connect_timeout(60).read_timeout(60).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("settarget", set_target))
    app.add_handler(CommandHandler("setdelay", set_delay))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("stop", stop))
    logger.info("Bot đang chạy...")
    app.run_polling(timeout=60, drop_pending_updates=True)

if __name__ == "__main__":
    main()
