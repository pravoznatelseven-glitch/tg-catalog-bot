import json
import os
import time
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "8368706232:AAEJUi3_cFMmQVjWsiJQ27uReyyJUN87YqE"

# ===== АДМІНИ =====
ADMIN_1_ID = 6352725328
ADMIN_2_ID = 1240962419

ADMIN_1_USERNAME = "antwerp0vape"
ADMIN_2_USERNAME = "Minderalkerstap"

ADMINS = {
    "a1": {"id": ADMIN_1_ID, "username": ADMIN_1_USERNAME, "label": "Адмін 1"},
    "a2": {"id": ADMIN_2_ID, "username": ADMIN_2_USERNAME, "label": "Адмін 2"},
}

DATA_FILE = "products.json"

CATEGORIES = {
    "liquid": "🧃 Жидкість",
    "cartridge": "🔋 Картридж",
    "device": "📱 Пристрій",
}


# ================= JSON =================
def load_products() -> List[Dict[str, Any]]:
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_products(products: List[Dict[str, Any]]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)


# ================= ЛОГІКА =================
def is_admin(user_id: int) -> bool:
    return user_id in {ADMIN_1_ID, ADMIN_2_ID}


def user_admin_key(user_id: int) -> str | None:
    if user_id == ADMIN_1_ID:
        return "a1"
    if user_id == ADMIN_2_ID:
        return "a2"
    return None


def status_emoji(val: bool) -> str:
    return "🟢" if val else "🔴"


def admin_link(key: str) -> str:
    username = ADMINS[key]["username"]
    label = ADMINS[key]["label"]
    return f'<a href="https://t.me/{username}">@{username}</a>'


def build_caption(p: Dict[str, Any]) -> str:
    s1 = bool(p["stock"].get("a1", False))
    s2 = bool(p["stock"].get("a2", False))
    cat_name = CATEGORIES.get(p.get("category", ""), "")

    return (
        f"<b>{p['name']}</b>\n"
        f"{p.get('desc','')}\n"
        f"<i>{cat_name}</i>\n\n"
        f"<b>Наявність:</b>\n"
        f"{status_emoji(s1)} {admin_link('a1')}\n"
        f"{status_emoji(s2)} {admin_link('a2')}"
    )


def visible_for_users(p: Dict[str, Any]) -> bool:
    # Показ тільки якщо є хоча б у одного
    return bool(p["stock"].get("a1") or p["stock"].get("a2"))


def make_product_id() -> str:
    return str(int(time.time() * 1000))


def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧃 Жидкість", callback_data="cat:liquid")],
        [InlineKeyboardButton("🔋 Картридж", callback_data="cat:cartridge")],
        [InlineKeyboardButton("📱 Пристрій", callback_data="cat:device")],
    ])


# ================= СТАРТ =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Оберіть категорію:",
        reply_markup=start_keyboard()
    )
# ================= ДОДАТИ ТОВАР =================
async def add_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    context.user_data["awaiting_add"] = True
    await update.message.reply_text(
        "Надішли фото з підписом:\n"
        "Назва | опис | категорія\n\n"
        "Категорії: liquid / cartridge / device"
    )


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.user_data.get("awaiting_add"):
        return

    caption = (update.message.caption or "").strip()
    parts = [p.strip() for p in caption.split("|")]

    if len(parts) != 3:
        await update.message.reply_text("❗ Формат: Назва | опис | категорія")
        return

    name, desc, category = parts
    category = category.lower()

    if category not in CATEGORIES:
        await update.message.reply_text("❗ Категорія: liquid / cartridge / device")
        return

    file_id = update.message.photo[-1].file_id

    products = load_products()
    products.append({
        "id": make_product_id(),
        "name": name,
        "desc": desc,
        "category": category,
        "file_id": file_id,
        "stock": {"a1": False, "a2": False},
    })
    save_products(products)

    context.user_data["awaiting_add"] = False
    await update.message.reply_text("✅ Товар додано.")


# ================= ПОКАЗ КАТЕГОРІЇ =================
async def send_category(chat_id, bot, category, viewer_id):
    products = load_products()
    admin_view = is_admin(viewer_id)

    sent_any = False

    for i, p in enumerate(products):
        if p.get("category") != category:
            continue

        if not admin_view and not visible_for_users(p):
            continue

        buttons = []

        # Кнопки "Написати продавцю"
        if p["stock"].get("a1"):
            buttons.append([
                InlineKeyboardButton(
                    "🟢 Написати @antwerp0vape",
                    url="https://t.me/antwerp0vape"
                )
            ])

        if p["stock"].get("a2"):
            buttons.append([
                InlineKeyboardButton(
                    "🟢 Написати @Minderalkerstap",
                    url="https://t.me/Minderalkerstap"
                )
            ])

        # Адмін-кнопка
        if admin_view:
            key = user_admin_key(viewer_id)
            cur = bool(p["stock"].get(key, False))
            buttons.append([
                InlineKeyboardButton(
                    f"Моя наявність: {status_emoji(cur)} (змінити)",
                    callback_data=f"toggle:{key}:{i}"
                )
            ])
        if admin_view:
    buttons.append([
        InlineKeyboardButton("🗑 Видалити товар", callback_data=f"delete:{i}")
    ])

        markup = InlineKeyboardMarkup(buttons) if buttons else None

        await bot.send_document(
            chat_id=chat_id,
            document=p["file_id"],
            caption=build_caption(p),
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )

        sent_any = True

    if not sent_any:
        await bot.send_message(chat_id, "У цій категорії немає товарів.")

# ================= КНОПКИ =================
async def on_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat_id

    if query.data.startswith("cat:"):
        category = query.data.split(":")[1]
        await send_category(chat_id, context.bot, category, user_id)

    if query.data.startswith("toggle:"):
        _, key, idx = query.data.split(":")
        idx = int(idx)

        if user_admin_key(user_id) != key:
            return

        products = load_products()
        products[idx]["stock"][key] = not products[idx]["stock"].get(key)
        save_products(products)

        await query.answer("✅ Оновлено", show_alert=True)


# ================= MAIN =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add_cmd))
app.add_handler(MessageHandler(filters.PHOTO, on_photo))
app.add_handler(CallbackQueryHandler(on_buttons))


app.run_polling()


