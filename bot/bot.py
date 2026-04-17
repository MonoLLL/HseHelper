import os, asyncio
from aiogram import Bot, Dispatcher, types
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import httpx

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE = os.getenv("BACKEND_BASE_URL","http://backend:8000")

bot = Bot(TOKEN)
dp = Dispatcher()

def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Сессия", callback_data="cat:session"),
         InlineKeyboardButton(text="💳 Оплата", callback_data="cat:payment")],
        [InlineKeyboardButton(text="🏠 Общежитие", callback_data="cat:dorm"),
         InlineKeyboardButton(text="📅 Расписание", callback_data="cat:schedule")]
    ])

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Привет! Я помогу быстро найти информацию по учёбе. Спроси меня или выбери тему ниже.", reply_markup=main_keyboard())

@dp.message()
async def handle_query(m: types.Message):
    q = (m.text or "").strip()
    if not q:
        await m.answer("Напиши вопрос, например: 'когда оплата'")
        return

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/api/search", params={"q": q})
        items = r.json()

    if not items:
        await m.answer("Пока не нашёл точного ответа. Попробуй уточнить формулировку или выбери тему на клавиатуре.")
        return

    top = items[0]
    btn = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"faq:{top['id']}")]
        ]
    )

    text = f"👉 {top['question']}\n{top['short_answer']}"
    await m.answer(text, reply_markup=btn)

@dp.callback_query(F.data.startswith("faq:"))
async def on_faq(c: CallbackQuery):
    fid = c.data.split(":", 1)[1]
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/api/faq/{fid}")
        faq = r.json()
    text = f"**{faq['question']}**\n\n{faq['full_answer']}"
    await c.message.edit_text(text, parse_mode="Markdown")
    await c.answer()  # подтверждаем клик

@dp.callback_query(F.data.startswith("cat:"))
async def on_category(c: CallbackQuery):
    topic = c.data.split(":", 1)[1]
    mapping = {
        "payment": "оплата",
        "session": "сессия",
        "dorm": "общежитие",
        "schedule": "расписание",
    }
    q = mapping.get(topic, topic)

    async with httpx.AsyncClient() as client:
        r = await client.get(f"{API_BASE}/api/search", params={"q": q})
        items = r.json()

    if not items:
        await c.message.answer("Пока нет готового ответа по этой теме. Попробуй задать вопрос словами.")
        await c.answer()
        return

    top = items[0]
    btn = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подробнее", callback_data=f"faq:{top['id']}")]
        ]
    )
    text = f"👉 {top['question']}\n{top['short_answer']}"
    await c.message.answer(text, reply_markup=btn)
    await c.answer()  # подтверждаем клик

async def main(): await dp.start_polling(bot)
if __name__ == "__main__": asyncio.run(main())
