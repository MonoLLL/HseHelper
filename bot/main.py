import asyncio
import html
import logging
import os
import tempfile
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from api import (
    append_incoming_message,
    close_incoming,
    create_incoming,
    list_incoming,
    search_faq,
)
from config import BOT_TOKEN
from keyboards import dialog_draft_kb, faq_not_found_kb, files_ready_kb, incoming_actions_kb, main_kb
from states import AskFlow


logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


def clean(value) -> str:
    return html.escape(str(value or "-"))


def status_label(status: str) -> str:
    return {
        "new": "Новое",
        "in_progress": "В работе",
        "done": "Закрыто",
    }.get(status, status or "-")


def sender_label(role: str) -> str:
    return "Вы" if role == "student" else "Учебный офис"


def format_incoming(x: dict) -> str:
    parts = [
        f"<b>Тема обращения:</b> {clean(x.get('text'))}",
        f"<b>Статус:</b> {clean(status_label(x.get('status')))}",
        f"<b>Создано:</b> {clean(x.get('created_at'))}",
    ]

    messages = x.get("messages") or []
    if messages:
        parts.append("")
        parts.append("<b>Диалог:</b>")
        for index, message in enumerate(messages[-20:], start=max(1, len(messages) - 19)):
            header = f"<b>{clean(sender_label(message.get('sender_role')))}</b> ({clean(message.get('created_at'))})"
            parts.append(f"{index}. {header}")

            if message.get("text"):
                parts.append(clean(message["text"]))

            attachments = message.get("attachments") or []
            if attachments:
                names = ", ".join(clean(item.get("original_name", "file")) for item in attachments)
                parts.append(f"<i>Файлы:</i> {names}")

            parts.append("")
    else:
        parts.append(f"<b>Вопрос:</b> {clean(x.get('text'))}")

    closed_at = x.get("closed_at")
    if closed_at:
        parts.append(f"<b>Закрыто:</b> {clean(closed_at)}")

    return "\n".join(parts).strip()


def build_dialog_draft_status(data: dict) -> str:
    draft_text = (data.get("draft_text") or "").strip()
    files = data.get("files", [])

    parts = ["Черновик ответа обновлен."]
    if draft_text:
        preview = draft_text if len(draft_text) <= 500 else f"{draft_text[:500]}..."
        parts.append("")
        parts.append("<b>Текст:</b>")
        parts.append(clean(preview))

    parts.append("")
    parts.append(f"<b>Файлов:</b> {len(files)}")
    parts.append("Когда все готово, нажмите «Отправить сообщение».")
    return "\n".join(parts)


async def cleanup_state_files(state: FSMContext):
    data = await state.get_data()
    for item in data.get("files", []):
        try:
            os.remove(item["path"])
        except OSError:
            pass


async def show_incoming_list(target_message: Message, telegram_user_id: str):
    items = await list_incoming(telegram_user_id)

    if not items:
        await target_message.answer("У тебя пока нет обращений.")
        return

    for item in items[:10]:
        markup = incoming_actions_kb(str(item["id"]), item.get("status") == "done")
        await target_message.answer(format_incoming(item), reply_markup=markup)


async def append_file_to_state(state: FSMContext, file_info: dict):
    data = await state.get_data()
    files = data.get("files", [])
    files.append(file_info)
    await state.update_data(files=files)
    return files


@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот учебного офиса.\n\n"
        "Я умею:\n"
        "• искать ответ в базе знаний\n"
        "• отправлять обращение в учебный офис\n"
        "• показывать твои обращения и продолжать диалог\n\n"
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


@dp.message(Command("my"))
async def cmd_my(message: Message):
    await show_incoming_list(message, str(message.from_user.id))


@dp.callback_query(F.data == "my_incoming")
async def cb_my_incoming(callback: CallbackQuery):
    await show_incoming_list(callback.message, str(callback.from_user.id))
    await callback.answer()


@dp.message(AskFlow.waiting_for_dialog_draft, F.text & ~F.text.startswith("/"))
async def handle_dialog_text(message: Message, state: FSMContext):
    data = await state.get_data()
    current = (data.get("draft_text") or "").strip()
    next_part = message.text.strip()
    draft_text = f"{current}\n{next_part}".strip() if current else next_part
    await state.update_data(draft_text=draft_text)

    updated = await state.get_data()
    await message.answer(build_dialog_draft_status(updated), reply_markup=dialog_draft_kb())


@dp.message(AskFlow.waiting_for_dialog_draft, F.document)
async def handle_dialog_document(message: Message, state: FSMContext):
    document = message.document
    tg_file = await bot.get_file(document.file_id)

    suffix = os.path.splitext(document.file_name or "")[1]
    fd, temp_path = tempfile.mkstemp(prefix="tgdoc_", suffix=suffix)
    os.close(fd)

    await bot.download(tg_file, destination=temp_path)

    files = await append_file_to_state(
        state,
        {
            "path": temp_path,
            "filename": document.file_name or "document.bin",
            "mime_type": document.mime_type or "application/octet-stream",
        },
    )

    await message.answer(
        f"Файл «{clean(document.file_name or 'document.bin')}» добавлен.\n"
        f"Сейчас прикреплено: {len(files)}",
        reply_markup=dialog_draft_kb(),
    )


@dp.message(AskFlow.waiting_for_dialog_draft, F.photo)
async def handle_dialog_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    tg_file = await bot.get_file(photo.file_id)

    fd, temp_path = tempfile.mkstemp(prefix="tgphoto_", suffix=".jpg")
    os.close(fd)

    await bot.download(tg_file, destination=temp_path)

    files = await append_file_to_state(
        state,
        {
            "path": temp_path,
            "filename": f"photo_{photo.file_unique_id}.jpg",
            "mime_type": "image/jpeg",
        },
    )

    await message.answer(
        f"Фото добавлено.\nСейчас прикреплено: {len(files)}",
        reply_markup=dialog_draft_kb(),
    )


