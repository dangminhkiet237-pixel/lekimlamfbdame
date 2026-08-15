import asyncio
import json
import logging
import os
import sys
import time
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async
import nest_asyncio

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== CẤU HÌNH TỪ BIẾN MÔI TRƯỜNG VỚI FALLBACK TOKEN =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8663622587:AAFIO8Mvr6hLCqyKvdsD_fQ-hNRxwlyKjNM")
DEFAULT_TARGET = os.environ.get("DEFAULT_TARGET", "https://www.facebook.com/profile.php?id=61557730067730")
FB_USER = os.environ.get("FB_USER", "0347999535")
FB_PASS = os.environ.get("FB_PASS", "qhmaicute")
PROXY = os.environ.get("PROXY", None)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
if not WEBHOOK_URL:
    WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{BOT_TOKEN}"
    logger.warning(f"WEBHOOK_URL tự tạo: {WEBHOOK_URL}")

# ===== COOKIE (CÓ THỂ CẬP NHẬT QUA LỆNH) =====
FB_COOKIES = [
    {"domain": ".facebook.com", "expirationDate": 1818296539.966642, "hostOnly": False, "httpOnly": False, "name": "c_user", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "100067984778655", "id": 1},
    {"domain": ".facebook.com", "expirationDate": 1821323219.201854, "hostOnly": False, "httpOnly": True, "name": "datr", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v39-aq3sWV4CaGn6EBAcZW5V", "id": 2},
    {"domain": ".facebook.com", "expirationDate": 1787320559, "hostOnly": False, "httpOnly": False, "name": "dpr", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "1", "id": 3},
    {"domain": ".facebook.com", "expirationDate": 1818300175, "hostOnly": False, "httpOnly": False, "name": "fbl_st", "path": "/", "sameSite": "strict", "secure": True, "session": False, "storeId": "0", "value": "101637987%3BT%3A29779402", "id": 4},
    {"domain": ".facebook.com", "expirationDate": 1794540174.543766, "hostOnly": False, "httpOnly": True, "name": "fr", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "0pFOPZA36cAJQhgIG.AWdCJOp3vpgqKZ2Tl-cnHvYF2_lQSxuFZcI2tcAJiwWJAlQUZIE.Bqfn-_..AAA.0.0.Bqf9uP.AWfUk7_aI6Y-XUclWeZ--qWG0hU", "id": 5},
    {"domain": ".facebook.com", "expirationDate": 1787280009.337014, "hostOnly": False, "httpOnly": False, "name": "locale", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "vi_VN", "id": 6},
    {"domain": ".facebook.com", "expirationDate": 1821324174.544097, "hostOnly": False, "httpOnly": True, "name": "pas", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "100067984778655%3ARQQlypdm5P", "id": 7},
    {"domain": ".facebook.com", "expirationDate": 1821235272.860229, "hostOnly": False, "httpOnly": True, "name": "ps_l", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "1", "id": 8},
    {"domain": ".facebook.com", "expirationDate": 1821235272.860385, "hostOnly": False, "httpOnly": True, "name": "ps_n", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "1", "id": 9},
    {"domain": ".facebook.com", "expirationDate": 1821320539.967243, "hostOnly": False, "httpOnly": True, "name": "sb", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v39-ahyiqwkPevzaL3IyMURk", "id": 10},
    {"domain": ".facebook.com", "expirationDate": 1791948175, "hostOnly": False, "httpOnly": False, "name": "vpd", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "v1%3B731x412x2.625", "id": 11},
    {"domain": ".facebook.com", "expirationDate": 1794540175, "hostOnly": False, "httpOnly": False, "name": "wl_cbv", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v2%3Bclient_version%3A3249%3Btimestamp%3A1786764175", "id": 12},
    {"domain": ".facebook.com", "expirationDate": 1818296539.967325, "hostOnly": False, "httpOnly": True, "name": "xs", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "47%3AmOiZsTKV5Rb25g%3A2%3A1786760539%3A-1%3A-1", "id": 13}
]

# ===== DANH SÁCH BÁO CÁO ĐẦY ĐỦ =====
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

# ===== BIẾN TOÀN CỤC =====
TARGET_URL = DEFAULT_TARGET
is_running = False
browser = None
current_index = 0
report_count = 0
total_items = len(REPORT_ITEMS)
DELAY_STEP = 1.8
DELAY_SUBMIT = 1.4
MAX_RETRY_PER_REASON = 3
TIMEOUT_NAVIGATE = 30000
TIMEOUT_SELECTOR = 10000

# ===== HÀM TÌM NÚT =====
async def find_more_button(page):
    selectors = [
        'div[aria-label="Hành động"]',
        'div[aria-label="Actions"]',
        'div[role="button"][aria-label*="chọn"]',
        'div[role="button"][aria-label*="More"]',
        '[data-testid="profile_actions"]',
        '[data-testid="profile_overflow_menu"]',
        'div[class*="action"]',
        'div[class*="overflow"]',
        'div[class*="more"]',
        '//span[contains(text(), "...")]',
        '//span[contains(text(), "Khác")]',
        '//span[contains(text(), "More")]',
        '//div[contains(@aria-label, "Hành động")]',
        '//div[contains(@aria-label, "Actions")]'
    ]
    for sel in selectors:
        try:
            if sel.startswith('//'):
                el = await page.locator(sel).first
            else:
                el = await page.query_selector(sel)
            if el and await el.is_visible():
                return el
        except:
            continue
    try:
        await page.evaluate('document.elementFromPoint(window.innerWidth-80, 120)?.click()')
        return True
    except:
        return None

async def wait_for_text(page, text, timeout=TIMEOUT_SELECTOR, retry=2):
    for attempt in range(retry + 1):
        try:
            xpath = f'//span[contains(text(), "{text}")]'
            await page.wait_for_selector(xpath, timeout=timeout)
            return await page.query_selector(xpath)
        except PlaywrightTimeoutError:
            if attempt < retry:
                await asyncio.sleep(1)
            else:
                return None
    return None

async def perform_report(page, main_reason, sub_reason):
    try:
        more = await find_more_button(page)
        if not more:
            return False
        if more is not True:
            await more.click()
        await asyncio.sleep(DELAY_STEP)

        report_btn = await wait_for_text(page, "Báo cáo") or await wait_for_text(page, "Tìm hỗ trợ") or await wait_for_text(page, "Report")
        if not report_btn:
            return False
        await report_btn.click()
        await asyncio.sleep(DELAY_STEP)

        main_el = await wait_for_text(page, main_reason, timeout=TIMEOUT_SELECTOR, retry=2)
        if not main_el:
            simple = main_reason.replace("lăng mạ/lạm dụng/ngược đãi", "lạm dụng")
            main_el = await wait_for_text(page, simple, timeout=5000, retry=1)
        if not main_el:
            return False
        await main_el.click()
        await asyncio.sleep(DELAY_STEP)

        if sub_reason:
            sub_el = await wait_for_text(page, sub_reason, timeout=5000, retry=1)
            if sub_el:
                await sub_el.click()
                await asyncio.sleep(DELAY_STEP)

        submit_btn = await wait_for_text(page, "Báo cáo ngay") or await wait_for_text(page, "Gửi") or await wait_for_text(page, "Tiếp tục")
        if not submit_btn:
            try:
                submit_btn = await page.query_selector('button[type="submit"]')
            except:
                pass
        if not submit_btn:
            return False
        await submit_btn.click()
        await asyncio.sleep(0.5)
        await submit_btn.click()
        await asyncio.sleep(DELAY_SUBMIT)
        return True
    except Exception as e:
        logger.error(f"Lỗi perform_report: {e}")
        return False

# ===== LỆNH TELEGRAM =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Auto Report FB – Render Deploy*\n"
        "▶️ /attack – Bắt đầu\n"
        "⏹ /stop – Dừng\n"
        "📊 /status – Trạng thái\n"
        "🔗 /settarget <url> – Đổi target\n"
        "⚡ /setdelay <giây> – Điều chỉnh tốc độ\n"
        "🔄 /reload – Load lại trang\n"
        "📥 Gửi file JSON để cập nhật cookie",
        parse_mode="Markdown"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, report_count, current_index, TARGET_URL
    txt = f"📊 *Trạng thái*\n🔹 Chạy: {'🟢' if is_running else '🔴'}\n🎯 {TARGET_URL}\n📌 Đã báo: {report_count}/{total_items}\n⏳ Hiện tại: {REPORT_ITEMS[current_index]['main'] if current_index < total_items else 'Hoàn thành'}\n⚡ Delay: {DELAY_STEP:.2f}s"
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
        await update.message.reply_text("❌ Cần số giây, ví dụ /setdelay 1.8")
        return
    try:
        d = float(context.args[0])
        if d < 0.5:
            await update.message.reply_text("⚠️ Delay quá thấp, đặt tối thiểu 0.5s")
            d = 0.5
        DELAY_STEP = d
        DELAY_SUBMIT = d * 0.8
        await update.message.reply_text(f"✅ Delay = {d:.2f}s, submit = {DELAY_SUBMIT:.2f}s")
    except:
        await update.message.reply_text("❌ Sai số, nhập dạng số thực (vd: 1.8)")

async def reload_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global browser
    if not is_running:
        await update.message.reply_text("⚠️ Bot không đang chạy.")
        return
    if browser:
        try:
            pages = browser.contexts[0].pages
            if pages:
                await pages[0].reload()
                await update.message.reply_text("🔄 Đã reload trang.")
            else:
                await update.message.reply_text("⚠️ Không tìm thấy trang.")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi reload: {e}")
    else:
        await update.message.reply_text("❌ Browser không tồn tại.")

async def update_cookie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FB_COOKIES
    doc = update.message.document
    if not doc.file_name.endswith(".json"):
        await update.message.reply_text("❌ Vui lòng gửi file .json")
        return
    file = await doc.get_file()
    raw = await file.download_as_bytearray()
    try:
        new_cookies = json.loads(bytes(raw))
        if not isinstance(new_cookies, list):
            raise ValueError("File phải là mảng cookie")
        FB_COOKIES = new_cookies
        await update.message.reply_text(f"✅ Đã cập nhật {len(FB_COOKIES)} cookie mới.")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser, current_index, report_count
    if is_running:
        await update.message.reply_text("⚠️ Đang chạy rồi!")
        return

    is_running = True
    current_index = 0
    report_count = 0
    await update.message.reply_text(f"🔥 Bắt đầu báo cáo vào {TARGET_URL} (timeout 30s)")

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
            await page.goto("https://facebook.com", timeout=TIMEOUT_NAVIGATE)
            if "login" in page.url:
                await update.message.reply_text("⚠️ Cookie hết hạn, đăng nhập thủ công...")
                await page.fill('input[name="email"]', FB_USER)
                await page.fill('input[name="pass"]', FB_PASS)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(5000)
            try:
                await page.wait_for_selector('div[role="main"]', timeout=TIMEOUT_NAVIGATE)
                await update.message.reply_text("✅ Đăng nhập thành công.")
            except:
                await update.message.reply_text("⚠️ Không xác định được trang chính, vẫn thử tiếp.")

            while is_running and current_index < total_items:
                item = REPORT_ITEMS[current_index]
                await update.message.reply_text(f"📌 Đang báo: {item['main']} → {item.get('sub', 'không')}")

                success = False
                for attempt in range(MAX_RETRY_PER_REASON):
                    if not is_running:
                        break
                    try:
                        for nav_try in range(2):
                            try:
                                await page.goto(TARGET_URL, timeout=TIMEOUT_NAVIGATE)
                                await page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVIGATE)
                                break
                            except:
                                if nav_try == 0:
                                    await asyncio.sleep(2)
                                else:
                                    raise
                        result = await perform_report(page, item["main"], item.get("sub"))
                        if result:
                            success = True
                            break
                        else:
                            await update.message.reply_text(f"⚠️ Lần {attempt+1}/{MAX_RETRY_PER_REASON} thất bại, thử lại...")
                            await asyncio.sleep(2)
                    except Exception as e:
                        await update.message.reply_text(f"⚠️ Lỗi: {e}")
                        await asyncio.sleep(3)

                if success:
                    report_count += 1
                    await update.message.reply_text(f"✅ Thành công ({report_count}/{total_items})")
                else:
                    await update.message.reply_text(f"❌ Bỏ qua lý do '{item['main']}' sau {MAX_RETRY_PER_REASON} lần thử.")

                current_index += 1
                if is_running and current_index < total_items:
                    await update.message.reply_text("🔄 Reload trang...")
                    try:
                        await page.reload()
                        await page.wait_for_load_state("networkidle", timeout=TIMEOUT_NAVIGATE)
                    except:
                        pass
                    await asyncio.sleep(1)

            await update.message.reply_text("🏁 Hoàn thành tất cả!")
        except Exception as e:
            await update.message.reply_text(f"❌ Lỗi nghiêm trọng: {e}")
        finally:
            if browser:
                await browser.close()
            is_running = False

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser
    is_running = False
    if browser:
        try:
            await browser.close()
        except:
            pass
    await update.message.reply_text("🛑 Đã dừng.")

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("settarget", set_target))
    app.add_handler(CommandHandler("setdelay", set_delay))
    app.add_handler(CommandHandler("reload", reload_cmd))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.Document.ALL, update_cookie))

    # Set webhook
    if WEBHOOK_URL:
        app.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set: {WEBHOOK_URL}")
    else:
        logger.warning("WEBHOOK_URL không set, chạy polling (không khuyến khích trên Render)")

    port = int(os.environ.get("PORT", 10000))
    app.run_webhook(listen="0.0.0.0", port=port, url_path=BOT_TOKEN)

if __name__ == "__main__":
    main()
