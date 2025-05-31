import dataclasses
from typing import Any, Sequence

from aiogram import F
from aiogram.filters import Filter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.magic_filter import MagicFilter

from aiogram_forms.fields.abstract_fields import MessageReplyField


@dataclasses.dataclass
class StringField(MessageReplyField):
    filters: Sequence[Filter | MagicFilter] = dataclasses.field(
        default_factory=lambda: [F.text]
    )

    async def handle_message(
        self, message: Message, form_data: dict[str, Any], state: FSMContext
    ):
        await super().handle_message(message, form_data, state)
        if message.text is None:
            return

        await self.handle_text(message.text, form_data)

    async def handle_text(self, text: str, form_data: dict[str, Any]):
        form_data[self.name] = text


@dataclasses.dataclass
class MultiStringField(StringField):
    clear_message: str = dataclasses.field(kw_only=True)
    end_of_input_message: str = dataclasses.field(kw_only=True)
    case_sensitive_end = False

    one_time_state: bool = False

    def __post_init__(self):
        super().__post_init__()

        if not self.text_hints:
            self.text_hints = [self.clear_message, self.end_of_input_message]

    async def handle_message(
        self, message: Message, form_data: dict[str, Any], state: FSMContext
    ):
        await super(StringField, self).handle_message(message, form_data, state)

        if message.text is None:
            return

        text = message.text
        clear_text = self.clear_message
        end_text = self.end_of_input_message
        if not self.case_sensitive_end:
            text = text.lower()
            clear_text = clear_text.lower()
            end_text = end_text.lower()

        if text == clear_text:
            form_data[self.name] = None
            return

        if text == end_text:
            await state.set_state(None)
            return

        await self.handle_text(message.text, form_data)

    async def handle_text(self, text: str, form_data: dict[str, Any]):
        if form_data.get(self.name) is None:
            form_data[self.name] = []

        form_data[self.name].append(text)
