import dataclasses
from typing import Any, Callable, Mapping, Protocol, Sequence, TypeVar

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram_forms.buttons import create_pagination_buttons
from aiogram_forms.callbacks.factories import FormChoiceFieldCallback, FormPageCallback
from aiogram_forms.fields.abstract_fields import InlineReplyField
from aiogram_forms.utils import edit_message


@dataclasses.dataclass
class ChoiceField(InlineReplyField):
    max_options: int = 1
    page_limit: int = 5

    option_type: type[Any] = str

    def add_objects_keyboard(
        self,
        builder: InlineKeyboardBuilder,
        options: Mapping[Any, str],
        selected: Sequence[Any],
        page: int,
    ):
        for value, text in options.items():
            prefix = "✅ " if (value in selected) else ""

            builder.button(
                text=f"{prefix}{text}",
                callback_data=FormChoiceFieldCallback(
                    form_name=self.parent_form_name,
                    field_name=self.name,
                    data=value,
                    current_page=page,
                ),
            )

    def add_page_keyboard(
        self, builder: InlineKeyboardBuilder, current_page: int, is_last: bool
    ):
        builder.row(
            *create_pagination_buttons(
                form_name=self.parent_form_name,
                field_name=self.name,
                page=current_page,
                limit=self.page_limit,
                is_last_page=is_last,
            )
        )

    async def field_action(
        self, callback_data: CallbackData, form_data: dict[str, Any]
    ):
        if not isinstance(callback_data, FormChoiceFieldCallback):
            raise ValueError("callback_data is not FormChoiceFieldCallback")

        new_value = self.option_type(callback_data.data)
        selected: list[str] | None = form_data.get(self.name)

        if selected is None:
            selected = [new_value]

        elif callback_data.data in selected:
            selected.remove(new_value)

        elif len(selected) < self.max_options:
            selected.append(new_value)

        else:
            selected.pop(0)
            selected.append(new_value)

        form_data[self.name] = selected

    async def page_handler(
        self,
        callback_query: CallbackQuery,
        callback_data: FormPageCallback,
        state: FSMContext,
    ):
        message = callback_query.message
        if not isinstance(message, Message):
            raise ValueError("callback_query does not have message")

        form_data = await self.get_parent_form_data(state)
        keyboard = await self.inline_markup(form_data, page=callback_data.page)

        if message.bot is None:
            raise ValueError("Bot is not attached to message")

        await edit_message(
            chat_id=message.chat.id,
            message_id=message.message_id,
            bot=message.bot,
            text=None,
            inline_markup=keyboard,
        )
        await callback_query.answer()

    def assign_handlers(self, router: Router):
        router.callback_query.register(
            self.page_handler,
            FormPageCallback.filter(F.form_name == self.parent_form_name),
            FormPageCallback.filter(F.field_name == self.name),
        )
        router.callback_query.register(
            self.inline_handler,
            FormChoiceFieldCallback.filter(F.form_name == self.parent_form_name),
            FormChoiceFieldCallback.filter(F.field_name == self.name),
        )


@dataclasses.dataclass
class StaticChoiceField(ChoiceField):
    choices: dict[str, str] = dataclasses.field(kw_only=True)

    _names: list[str] = dataclasses.field(init=False)

    def __post_init__(self):
        self._names = list(self.choices.keys())

    async def inline_markup(
        self, form_data: dict[str, Any], page: int = 0
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        selected: list[str] | None = form_data.get(self.name)
        if selected is None:
            selected = []

        page_names = self._names[
            page * self.page_limit : (page + 1) * self.page_limit + 1
        ]
        is_last_page = len(page_names) < self.page_limit + 1
        page_names = page_names[: self.page_limit]
        page_items = {k: v for k, v in self.choices.items() if k in page_names}

        self.add_objects_keyboard(builder, page_items, selected, page=page)
        builder.adjust(1)
        self.add_page_keyboard(builder, page, is_last_page)
        builder.row(self.return_button)

        return builder.as_markup()


T = TypeVar("T")


class ObjectsLoader[T](Protocol):
    async def __call__(self, limit: int = 5, page: int = 0) -> Sequence[T]: ...


@dataclasses.dataclass
class DynamicChoiceField[T](ChoiceField):
    choices_loader: ObjectsLoader[T] = dataclasses.field(kw_only=True)

    option_type: type[Any] = int
    object_to_option: Callable[[T], Any] = repr
    object_to_text: Callable[[T], str] = str

    async def inline_markup(
        self, form_data: dict[str, Any], page: int = 0
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        selected: list[int] | None = form_data.get(self.name)
        if selected is None:
            selected = []

        objects = await self.choices_loader(page=page, limit=self.page_limit + 1)
        is_last_page = len(objects) < self.page_limit + 1
        objects = objects[: self.page_limit]

        items = {self.object_to_option(o): self.object_to_text(o) for o in objects}

        self.add_objects_keyboard(builder, items, selected, page=page)
        builder.adjust(1)
        self.add_page_keyboard(builder, page, is_last_page)
        builder.row(self.return_button)

        return builder.as_markup()
