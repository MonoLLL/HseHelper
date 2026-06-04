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
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from api import (
    append_incoming_message,
    build_public_url,
    close_incoming,
    create_incoming,
    download_attachment,
    get_registered_user,
    list_incoming,
    login_telegram_with_site_account,
    register_user as api_register_user,
    search_faq,
    set_site_credentials,
)
from config import BOT_TOKEN
from keyboards import (
    dialog_draft_kb,
    faq_not_found_kb,
    files_ready_kb,
    incoming_actions_kb,
    main_kb,
    registration_cancel_kb,
)
from states import AskFlow, RegistrationFlow, SiteAccessFlow, SiteLoginFlow


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
        await send_incoming_attachments(target_message, item)


def message_attachment_groups(item: dict):
    messages = item.get("messages") or []
    if messages:
        start_index = max(1, len(messages) - 19)
        for index, message in enumerate(messages[-20:], start=start_index):
            attachments = message.get("attachments") or []
            if attachments:
                yield index, attachments
        return

    attachments = item.get("attachments") or []
    if attachments:
        yield None, attachments


async def send_incoming_attachments(target_message: Message, item: dict):
    for message_index, attachments in message_attachment_groups(item):
        for attachment in attachments:
            await send_attachment(target_message, attachment, message_index)


async def send_attachment(target_message: Message, attachment: dict, message_index: int | None = None):
    filename = str(attachment.get("original_name") or "file")
    path = attachment.get("url")
    caption_prefix = f"Файл из сообщения {message_index}" if message_index else "Файл"
    caption = f"{caption_prefix}: {clean(filename)}"

    try:
        content, _content_type = await download_attachment(path)
        input_file = BufferedInputFile(content, filename=filename)
        await target_message.answer_document(input_file, caption=caption)
    except Exception:
        logging.exception("Failed to send attachment")
        public_url = build_public_url(path)
        if public_url:
            await target_message.answer(
                f"{caption_prefix}: <a href=\"{clean(public_url)}\">{clean(filename)}</a>"
            )
        else:
            await target_message.answer(caption)


async def append_file_to_state(state: FSMContext, file_info: dict):
    data = await state.get_data()
    files = data.get("files", [])
    files.append(file_info)
    await state.update_data(files=files)
    return files


def format_profile(user: dict) -> str:
    parts = [
        "<b>Твои данные:</b>",
        f"ФИО: {clean(user.get('full_name'))}",
        f"Факультет: {clean(user.get('faculty'))}",
        f"Курс: {clean(user.get('course'))}",
        f"Группа: {clean(user.get('group_name'))}",
    ]
    if user.get("email"):
        parts.append(f"Email: {clean(user.get('email'))}")
    return "\n".join(parts)


def user_has_site_credentials(user: dict | None) -> bool:
    return bool(user and user.get("email"))


def main_keyboard_for(user: dict | None):
    return main_kb(user is not None, user_has_site_credentials(user))


async def load_registered_user(telegram_user_id: str):
    try:
        return await get_registered_user(telegram_user_id)
    except Exception:
        logging.exception("Failed to load registered user")
        return None


async def ask_registration(target_message: Message):
    await target_message.answer(
        "Чтобы отправлять обращения в учебный офис, сначала зарегистрируйся. "
        "Это займет меньше минуты.",
        reply_markup=main_keyboard_for(None),
    )


async def start_registration(message: Message, state: FSMContext):
    await cleanup_state_files(state)
    await state.clear()

    user = await load_registered_user(str(message.from_user.id))
    if user and user_has_site_credentials(user):
        await message.answer(
            "Этот Telegram уже привязан к аккаунту сайта. В боте можно использовать только этот профиль.",
            reply_markup=main_keyboard_for(user),
        )
        return

    await state.set_state(RegistrationFlow.waiting_for_full_name)
    await message.answer(
        "Начнем регистрацию.\n\nВведи ФИО полностью, например: Иванов Иван Иванович.",
        reply_markup=registration_cancel_kb(),
    )


async def start_site_login(message: Message, state: FSMContext):
    await cleanup_state_files(state)
    await state.clear()
    await state.set_state(SiteLoginFlow.waiting_for_email)
    await message.answer(
        "Введи email и пароль от аккаунта на сайте. После входа я привяжу этот Telegram к твоему профилю.\n\nСначала отправь email.",
        reply_markup=registration_cancel_kb(),
    )


