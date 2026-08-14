import asyncio
import json
import random
import os
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import nest_asyncio

nest_asyncio.apply()

# === THÔNG TIN CỐ ĐỊNH ===
BOT_TOKEN = "8663622587:AAFIO8Mvr6hLCqyKvdsD_fQ-hNRxwlyKjNM"

FB_COOKIES = [  # (giữ nguyên cookie của bạn, không thay đổi)
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

FB_USER = "0347999535"
FB_PASS = "qhmaicute"
PROXY = None

COORDINATES = []
is_running = False
browser = None

# === HÀM XỬ LÝ ===
def parse_coord_json(content: bytes) -> list:
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("Không phải mảng")
    return [{"x": item["x"], "y": item["y"]} for item in data if "x" in item and "y" in item]

# === LỆNH ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Dame Auto FB*\n"
        "📤 Gửi file JSON tọa độ\n"
        "▶️ /attack – Bắt đầu\n"
        "⏹ /stop   – Dừng",
        parse_mode="Markdown"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global COORDINATES
    doc = update.message.document
    if not doc.file_name.endswith(".json"):
        await update.message.reply_text("❌ Gửi file .json")
        return
    file = await doc.get_file()
    raw = await file.download_as_bytearray()
    try:
        coords = parse_coord_json(bytes(raw))
        if not coords:
            await update.message.reply_text("❌ File rỗng hoặc sai")
            return
        COORDINATES = coords
        await update.message.reply_text(f"✅ Đã nạp {len(COORDINATES)} tọa độ")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: {e}")

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser
    if not COORDINATES:
        await update.message.reply_text("❌ Chưa có tọa độ")
        return
    if is_running:
        await update.message.reply_text("⚠️ Đang chạy")
        return

    is_running = True
    await update.message.reply_text(f"🔥 Bắt đầu với {len(COORDINATES)} tọa độ...")

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

        browser = await p.chromium.launch(**launch_opts)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        await stealth_async(page)

        try:
            # Đăng nhập bằng cookie
            cookies = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"), "secure": c.get("secure", True)} for c in FB_COOKIES]
            await context.add_cookies(cookies)
            await page.goto("https://facebook.com", timeout=60000)
            if "login" in page.url:
                await update.message.reply_text("⚠️ Cookie hết hạn, dùng user/pass...")
                await page.fill('input[name="email"]', FB_USER)
                await page.fill('input[name="pass"]', FB_PASS)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(5000)
            await page.wait_for_selector('div[role="main"]', timeout=15000)
            await update.message.reply_text("✅ Đăng nhập thành công.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Lỗi login: {e}")
            await browser.close()
            is_running = False
            return

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
                    if loop_count % 30 == 0:
                        await update.message.reply_text(f"✅ Đã click {loop_count} lần")
                except Exception as e:
                    await update.message.reply_text(f"⚠️ Lỗi click: {e}. Reload...")
                    await page.reload()
                    await asyncio.sleep(2)
            await page.reload()
            await asyncio.sleep(1)

        await browser.close()
        is_running = False
        await update.message.reply_text("🛑 Đã dừng.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, browser
    is_running = False
    if browser:
        try:
            await browser.close()
        except:
            pass
    await update.message.reply_text("🛑 Đã gửi lệnh dừng.")

# === KHỞI TẠO BOT ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Lấy URL public của Render (tự động cấp)
    render_url = os.getenv("RENDER_EXTERNAL_URL")
    if render_url:
    # ... webhook
else:
    app.run_polling(timeout=30, drop_pending_updates=True)

if __name__ == "__main__":
    main()
