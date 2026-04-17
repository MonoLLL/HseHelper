import asyncio
import logging
import os
import tempfile
import httpx
import tempfile
from pathlib import Path
from aiogram.types import FSInputFile


from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN
from api import search_faq, create_incoming, list_incoming
from states import AskFlow
from keyboards import faq_not_found_kb, files_ready_kb, main_kb

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


def format_incoming(x: dict) -> str:
    parts = [
        f"<b>Статус:</b> {x.get('status', '-')}",
        f"<b>Дата:</b> {x.get('created_at', '-')}",
        f"<b>Вопрос:</b> {x.get('text', '-')}",
    ]

    if x.get("answer"):
        parts.append(f"<b>Ответ:</b> {x['answer']}")

    if x.get("attachments"):
        names = [a.get("original_name", "файл") for a in x["attachments"]]
        if names:
            parts.append("<b>Файлы:</b> " + ", ".join(names))

    return "\n".join(parts)


@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот учебного офиса.\n\n"
        "Я умею:\n"
        "• искать ответ в базе знаний\n"
        "• отправлять обращение в учебный офис\n"
        "• показывать твои обращения\n\n"
        "Просто напиши свой вопрос или используй /my"
    )
    await message.answer(text, reply_markup=main_kb())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start — начать работу\n"
        "/help — помощь\n"
        "/my — мои обращения\n\n"
        "Также можно просто написать вопрос."
    )

async def send_attachments_to_user(message: Message, attachments: list[dict]):
    if not attachments:
        return

    async with httpx.AsyncClient(timeout=60) as client:
        for a in attachments:
            url = a.get("url")
            name = a.get("original_name", "file")
            mime_type = a.get("mime_type", "")

            if not url:
                continue

            full_url = f"http://backend:8000{url}"
            if os.getenv("API_BASE", "").startswith("http://localhost"):
                full_url = f"http://localhost:8000{url}"

            temp_path = None

            try:
                resp = await client.get(full_url)
                resp.raise_for_status()

                suffix = Path(name).suffix or ".bin"
                fd, temp_path = tempfile.mkstemp(prefix="tg_out_", suffix=suffix)
                os.close(fd)

                with open(temp_path, "wb") as f:
                    f.write(resp.content)

                tg_file = FSInputFile(temp_path, filename=name)

                if mime_type.startswith("image/"):
                    await message.answer_photo(
                        photo=tg_file,
                        caption=name,
                    )
                else:
                    await message.answer_document(
                        document=tg_file,
                        caption=name,
                    )

            except Exception as e:
                # без HTML-символов из repr(e)
                await message.answer(
                    f"Не удалось отправить файл: {name}\n{type(e).__name__}"
                )
            finally:
                if temp_path:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass



@dp.message(Command("my"))
async def cmd_my(message: Message):
    tg_id = str(message.from_user.id)
    items = await list_incoming(tg_id)

    if not items:
        await message.answer("У тебя пока нет обращений.")
        return

    for x in items[:10]:
        await message.answer(format_incoming(x))

        staff_attachments = [a for a in x.get("attachments", []) if a.get("uploader_role") == "staff"]
        if staff_attachments:
            await message.answer("Прикреплённые файлы сотрудника:")
            await send_attachments_to_user(message, staff_attachments)


