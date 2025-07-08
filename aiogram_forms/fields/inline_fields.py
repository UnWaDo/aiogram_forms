from abc import abstractmethod
import dataclasses
from typing import Any, Callable, Protocol, Sequence, TypeVar

from aiogram import F, Router
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram_forms.buttons import create_pagination_buttons
from aiogram_forms.callbacks.factories import FormChoiceFieldCallback, FormPageCallback
from aiogram_forms.fields.abstract_fields import InlineReplyField
from aiogram_forms.utils import edit_message

T = TypeVar("T")
K = TypeVar("K", default=str)


@dataclasses.dataclass
class ChoiceField[T, K](InlineReplyField):
    max_options: int = 1
    page_limit: int = 5

    option_to_button: Callable[[T], str] = dataclasses.field(kw_only=True)
    option_to_data: Callable[[T], K] = dataclasses.field(kw_only=True)
    option_data_type: Callable[[str], K] = dataclasses.field(
        kw_only=True, default=str  # type: ignore
    )

    def add_objects_keyboard(
        self,
        builder: InlineKeyboardBuilder,
        options: Sequence[T],
        selected: Sequence[K],
        page: int,
    ):
        for option in options:
            value = self.option_to_data(option)
            text = self.option_to_button(option)

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
        self, callback_data: CallbackData, form_data: dict[str, Any], **kwargs
    ):
        if not isinstance(callback_data, FormChoiceFieldCallback):
            raise ValueError("callback_data is not FormChoiceFieldCallback")

        new_value = self.option_data_type(callback_data.data)
        selected: list[K] | None = form_data.get(self.name)

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
        **kwargs,
    ):
        message = callback_query.message
        if not isinstance(message, Message):
            raise ValueError("callback_query does not have message")

        form_data = await self.get_parent_form_data(state)
        keyboard = await self.inline_markup(
            form_data, page=callback_data.page, **kwargs
        )

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
        super().assign_handlers(router)

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

    async def inline_markup(
        self, form_data: dict[str, Any], page: int = 0, **kwargs
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        selected: list[K] | None = form_data.get(self.name)
        if selected is None:
            selected = []

        page_options = await self.load_options(
            form_data,
            offset=page * self.page_limit,
            limit=self.page_limit + 1,
            **kwargs,
        )

        if len(page_options) <= self.page_limit:
            is_last_page = True
        else:
            is_last_page = False
            page_options = page_options[: self.page_limit]

        self.add_objects_keyboard(builder, page_options, selected, page=page)
        builder.adjust(1)

        self.add_page_keyboard(builder, page, is_last_page)

        for action in self.additional_actions:
            builder.row(action.button(self, form_data))

        builder.row(self.return_button)

        return builder.as_markup()

    @abstractmethod
    async def load_options(
        self, form_data: dict[str, Any], offset: int, limit: int, **kwargs
    ) -> Sequence[T]: ...


@dataclasses.dataclass
class StaticChoiceField[K](ChoiceField):
    choices: dict[K, str] = dataclasses.field(kw_only=True)

    _keys: list[K] = dataclasses.field(init=False)

    option_to_button: Callable[[K], str] = dataclasses.field(init=False)
    option_to_data: Callable[[K], K] = dataclasses.field(init=False)

    def __post_init__(self):
        super().__post_init__()

        self._keys = list(self.choices.keys())
        self.option_to_button = lambda x: self.choices[x]
        self.option_to_data = lambda x: x

    async def load_options(
        self, form_data: dict[str, Any], offset: int, limit: int, **kwargs
    ):
        return self._keys[offset : offset + limit]


T = TypeVar("T")


class ObjectsLoader[T](Protocol):
    async def __call__(
        self, form_data: dict[str, Any], offset: int = 0, limit: int = 5, **kwargs
    ) -> Sequence[T]: ...


@dataclasses.dataclass
class DynamicChoiceField[T](ChoiceField):
    choices_loader: ObjectsLoader[T] = dataclasses.field(kw_only=True)

    option_to_data: Callable[[T], Any] = repr
    option_to_button: Callable[[T], str] = str

    async def load_options(
        self, form_data: dict[str, Any], offset: int, limit: int, **kwargs
    ):
        return await self.choices_loader(
            form_data=form_data, offset=offset, limit=limit, **kwargs
        )