@dp.callback_query(F.data.startswith("reply_incoming:"))
async def cb_reply_incoming(callback: CallbackQuery, state: FSMContext):
    incoming_id = callback.data.split(":", 1)[1]
    items = await list_incoming(str(callback.from_user.id))
    selected = next((item for item in items if str(item.get("id")) == incoming_id), None)

    await cleanup_state_files(state)
    await state.set_state(AskFlow.waiting_for_dialog_draft)
    await state.set_data(
        {
            "draft_mode": "reply",
            "incoming_id": incoming_id,
            "draft_text": "",
            "files": [],
        }
    )

    if selected:
        await callback.message.answer(format_incoming(selected))

    await callback.message.answer(
        "Отправь текст сообщения, фото или документы. Можно прислать несколько сообщений подряд, "
        "я соберу их в один ответ. Когда закончишь, нажми «Отправить сообщение».",
        reply_markup=dialog_draft_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data == "send_dialog_message")
async def cb_send_dialog_message(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    incoming_id = data.get("incoming_id")
    draft_text = (data.get("draft_text") or "").strip()
    files = data.get("files", [])

    if not incoming_id:
        await callback.message.answer("Не удалось определить обращение для ответа.")
        await callback.answer()
        await state.clear()
        return

    if not draft_text and not files:
        await callback.message.answer("Добавь текст сообщения или прикрепи хотя бы один файл.")
        await callback.answer()
        return

    try:
        row = await append_incoming_message(
            incoming_id=incoming_id,
            telegram_user_id=str(callback.from_user.id),
            text=draft_text,
            file_paths=files,
        )
    except Exception as exc:
        await callback.message.answer(f"Ошибка отправки сообщения: {clean(exc)}")
        await callback.answer()
        return

    await callback.message.answer("Сообщение отправлено в диалог.")
    await callback.message.answer(
        format_incoming(row),
        reply_markup=incoming_actions_kb(str(row["id"]), row.get("status") == "done"),
    )
    await callback.answer()
    await state.clear()


@dp.callback_query(F.data == "cancel_dialog_message")
async def cb_cancel_dialog_message(callback: CallbackQuery, state: FSMContext):
    await cleanup_state_files(state)
    await state.clear()
    await callback.message.answer("Черновик ответа отменен.")
    await callback.answer()


@dp.callback_query(F.data.startswith("close_incoming:"))
async def cb_close_incoming(callback: CallbackQuery):
    incoming_id = callback.data.split(":", 1)[1]

    try:
        row = await close_incoming(incoming_id, str(callback.from_user.id))
    except Exception as exc:
        await callback.message.answer(f"Не удалось закрыть обращение: {clean(exc)}")
        await callback.answer()
        return

    await callback.message.answer("Диалог закрыт. Если появятся новые вопросы, можно создать новое обращение.")
    await callback.message.answer(format_incoming(row))
    await callback.answer()


@dp.message(F.text & ~F.text.startswith("/"))
async def handle_question(message: Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        return

    try:
        items = await search_faq(query)
    except Exception as exc:
        await message.answer(f"Ошибка поиска: {clean(exc)}")
        return

    if items:
        top = items[0]
        question = top.get("question") or "Найденный ответ"
        short_answer = top.get("short_answer") or top.get("full_answer") or "Ответ не найден"

        await message.answer(f"<b>{clean(question)}</b>\n\n{clean(short_answer)}")

        if len(items) > 1:
            others = items[1:4]
            lines = ["<b>Похожие ответы:</b>"]
            for item in others:
                lines.append(f"• {clean(item.get('question', 'Без названия'))}")
            await message.answer("\n".join(lines))
        return

    await cleanup_state_files(state)
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
        "Пришли один или несколько файлов сообщениями. Когда закончишь, нажми «Готово, отправить».",
        reply_markup=files_ready_kb(),
    )
    await callback.answer()


@dp.message(AskFlow.waiting_for_files, F.document)
async def handle_document(message: Message, state: FSMContext):
    document = message.document
    tg_file = await bot.get_file(document.file_id)

    suffix = os.path.splitext(document.file_name or "")[1]
    fd, temp_path = tempfile.mkstemp(prefix="tgdoc_", suffix=suffix)
    os.close(fd)

    await bot.download(tg_file, destination=temp_path)

    files = await append_file_to_state(
        state,
        {
            "path": temp_path,
            "filename": document.file_name or "document.bin",
            "mime_type": document.mime_type or "application/octet-stream",
        },
    )

    await message.answer(
        f"Файл «{clean(document.file_name or 'document.bin')}» добавлен.\n"
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

    files = await append_file_to_state(
        state,
        {
            "path": temp_path,
            "filename": f"photo_{photo.file_unique_id}.jpg",
            "mime_type": "image/jpeg",
        },
    )

    await message.answer(
        f"Фото добавлено.\nСейчас прикреплено: {len(files)}",
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
    except Exception as exc:
        await callback.message.answer(f"Ошибка отправки обращения: {clean(exc)}")
        await callback.answer()
        await state.clear()
        return

    await callback.message.answer("Обращение отправлено.")
    await callback.message.answer(
        format_incoming(row),
        reply_markup=incoming_actions_kb(str(row["id"]), row.get("status") == "done"),
    )
    await callback.answer()
    await state.clear()


@dp.callback_query(F.data == "cancel_incoming")
async def cb_cancel_incoming(callback: CallbackQuery, state: FSMContext):
    await cleanup_state_files(state)
    await state.clear()
    await callback.message.answer("Отправка обращения отменена.")
    await callback.answer()


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is empty")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
