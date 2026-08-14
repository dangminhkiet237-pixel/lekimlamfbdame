import asyncio
import json
import random
import os
import time
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import nest_asyncio

nest_asyncio.apply()

# === THÔNG TIN CỐ ĐỊNH ===
BOT_TOKEN = "8663622587:AAFIO8Mvr6hLCqyKvdsD_fQ-hNRxwlyKjNM"
TARGET_URL = "https://www.facebook.com/profile.php?id=61557730067730"

FB_COOKIES = [ ... ]  # (giữ nguyên danh sách cookie của bạn)
FB_USER = "0347999535"
FB_PASS = "qhmaicute"
PROXY = None

COORDINATES = []
is_running = False
browser = None
total_clicks = 0
start_time = None

# === HÀM XỬ LÝ FILE JSON ===
def parse_coord_json(content: bytes) -> list:
    data = json.loads(content)
    if not isinstance(data, list):
        raise ValueError("Dữ liệu không phải mảng")
    return [{"x": item["x"], "y": item["y"]} for item in data if "x" in item and "y" in item]

# === LỆNH START ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Bot Dame Auto FB*\n"
        "📤 Gửi file JSON tọa độ (có key x, y)\n"
        "🔗 /settarget <url> – Đổi URL mục tiêu\n"
        "🔍 /showtarget – Xem URL hiện tại\n"
        "📊 /status – Xem trạng thái tấn công\n"
        "▶️ /attack – Bắt đầu click\n"
        "⏹ /stop   – Dừng ngay",
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
    global is_running, browser, total_clicks, start_time, TARGET_URL
    if not COORDINATES:
        await update.message.reply_text("❌ Chưa có tọa độ. Hãy gửi file JSON trước.")
        return
    if is_running:
        await update.message.reply_text("⚠️ Bot đang chạy rồi!")
        return

    is_running = True
    total_clicks = 0
    start_time = time.time()
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

        browser = await p.chromium.launch(**launch_opts)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        await stealth_async(page)

        # === ĐĂNG NHẬP BẰNG COOKIE ===
        try:
            cookies = [{"name": c["name"], "value": c["value"], "domain": c["domain"], "path": c.get("path", "/"), "secure": c.get("secure", True)} for c in FB_COOKIES]
            await context.add_cookies(cookies)
            await page.goto("https://facebook.com", timeout=60000)
            if "login" in page.url:
                await update.message.reply_text("⚠️ Cookie hết hạn, thử đăng nhập bằng user/pass...")
                await page.fill('input[name="email"]', FB_USER)
                await page.fill('input[name="pass"]', FB_PASS)
                await page.click('button[name="login"]')
                await page.wait_for_timeout(5000)
            await page.wait_for_selector('div[role="main"]', timeout=15000)
            await update.message.reply_text("✅ Đăng nhập thành công.")
            
            # === ĐIỀU HƯỚNG ĐẾN URL MỤC TIÊU ===
            await page.goto(TARGET_URL, timeout=60000)
            await page.wait_for_load_state("networkidle", timeout=10000)
            await update.message.reply_text(f"✅ Đã vào trang mục tiêu: {TARGET_URL}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Lỗi đăng nhập hoặc điều hướng: {e}")
            await browser.close()
            is_running = False
            return

        # === VÒNG LẶP CLICK VỚI BÁO CÁO ===
        last_report_time = time.time()
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
                    
                    # Gửi báo cáo mỗi 100 click hoặc mỗi 60 giây
                    if loop_count % 100 == 0 or (time.time() - last_report_time) >= 60:
                        elapsed = int(time.time() - start_time)
                        m, s = divmod(elapsed, 60)
                        h, m = divmod(m, 60)
                        await update.message.reply_text(
                            f"📊 *Báo cáo*\n"
                            f"🖱️ Đã click: {total_clicks}\n"
                            f"⏱️ Thời gian: {h:02d}:{m:02d}:{s:02d}\n"
                            f"🎯 Mục tiêu: {TARGET_URL}",
                            parse_mode="Markdown"
                        )
                        last_report_time = time.time()
                except Exception as e:
                    await update.message.reply_text(f"⚠️ Lỗi click: {e}. Reload...")
                    await page.reload()
                    await asyncio.sleep(2)
            # Refresh sau mỗi vòng để giải phóng RAM
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

# === KHỞI TẠO BOT ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("settarget", set_target))
    app.add_handler(CommandHandler("showtarget", show_target))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🤖 Bot đang chạy (polling)...")
    app.run_polling(timeout=30, drop_pending_updates=True)

if __name__ == "__main__":
    main()
