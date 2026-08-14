import asyncio
import json
import random
import os
import time
import logging
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import stealth_async
import nest_asyncio

nest_asyncio.apply()

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === THÔNG TIN CỐ ĐỊNH (đã nhúng) ===
BOT_TOKEN = "8663622587:AAFIO8Mvr6hLCqyKvdsD_fQ-hNRxwlyKjNM"
DEFAULT_TARGET = "https://www.facebook.com/profile.php?id=61557730067730"
FB_USER = "0347999535"
FB_PASS = "qhmaicute"
PROXY = None  # Đặt proxy nếu có, ví dụ: "http://user:pass@ip:port"

FB_COOKIES = [
    {"domain": ".facebook.com", "expirationDate": 1818244507.256036, "hostOnly": False, "httpOnly": False, "name": "c_user", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "100067984778655", "id": 1},
    {"domain": ".facebook.com", "expirationDate": 1821268373.421146, "hostOnly": False, "httpOnly": True, "name": "datr", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v39-aq3sWV4CaGn6EBAcZW5V", "id": 2},
    {"domain": ".facebook.com", "expirationDate": 1818244511, "hostOnly": False, "httpOnly": False, "name": "fbl_st", "path": "/", "sameSite": "strict", "secure": True, "session": False, "storeId": "0", "value": "101729642%3BT%3A29778475", "id": 3},
    {"domain": ".facebook.com", "expirationDate": 1794484510.265904, "hostOnly": False, "httpOnly": True, "name": "fr", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "0pFOPZA36cAJQhgIG.AWejN28GQ4quG2Cf3etJ6V7qA2D8SuDN06iGw3yGlMuS31par44.Bqfn-_..AAA.0.0.BqfwIc.AWf9RzfZ1_57nm2nHAGCskiv4wk", "id": 4},
    {"domain": ".facebook.com", "expirationDate": 1787280009.337014, "hostOnly": False, "httpOnly": False, "name": "locale", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "vi_VN", "id": 5},
    {"domain": ".facebook.com", "hostOnly": False, "httpOnly": False, "name": "m_pixel_ratio", "path": "/", "sameSite": "unspecified", "secure": True, "session": True, "storeId": "0", "value": "2.625", "id": 6},
    {"domain": ".facebook.com", "expirationDate": 1821268510.266276, "hostOnly": False, "httpOnly": True, "name": "pas", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "100067984778655%3ARQQlypdm5P", "id": 7},
    {"domain": ".facebook.com", "expirationDate": 1821235272.860229, "hostOnly": False, "httpOnly": True, "name": "ps_l", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "1", "id": 8},
    {"domain": ".facebook.com", "expirationDate": 1821235272.860385, "hostOnly": False, "httpOnly": True, "name": "ps_n", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "1", "id": 9},
    {"domain": ".facebook.com", "expirationDate": 1821268507.258444, "hostOnly": False, "httpOnly": True, "name": "sb", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v39-ahyiqwkPevzaL3IyMURk", "id": 10},
    {"domain": ".facebook.com", "expirationDate": 1791892511, "hostOnly": False, "httpOnly": False, "name": "vpd", "path": "/", "sameSite": "lax", "secure": True, "session": False, "storeId": "0", "value": "v1%3B731x412x2.625", "id": 11},
    {"domain": ".facebook.com", "hostOnly": False, "httpOnly": False, "name": "wd", "path": "/", "sameSite": "unspecified", "secure": True, "session": True, "storeId": "0", "value": "412x869", "id": 12},
    {"domain": ".facebook.com", "expirationDate": 1794484510, "hostOnly": False, "httpOnly": False, "name": "wl_cbv", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "v2%3Bclient_version%3A3248%3Btimestamp%3A1786708508", "id": 13},
    {"domain": ".facebook.com", "expirationDate": 1818244507.258862, "hostOnly": False, "httpOnly": True, "name": "xs", "path": "/", "sameSite": "no_restriction", "secure": True, "session": False, "storeId": "0", "value": "30%3An9p7CuIv_HLSDw%3A2%3A1786708502%3A-1%3A-1", "id": 14}
]

# === BIẾN TOÀN CỤC ===
TARGET_URL = DEFAULT_TARGET
COORDINATES = []
is_running = False
browser = None
total_clicks = 0
start_time = None
last_report_time = None

# === HÀM TÌM NÚT BA CHẤM ===
async def find_more_button(page):
    """
    Tìm nút '...' trên trang Facebook với nhiều selector khác nhau
    """
    selectors = [
        'div[aria-label="Hành động"]',
        'div[aria-label="Actions"]',
        'div[aria-label="Khác"]',
        'div[aria-label="More"]',
        'div[role="button"][aria-label*="Hành động"]',
        'div[role="button"][aria-label*="Actions"]',
        'div[role="button"][aria-label*="Khác"]',
        'div[role="button"][aria-label*="More"]',
        '[data-testid="profile_actions"]',
        '[data-testid="profile_overflow_menu"]',
        'div[class*="action"]',
        'div[class*="overflow"]',
        'div[class*="more"]',
        '//span[contains(text(), "...")]',
        '//span[contains(text(), "Khác")]',
        '//span[contains(text(), "More")]',
        '//div[contains(text(), "...")]',
    ]
    
    for selector in selectors:
        try:
            if selector.startswith('//'):
                element = await page.locator(selector).first
            else:
                element = await page.query_selector(selector)
            if element:
                if await element.is_visible():
                    logger.info(f"Tìm thấy nút '...' với selector: {selector}")
                    return element
        except Exception as e:
            logger.debug(f"Selector {selector} không dùng được: {e}")
    return None

# === HÀM XỬ LÝ JSON ===
def parse_coord_json(content: bytes) -> list:
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("Dữ liệu không phải mảng")
    return [{"x": item["x"], "y": item["y"]} for item in data if "x" in item and "y" in item]

# === LỆNH START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Dame Auto FB - FINAL*\n\n"
        "📤 Gửi file JSON tọa độ (có key x, y)\n"
        "🔗 /settarget <url> – Đổi URL mục tiêu\n"
        "🔍 /showtarget – Xem URL hiện tại\n"
        "📊 /status – Xem trạng thái tấn công\n"
        "▶️ /attack – Bắt đầu click\n"
        "⏹ /stop – Dừng ngay",
        parse_mode="Markdown"
    )

# === LỆNH STATUS ===
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, total_clicks, start_time, TARGET_URL, COORDINATES
    status_text = "📊 *Trạng thái tấn công*\n\n"
    status_text += f"🔹 Trạng thái: {'🟢 Đang chạy' if is_running else '🔴 Đã dừng'}\n"
    status_text += f"🎯 Mục tiêu: {TARGET_URL}\n"
    status_text += f"📌 Số tọa độ: {len(COORDINATES)}\n"
    status_text += f"🖱️ Tổng click: {total_clicks}\n"
    if start_time and is_running:
        elapsed = int(time.time() - start_time)
        m, s = divmod(elapsed, 60)
        h, m = divmod(m, 60)
        status_text += f"⏱️ Thời gian chạy: {h:02d}:{m:02d}:{s:02d}\n"
    else:
        status_text += "⏱️ Thời gian chạy: 00:00:00\n"
    await update.message.reply_text(status_text, parse_mode="Markdown")

# === LỆNH SET TARGET ===
async def set_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TARGET_URL
    args = context.args
    if not args:
        await update.message.reply_text("❌ Cần cung cấp URL. Ví dụ: /settarget https://www.facebook.com/...")
        return
    new_url = args[0].strip()
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        await update.message.reply_text("❌ URL không hợp lệ (phải bắt đầu bằng http:// hoặc https://)")
        return
    TARGET_URL = new_url
    await update.message.reply_text(f"✅ Đã đổi mục tiêu thành:\n{TARGET_URL}")

# === LỆNH SHOW TARGET ===
async def show_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🎯 Mục tiêu hiện tại:\n{TARGET_URL}")

# === NHẬN FILE JSON ===
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global COORDINATES
    doc = update.message.document
    if not doc.file_name.endswith(".json"):
        await update.message.reply_text("❌ Vui lòng gửi file .json")
        return
    file = await doc.get_file()
    raw = await file.download_as_bytearray()
    try:
        coords = parse_coord_json(bytes(raw))
        if not coords:
            await update.message.reply_text("❌ File rỗng hoặc sai định dạng")
            return
        COORDINATES = coords
        await update.message.reply_text(f"✅ Đã nạp {len(COORDINATES)} tọa độ")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

# === LỆNH ATTACK ===
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser, total_clicks, start_time, last_report_time, TARGET_URL, COORDINATES
    if not COORDINATES:
        await update.message.reply_text("❌ Chưa có tọa độ. Hãy gửi file JSON trước.")
        return
    if is_running:
        await update.message.reply_text("⚠️ Bot đang chạy rồi!")
        return

    is_running = True
    total_clicks = 0
    start_time = time.time()
    last_report_time = start_time
    await update.message.reply_text(f"🔥 Bắt đầu tấn công vào {TARGET_URL} với {len(COORDINATES)} tọa độ...")

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
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            await stealth_async(page)

            # === ĐĂNG NHẬP BẰNG COOKIE ===
            cookies = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"), "secure": c.get("secure", True)} for c in FB_COOKIES]
            await context.add_cookies(cookies)
            await page.goto("https://facebook.com", timeout=60000)
            if "login" in page.url:
                await update.message.reply_text("⚠️ Cookie hết hạn, thử đăng nhập bằng user/pass...")
                await page.fill('input[name="email"]', FB_USER)
                await page.fill('input[name="pass"]', FB_PASS)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(5000)
            await page.wait_for_selector('div[role="main"]', timeout=20000)
            await update.message.reply_text("✅ Đăng nhập thành công.")
            
            # === ĐIỀU HƯỚNG TARGET ===
            await page.goto(TARGET_URL, timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=20000)
            await update.message.reply_text(f"✅ Đã vào trang mục tiêu.")

            # === TÌM NÚT BA CHẤM (chỉ để test, không dùng vì bạn có tọa độ) ===
            # more_btn = await find_more_button(page)
            # if more_btn:
            #     await update.message.reply_text("✅ Đã tìm thấy nút '...'")
            # else:
            #     await update.message.reply_text("⚠️ Không tìm thấy nút '...'")

        except Exception as e:
            await update.message.reply_text(f"⚠️ Lỗi đăng nhập/điều hướng: {e}")
            if browser:
                await browser.close()
            is_running = False
            return

        # === VÒNG LẶP CLICK ===
        loop_count = 0
        while is_running:
            for coord in COORDINATES:
                if not is_running:
                    break
                try:
                    x, y = coord["x"], coord["y"]
                    await page.mouse.click(x, y)
                    await asyncio.sleep(random.uniform(0.3, 0.8))
                    loop_count += 1
                    total_clicks += 1

                    # Báo cáo mỗi 100 click hoặc 60 giây
                    now = time.time()
                    if total_clicks % 100 == 0 or (now - last_report_time) >= 60:
                        elapsed = int(now - start_time)
                        m, s = divmod(elapsed, 60)
                        h, m = divmod(m, 60)
                        await update.message.reply_text(
                            f"📊 *Báo cáo*\n"
                            f"🖱️ Đã click: {total_clicks}\n"
                            f"⏱️ Thời gian: {h:02d}:{m:02d}:{s:02d}\n"
                            f"🎯 Mục tiêu: {TARGET_URL}",
                            parse_mode="Markdown"
                        )
                        last_report_time = now
                except Exception as e:
                    error_msg = f"Lỗi click tại ({x},{y}): {e}"
                    logger.error(error_msg)
                    await update.message.reply_text(f"⚠️ {error_msg} - Thử scroll và click lại...")
                    try:
                        await page.evaluate(f"window.scrollTo({x-100}, {y-100});")
                        await asyncio.sleep(1)
                        await page.mouse.click(x, y)
                        total_clicks += 1
                    except:
                        pass
            # Refresh sau mỗi vòng
            await page.reload()
            await asyncio.sleep(1)

        await browser.close()
        is_running = False
        await update.message.reply_text("🛑 Đã dừng tấn công.")

# === LỆNH STOP ===
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser
    is_running = False
    if browser:
        try:
            await browser.close()
        except:
            pass
    await update.message.reply_text("🛑 Đã gửi lệnh dừng.")

# === MAIN ===
def main():
    # Tạo app với timeout lớn để tránh lỗi kết nối
    app = Application.builder().token(BOT_TOKEN).connect_timeout(60).read_timeout(60).build()
    
    # Thêm handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("settarget", set_target))
    app.add_handler(CommandHandler("showtarget", show_target))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Bắt đầu polling với timeout lớn và retry tự động
    logger.info("Bot đang chạy (polling)...")
    app.run_polling(timeout=60, drop_pending_updates=True, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