@dp.callback_query(F.data == "my_incoming")
async def cb_my_incoming(callback: CallbackQuery):
    tg_id = str(callback.from_user.id)
    items = await list_incoming(tg_id)

    if not items:
        await callback.message.answer("У тебя пока нет обращений.")
        await callback.answer()
        return

    for x in items[:10]:
        await callback.message.answer(format_incoming(x))

        staff_attachments = [a for a in x.get("attachments", []) if a.get("uploader_role") == "staff"]
        if staff_attachments:
            await callback.message.answer("Прикреплённые файлы сотрудника:")
            await send_attachments_to_user(callback.message, staff_attachments)
    await callback.answer()


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_question(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return

    try:
        items = await search_faq(query)
    except Exception as e:
        await message.answer(f"Ошибка поиска: {e}")
        return

    if items:
        top = items[0]
        question = top.get("question") or "Найденный ответ"
        short_answer = top.get("short_answer") or top.get("full_answer") or "Ответ не найден"

        text = f"<b>{question}</b>\n\n{short_answer}"
        await message.answer(text)

        if len(items) > 1:
            others = items[1:4]
            more = ["\n<b>Похожие ответы:</b>"]
            for x in others:
                more.append(f"• {x.get('question', 'Без названия')}")
            await message.answer("\n".join(more))
        return

    await state.clear()
    await state.update_data(question_text=query, files=[])
    await state.set_state(AskFlow.waiting_for_confirm)

    await message.answer(
        "Точного ответа не найдено. Можно сразу отправить обращение или сначала прикрепить файлы.",
        reply_markup=faq_not_found_kb(),
    )


@dp.callback_query(F.data == "attach_files")
async def cb_attach_files(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AskFlow.waiting_for_files)
    await callback.message.answer(
        "Пришли один или несколько файлов сообщениями.\n"
        "Когда закончишь — нажми «Готово, отправить».",
        reply_markup=files_ready_kb(),
    )
    await callback.answer()


@dp.message(AskFlow.waiting_for_files, F.document)
async def handle_document(message: Message, state: FSMContext):
    doc = message.document
    tg_file = await bot.get_file(doc.file_id)

    suffix = os.path.splitext(doc.file_name or "")[1]
    fd, temp_path = tempfile.mkstemp(prefix="tgdoc_", suffix=suffix)
    os.close(fd)

    await bot.download(tg_file, destination=temp_path)

    data = await state.get_data()
    files = data.get("files", [])
    files.append(
        {
            "path": temp_path,
            "filename": doc.file_name or "document.bin",
            "mime_type": doc.mime_type or "application/octet-stream",
        }
    )
    await state.update_data(files=files)

    await message.answer(
        f"Файл «{doc.file_name}» добавлен.\n"
        f"Сейчас прикреплено: {len(files)}",
        reply_markup=files_ready_kb(),
    )


@dp.message(AskFlow.waiting_for_files, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    tg_file = await bot.get_file(photo.file_id)

    fd, temp_path = tempfile.mkstemp(prefix="tgphoto_", suffix=".jpg")
    os.close(fd)

    await bot.download(tg_file, destination=temp_path)

    data = await state.get_data()
    files = data.get("files", [])
    files.append(
        {
            "path": temp_path,
            "filename": f"photo_{photo.file_unique_id}.jpg",
            "mime_type": "image/jpeg",
        }
    )
    await state.update_data(files=files)

    await message.answer(
        f"Фото добавлено.\n"
        f"Сейчас прикреплено: {len(files)}",
        reply_markup=files_ready_kb(),
    )


@dp.callback_query(F.data == "send_incoming_now")
async def cb_send_incoming(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    question_text = data.get("question_text")
    files = data.get("files", [])

    if not question_text:
        await callback.message.answer("Не удалось получить текст вопроса.")
        await callback.answer()
        await state.clear()
        return

    try:
        row = await create_incoming(
            text=question_text,
            telegram_user_id=str(callback.from_user.id),
            file_paths=files,
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка отправки обращения: {e}")
        await callback.answer()
        await state.clear()
        return

    await callback.message.answer(
        f"Обращение отправлено.\n\n"
        f"<b>ID:</b> {row.get('id')}\n"
        f"<b>Статус:</b> {row.get('status')}"
    )
    await callback.answer()
    await state.clear()


@dp.callback_query(F.data == "cancel_incoming")
async def cb_cancel_incoming(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    for item in data.get("files", []):
        try:
            os.remove(item["path"])
        except OSError:
            pass

    await state.clear()
    await callback.message.answer("Отправка обращения отменена.")
    await callback.answer()


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())