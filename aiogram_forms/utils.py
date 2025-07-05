import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

logger = logging.getLogger(__name__)


async def edit_message(
    chat_id: int,
    message_id: int,
    bot: Bot,
    text: str | None,
    inline_markup: InlineKeyboardMarkup | None = None,
):
    if text is None and inline_markup is None:
        raise ValueError("text and inline_markup cannot be both None")

    try:
        if text is None:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=inline_markup,
            )
        else:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=inline_markup,
            )
        return True
    except TelegramBadRequest as e:
        if (
            e.message
            == "Bad Request: message is not modified: specified new message content and reply markup are exactly the same as a current content and reply markup of the message"
        ):
            return True
        logger.warning(f"Exception {e} raised when editing message")

    except Exception as e:
        logger.warning(f"Exception {e} raised when editing message")

    return False


async def delete_message(chat_id: int, bot: Bot, message_id: int):
    try:
        await bot.delete_message(
            chat_id=chat_id,
            message_id=message_id,
        )
        return True
    except Exception as e:
        logger.warning(f"Exception {e} raised when deleting message")

    return False