async def start_site_access(message: Message, state: FSMContext):
    user = await load_registered_user(str(message.from_user.id))
    if not user:
        await message.answer("Сначала зарегистрируйся в боте или войди через аккаунт сайта командой /login.")
        return

    await cleanup_state_files(state)
    await state.clear()
    await state.set_state(SiteAccessFlow.waiting_for_email)
    await message.answer(
        "Сделаем доступ к сайту для твоего Telegram-профиля.\n\nОтправь email, который будешь использовать для входа на сайт.",
        reply_markup=registration_cancel_kb(),
    )


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await cleanup_state_files(state)
    await state.clear()

    user = await load_registered_user(str(message.from_user.id))

    text = (
        "Привет! Я бот учебного офиса.\n\n"
        "Я умею:\n"
        "• искать ответ в базе знаний\n"
        "• отправлять обращение в учебный офис\n"
        "• показывать твои обращения и продолжать диалог\n\n"
        "Просто напиши свой вопрос или используй /my"
    )
    if user:
        text = f"Привет, {clean(user.get('full_name'))}!\n\n" + text
    else:
        text += "\n\nДля отправки обращений понадобится регистрация."

    await message.answer(text, reply_markup=main_keyboard_for(user))


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Команды:\n"
        "/start — начать работу\n"
        "/register — регистрация или обновление данных\n"
        "/login — войти в боте через аккаунт сайта\n"
        "/site — сделать вход на сайт для профиля из бота\n"
        "/profile — мои данные\n"
        "/cancel — отменить текущее действие\n"
        "/help — помощь\n"
        "/my — мои обращения\n\n"
        "Также можно просто написать вопрос."
    )


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await cleanup_state_files(state)
    await state.clear()
    user = await load_registered_user(str(message.from_user.id))
    await message.answer("Действие отменено.", reply_markup=main_keyboard_for(user))


@dp.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    await start_registration(message, state)


@dp.message(Command("login"))
async def cmd_login(message: Message, state: FSMContext):
    await start_site_login(message, state)


@dp.message(Command("site"))
async def cmd_site(message: Message, state: FSMContext):
    await start_site_access(message, state)


@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await load_registered_user(str(message.from_user.id))
    if not user:
        await ask_registration(message)
        return

    await message.answer(format_profile(user), reply_markup=main_keyboard_for(user))


@dp.message(Command("my"))
async def cmd_my(message: Message):
    user = await load_registered_user(str(message.from_user.id))
    if not user:
        await ask_registration(message)
        return
    await show_incoming_list(message, str(message.from_user.id))


@dp.callback_query(F.data == "register_user")
async def cb_register_user(callback: CallbackQuery, state: FSMContext):
    await start_registration(callback.message, state)
    await callback.answer()


@dp.callback_query(F.data == "site_login")
async def cb_site_login(callback: CallbackQuery, state: FSMContext):
    await start_site_login(callback.message, state)
    await callback.answer()


@dp.callback_query(F.data == "site_access")
async def cb_site_access(callback: CallbackQuery, state: FSMContext):
    await start_site_access(callback.message, state)
    await callback.answer()


@dp.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    user = await load_registered_user(str(callback.from_user.id))
    if not user:
        await ask_registration(callback.message)
        await callback.answer()
        return

    await callback.message.answer(format_profile(user), reply_markup=main_keyboard_for(user))
    await callback.answer()


