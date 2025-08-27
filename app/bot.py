import os
import sqlite3
from contextlib import closing
from typing import Tuple, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from telegram.constants import ChatMemberStatus

DB_PATH = os.getenv("DB_PATH", "./data/entries.db")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# ---------------------- DB helpers ----------------------

def get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db() -> None:
    with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                name    TEXT    NOT NULL,
                count   INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id, name)
            );
            """
        )
        conn.commit()


# ---------------------- UI rendering ----------------------


def build_list_and_keyboard(chat_id: int) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
    with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            "SELECT id, name, count FROM entries WHERE chat_id = ? ORDER BY count DESC, name ASC",
            (chat_id,),
        )
        rows = cur.fetchall()

    if not rows:
        return "No entries yet.", None

    lines = ["📋 List:"]
    keyboard = []
    for entry_id, name, count in rows:
        lines.append(f"{name}: {count}")
        keyboard.append(
            [InlineKeyboardButton(f"👍 {name} ({count})", callback_data=f"up:{entry_id}")]
        )

    return "\n".join(lines), InlineKeyboardMarkup(keyboard)


# ---------------------- Commands ----------------------


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await help_command(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Commands:\n"
        "/add <text> – add a new entry\n"
        "/list – show list with buttons\n"
        "/up <text> – increment an entry (alternative to buttons)\n"
        "/top – show top entries\n"
        "/reset – reset list (admins only)\n"
        "/help – show this help\n"
    )
    await update.message.reply_text(text)


async def add_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify an entry: /add <text>")
        return

    entry = " ".join(context.args).strip().lower()
    chat_id = update.effective_chat.id

    if not entry:
        await update.message.reply_text("Entry cannot be empty.")
        return

    try:
        with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
            cur.execute(
                "INSERT INTO entries (chat_id, name, count) VALUES (?, ?, 0)",
                (chat_id, entry),
            )
            conn.commit()
        await update.message.reply_text(f"Entry '{entry}' added.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"'{entry}' already exists.")


async def list_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text, keyboard = build_list_and_keyboard(chat_id)
    await update.message.reply_text(text, reply_markup=keyboard)


async def up_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please specify an entry: /up <text>")
        return

    entry = " ".join(context.args).strip().lower()
    chat_id = update.effective_chat.id

    with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            "SELECT id, count FROM entries WHERE chat_id = ? AND name = ?",
            (chat_id, entry),
        )
        row = cur.fetchone()
        if not row:
            await update.message.reply_text(
                f"'{entry}' does not exist yet. Add it with /add."
            )
            return
        entry_id, count = row
        new_count = count + 1
        cur.execute("UPDATE entries SET count = ? WHERE id = ?", (new_count, entry_id))
        conn.commit()

    text, keyboard = build_list_and_keyboard(chat_id)
    await update.message.reply_text(text, reply_markup=keyboard)


async def top_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute(
            "SELECT name, count FROM entries WHERE chat_id = ? ORDER BY count DESC, name ASC LIMIT 3",
            (chat_id,),
        )
        rows = cur.fetchall()

    if not rows:
        await update.message.reply_text("No entries yet.")
        return

    lines = ["🏆 Top entries:"]
    for i, (name, count) in enumerate(rows,  start=1):
        lines.append(f"{i}. {name}: {count}")
    await update.message.reply_text("\n".join(lines))


async def reset_entries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type in ("group", "supergroup"):
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
            await update.message.reply_text("❌ Only admins can reset the list.")
            return

    with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
        cur.execute("DELETE FROM entries WHERE chat_id = ?", (chat.id,))
        conn.commit()

    await update.message.reply_text("✅ List has been reset.")


# ---------------------- Callback buttons ----------------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("up:"):
        entry_id = int(data.split(":", 1)[1])
        with closing(get_conn()) as conn, closing(conn.cursor()) as cur:
            cur.execute(
                "SELECT chat_id, name, count FROM entries WHERE id = ?",
                (entry_id,),
            )
            row = cur.fetchone()
            if not row:
                await query.edit_message_text("❌ Entry not found.")
                return
            chat_id, name, count = row
            new_count = count + 1
            cur.execute("UPDATE entries SET count = ? WHERE id = ?", (new_count, entry_id))
            conn.commit()

        text, keyboard = build_list_and_keyboard(chat_id)
        await query.edit_message_text(text, reply_markup=keyboard)


# ---------------------- Bot setup ----------------------

async def set_commands(application: Application):
    commands = [
        BotCommand("add", "Add a new entry"),
        BotCommand("list", "Show list with counters"),
        BotCommand("up", "Increment an entry"),
        BotCommand("top", "Show top entries"),
        BotCommand("reset", "Reset list (admins only)"),
        BotCommand("help", "Show help"),
    ]
    await application.bot.set_my_commands(commands)


def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN env var is not set")

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("add", add_entry))
    app.add_handler(CommandHandler("list", list_entries))
    app.add_handler(CommandHandler("up", up_entry))
    app.add_handler(CommandHandler("top", top_entry))
    app.add_handler(CommandHandler("reset", reset_entries))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.post_init = set_commands
    return app


def main() -> None:
    app = build_app()
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
