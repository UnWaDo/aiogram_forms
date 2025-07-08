from abc import ABC, abstractmethod
import dataclasses
from gettext import gettext as _
from typing import Any, Sequence

from aiogram import F, Router
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

from aiogram_forms.callbacks.factories import FormFieldActionCallback, FormFieldCallback
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
        self, message: Message, form_data: dict[str, Any], state: FSMContext, **kwargs
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
        self, message: Message, form_data: dict[str, Any], **kwargs
    ) -> bool:
        for validator in self.validators:
            if not validator(message, form_data, **kwargs):
                return False

        return True

    async def reply_markup(
        self, form_data: dict[str, Any], **kwargs
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


class Action:
    name: str
    button_text: str

    @abstractmethod
    async def __call__(
        self,
        field: FormField,
        form_data: dict[str, Any],
        value: Any | None = None,
        **kwargs,
    ) -> Any: ...

    def prepare_value(self, field: FormField, form_data: dict[str, Any], **kwargs):
        return None

    def callback_data(self, field: FormField, form_data: dict[str, Any], **kwargs):
        return FormFieldActionCallback(
            form_name=field.parent_form_name,
            field_name=field.name,
            action=self.name,
            value=self.prepare_value(field, form_data, **kwargs),
        ).pack()

    def button(self, field: FormField, form_data: dict[str, Any], **kwargs):
        return InlineKeyboardButton(
            text=self.button_text,
            callback_data=self.callback_data(field, form_data, **kwargs),
        )


@dataclasses.dataclass
class InlineReplyField(FormField):
    additional_actions: list[Action] = dataclasses.field(
        kw_only=True, default_factory=list
    )

    _additional_actions: dict[str, Action] = dataclasses.field(init=False)

    def __post_init__(self):
        self._additional_actions = {
            action.name: action for action in self.additional_actions
        }

    @abstractmethod
    async def field_action(
        self, callback_data: CallbackData, form_data: dict[str, Any], **kwargs
    ): ...

    @abstractmethod
    async def inline_markup(
        self, form_data: dict[str, Any], page: int = 0, **kwargs
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

        if isinstance(callback_data, FormFieldActionCallback):
            action = self._additional_actions.get(callback_data.action)
            if action is None:
                raise ValueError(f"Action {callback_data.action} is not registered")

            await action(self, form_data, callback_data.value, **kwargs)

        else:
            await self.field_action(callback_data, form_data, **kwargs)

        await self.update_parent_form_data(state, form_data)

        if self.prompt_formatter is None:
            text = None
        else:
            text = await self.prompt_formatter(form_data, **kwargs)

        if hasattr(callback_data, "current_page"):
            page = getattr(callback_data, "current_page")
        else:
            page = 0

        keyboard = await self.inline_markup(form_data, page=page, **kwargs)

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

    def assign_handlers(self, router: Router):
        router.callback_query.register(
            self.inline_handler,
            FormFieldActionCallback.filter(F.form_name == self.parent_form_name),
            FormFieldActionCallback.filter(F.field_name == self.name),
        )

    @property
    def return_button(self):
        return InlineKeyboardButton(
            text=_("⬅️ Back to menu"),
            callback_data=FormFieldCallback(
                form_name=self.parent_form_name,
                field_name=None,
            ).pack(),
        )
