from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


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


def main_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мои обращения", callback_data="my_incoming"),
            ]
        ]
    )