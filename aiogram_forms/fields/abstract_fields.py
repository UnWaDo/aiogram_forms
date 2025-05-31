from abc import ABC, abstractmethod
import dataclasses
from typing import (
    Any,
    Sequence,
)
from gettext import gettext as _

from aiogram import Router
from aiogram.filters import Filter
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.utils.magic_filter import MagicFilter

from aiogram_forms.callbacks.factories import FormFieldCallback
from aiogram_forms.modifiers.formatters import MessageFormatter
from aiogram_forms.modifiers.validators import MessageValidator
from aiogram_forms.modifiers.visibles import FieldVisible
from aiogram_forms.utils import delete_message, edit_message


@dataclasses.dataclass
class FormField(ABC):
    name: str
    button_text: str | MessageFormatter
    prompt_formatter: MessageFormatter | None = None

    default_value: Any | None = None

    visible: Sequence[FieldVisible] = dataclasses.field(default_factory=list)

    parent_form_name: str = dataclasses.field(init=False, default="")


@dataclasses.dataclass
class MessageReplyField(FormField):
    validators: Sequence[MessageValidator] = dataclasses.field(default_factory=list)
    one_time_state: bool = True
    delete_message: bool = True

    fsm_state: State = dataclasses.field(init=False)
    filters: Sequence[Filter | MagicFilter] = dataclasses.field(default_factory=list)

    text_hints: Sequence[str] = dataclasses.field(default_factory=list, kw_only=True)

    def __post_init__(self):
        self.fsm_state = State(self.name)

    async def handle_message(
        self, message: Message, form_data: dict[str, Any], state: FSMContext
    ):
        if self.one_time_state:
            await state.set_state(None)

        if self.delete_message:
            if message.bot is None:
                raise ValueError("Bot is not attached to message")

            await delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id,
                bot=message.bot,
            )

    async def validate_message(
        self, message: Message, form_data: dict[str, Any]
    ) -> bool:
        for validator in self.validators:
            if not validator(message, form_data):
                return False

        return True

    async def reply_markup(
        self, form_data: dict[str, Any]
    ) -> ReplyKeyboardMarkup | None:

        if not self.text_hints:
            return None

        builder = ReplyKeyboardBuilder()

        for text in self.text_hints:
            builder.button(text=text)

        builder.adjust(1)
        markup = builder.as_markup()
        markup.resize_keyboard = True

        return markup


@dataclasses.dataclass
class InlineReplyField(FormField):
    @abstractmethod
    async def field_action(
        self, callback_data: CallbackData, form_data: dict[str, Any]
    ): ...

    @abstractmethod
    async def inline_markup(
        self, form_data: dict[str, Any], page: int = 0
    ) -> InlineKeyboardMarkup: ...

    async def get_parent_form_data(self, state: FSMContext) -> dict[str, Any]:
        data = await state.get_value(self.parent_form_name)
        if data is None:
            data = {}

        return data

    async def update_parent_form_data(self, state: FSMContext, data: dict[str, Any]):
        await state.update_data({self.parent_form_name: data})

    async def inline_handler(
        self,
        callback_query: CallbackQuery,
        callback_data: CallbackData,
        state: FSMContext,
        **kwargs,
    ):
        message = callback_query.message
        if not isinstance(message, Message):
            raise ValueError("callback_query does not have message")

        form_data = await self.get_parent_form_data(state)
        await self.field_action(callback_data, form_data)
        await self.update_parent_form_data(state, form_data)

        if self.prompt_formatter is None:
            text = None
        else:
            text = await self.prompt_formatter(form_data)

        if hasattr(callback_data, "current_page"):
            page = getattr(callback_data, "current_page")
        else:
            page = 0

        keyboard = await self.inline_markup(form_data, page=page)

        if message.bot is None:
            raise ValueError("Bot is not attached to message")

        await edit_message(
            chat_id=message.chat.id,
            message_id=message.message_id,
            bot=message.bot,
            text=text,
            inline_markup=keyboard,
        )
        await callback_query.answer()

    @property
    def return_button(self):
        return InlineKeyboardButton(
            text=_("⬅️ Back to menu"),
            callback_data=FormFieldCallback(
                form_name=self.parent_form_name,
                field_name=self.parent_form_name,
            ).pack(),
        )

    def assign_handlers(self, router: Router): ...