@dp.callback_query(F.data == "cancel_registration")
async def cb_cancel_registration(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    user = await load_registered_user(str(callback.from_user.id))
    await callback.message.answer("Действие отменено.", reply_markup=main_keyboard_for(user))
    await callback.answer()


@dp.callback_query(F.data == "my_incoming")
async def cb_my_incoming(callback: CallbackQuery):
    user = await load_registered_user(str(callback.from_user.id))
    if not user:
        await ask_registration(callback.message)
        await callback.answer()
        return
    await show_incoming_list(callback.message, str(callback.from_user.id))
    await callback.answer()


@dp.message(SiteLoginFlow.waiting_for_email, F.text & ~F.text.startswith("/"))
async def handle_site_login_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await state.set_state(SiteLoginFlow.waiting_for_password)
    await message.answer("Теперь отправь пароль от сайта.")


@dp.message(SiteLoginFlow.waiting_for_password, F.text & ~F.text.startswith("/"))
async def handle_site_login_password(message: Message, state: FSMContext):
    data = await state.get_data()
    password = message.text.strip()

    try:
        await message.delete()
    except Exception:
        pass

    try:
        user = await login_telegram_with_site_account(
            email=data.get("email", ""),
            password=password,
            telegram_user_id=str(message.from_user.id),
            telegram_username=message.from_user.username,
            telegram_first_name=message.from_user.first_name,
            telegram_last_name=message.from_user.last_name,
        )
    except Exception as exc:
        logging.exception("Failed to login Telegram user with site account")
        await message.answer(f"Не удалось войти через сайт: {clean(exc)}", reply_markup=main_keyboard_for(None))
        await state.clear()
        return

    await state.clear()
    await message.answer("Готово, Telegram привязан к аккаунту сайта.")
    await message.answer(format_profile(user), reply_markup=main_keyboard_for(user))


@dp.message(SiteAccessFlow.waiting_for_email, F.text & ~F.text.startswith("/"))
async def handle_site_access_email(message: Message, state: FSMContext):
    await state.update_data(email=message.text.strip())
    await state.set_state(SiteAccessFlow.waiting_for_password)
    await message.answer("Теперь придумай пароль для входа на сайт. Минимум 8 символов.")


@dp.message(SiteAccessFlow.waiting_for_password, F.text & ~F.text.startswith("/"))
async def handle_site_access_password(message: Message, state: FSMContext):
    data = await state.get_data()
    password = message.text.strip()

    try:
        await message.delete()
    except Exception:
        pass

    try:
        user = await set_site_credentials(
            telegram_user_id=str(message.from_user.id),
            email=data.get("email", ""),
            password=password,
        )
    except Exception as exc:
        logging.exception("Failed to set site credentials for Telegram user")
        current_user = await load_registered_user(str(message.from_user.id))
        await message.answer(
            f"Не удалось сохранить доступ к сайту: {clean(exc)}",
            reply_markup=main_keyboard_for(current_user),
        )
        await state.clear()
        return

    await state.clear()
    await message.answer("Готово. Теперь можно входить на сайт с этим email и паролем.")
    await message.answer(format_profile(user), reply_markup=main_keyboard_for(user))


@dp.message(RegistrationFlow.waiting_for_full_name, F.text & ~F.text.startswith("/"))
async def handle_registration_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if len(full_name) < 3:
        await message.answer("ФИО выглядит слишком коротким. Введи ФИО полностью.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationFlow.waiting_for_faculty)
    await message.answer(
        "Укажи факультет или образовательную программу. Если не хочешь указывать, отправь «-».",
        reply_markup=registration_cancel_kb(),
    )


@dp.message(RegistrationFlow.waiting_for_faculty, F.text & ~F.text.startswith("/"))
async def handle_registration_faculty(message: Message, state: FSMContext):
    faculty = message.text.strip()
    if faculty in {"-", "—"}:
        faculty = ""

    await state.update_data(faculty=faculty)
    await state.set_state(RegistrationFlow.waiting_for_course)
    await message.answer(
        "Укажи курс цифрой от 1 до 10. Если не хочешь указывать, отправь «-».",
        reply_markup=registration_cancel_kb(),
    )


@dp.message(RegistrationFlow.waiting_for_course, F.text & ~F.text.startswith("/"))
async def handle_registration_course(message: Message, state: FSMContext):
    raw_course = message.text.strip()
    course = None

    if raw_course not in {"-", "—"}:
        try:
            course = int(raw_course)
        except ValueError:
            await message.answer("Курс нужно указать числом, например 2. Можно отправить «-», чтобы пропустить.")
            return

        if not 1 <= course <= 10:
            await message.answer("Курс должен быть от 1 до 10. Можно отправить «-», чтобы пропустить.")
            return

    await state.update_data(course=course)
    await state.set_state(RegistrationFlow.waiting_for_group)
    await message.answer(
        "Укажи группу, например БПИ221. Если не хочешь указывать, отправь «-».",
        reply_markup=registration_cancel_kb(),
    )


@dp.message(RegistrationFlow.waiting_for_group, F.text & ~F.text.startswith("/"))
async def handle_registration_group(message: Message, state: FSMContext):
    raw_group = message.text.strip()
    group_name = "" if raw_group in {"-", "—"} else raw_group
    data = await state.get_data()

    try:
        user = await api_register_user(
            telegram_user_id=str(message.from_user.id),
            full_name=data["full_name"],
            faculty=data.get("faculty") or None,
            course=data.get("course"),
            group_name=group_name or None,
            telegram_username=message.from_user.username,
            telegram_first_name=message.from_user.first_name,
            telegram_last_name=message.from_user.last_name,
        )
    except Exception as exc:
        logging.exception("Failed to register user")
        await state.clear()
        current_user = await load_registered_user(str(message.from_user.id))
        if "Telegram is already linked to a site account" in str(exc):
            await message.answer(
                "Этот Telegram уже привязан к аккаунту сайта, поэтому я не буду перезаписывать его ФИО, курс и группу.\n\n"
                "В боте можно использовать только профиль, который уже привязан к этому Telegram.",
                reply_markup=main_keyboard_for(current_user),
            )
            return

        await message.answer(
            f"Не удалось сохранить регистрацию: {clean(exc)}",
            reply_markup=main_keyboard_for(current_user),
        )
        return

    await state.clear()
    await message.answer("Готово, регистрация сохранена.")
    await message.answer(format_profile(user), reply_markup=main_keyboard_for(user))


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
        await send_incoming_attachments(callback.message, selected)

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
    await send_incoming_attachments(callback.message, row)
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
    await send_incoming_attachments(callback.message, row)
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

    user = await load_registered_user(str(message.from_user.id))
    if not user:
        await message.answer("Точного ответа не найдено.")
        await ask_registration(message)
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

    user = await load_registered_user(str(callback.from_user.id))
    if not user:
        await ask_registration(callback.message)
        await callback.answer()
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
    await send_incoming_attachments(callback.message, row)
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
