from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def faq_not_found_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить без файлов",
                    callback_data="send_incoming_now",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Прикрепить файлы",
                    callback_data="attach_files",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_incoming",
                ),
            ],
        ]
    )


def files_ready_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Готово, отправить",
                    callback_data="send_incoming_now",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_incoming",
                ),
            ]
        ]
    )


def dialog_draft_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отправить сообщение",
                    callback_data="send_dialog_message",
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_dialog_message",
                ),
            ]
        ]
    )


def incoming_actions_kb(incoming_id: str, is_closed: bool = False):
    rows = []

    if not is_closed:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Ответить",
                    callback_data=f"reply_incoming:{incoming_id}",
                ),
                InlineKeyboardButton(
                    text="Информация получена",
                    callback_data=f"close_incoming:{incoming_id}",
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def registration_cancel_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="cancel_registration",
                ),
            ]
        ]
    )


def main_kb(is_registered: bool = False, has_site_credentials: bool = False):
    rows = []

    if is_registered:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Мои обращения",
                    callback_data="my_incoming",
                ),
                InlineKeyboardButton(
                    text="Мои данные",
                    callback_data="profile",
                ),
            ]
        )
        if not has_site_credentials:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Обновить регистрацию",
                        callback_data="register_user",
                    ),
                ]
            )
        rows.append(
            [
                InlineKeyboardButton(
                    text="Обновить доступ к сайту" if has_site_credentials else "Доступ к сайту",
                    callback_data="site_access",
                ),
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Зарегистрироваться в боте",
                    callback_data="register_user",
                ),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="Войти через сайт",
                    callback_data="site_login",
                ),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="Мои обращения",
                    callback_data="my_incoming",
                ),
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)
