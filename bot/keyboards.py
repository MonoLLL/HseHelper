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


def main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Мои обращения",
                    callback_data="my_incoming",
                ),
            ]
        ]
    )
