from typing import Any, MutableMapping

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from aiogram_forms.buttons import create_close_form_button
from aiogram_forms.callbacks.factories import FormCloseCallback, FormFieldCallback
from aiogram_forms.fields.abstract_fields import (
    FormField,
    InlineReplyField,
    MessageReplyField,
)
from aiogram_forms.fields.click_fields import ClickHandler
from aiogram_forms.modifiers.formatters import MessageFormatter
from aiogram_forms.utils import delete_message, edit_message


class FormBuilder:
    name: str
    menu_message: MessageFormatter
    preserve_data_on_restart = False

    _fields: MutableMapping[str, FormField]
    _keyboard_builder: InlineKeyboardBuilder | None = None
    _states_group: type[StatesGroup]
    _states: MutableMapping[str, State]
    _close_button: InlineKeyboardButton

    def __init__(
        self, name: str, menu_message: MessageFormatter, preserve_data_on_restart=False
    ):
        self.name = name
        self.menu_message = menu_message
        self.preserve_data_on_restart = preserve_data_on_restart

        self._fields = {}
        self._states_group = type(f"{name}-states", (StatesGroup,), {})
        self._states = {}
        self._close_button = create_close_form_button(self.name)

    def add_field(self, field: FormField):
        if field.name in self._fields:
            raise ValueError(f"Field {field.name} already exists")

        self._fields[field.name] = field
        field.parent_form_name = self.name

        if isinstance(field, MessageReplyField):
            field.fsm_state.set_parent(self._states_group)

            self._states[field.name] = field.fsm_state

    @property
    def root_message_name(self) -> str:
        return f"{self.name}-root_message"

    @property
    def initial_form_data(self) -> dict[str, Any]:
        form_data = {}

        for name, field in self._fields.items():
            if field.default_value is not None:
                form_data[name] = field.default_value

        return form_data

    async def _menu_keyboard(
        self, form_data: dict[str, Any], **kwargs
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        for name, field in self._fields.items():

            if not all(visible(form_data, **kwargs) for visible in field.visible):
                continue

            if isinstance(field.button_text, str):
                button_text = field.button_text
            else:
                button_text = await field.button_text(form_data, **kwargs)

            builder.button(
                text=button_text,
                callback_data=FormFieldCallback(
                    form_name=self.name,
                    field_name=name,
                ),
            )
        builder.adjust(1)
        builder.row(self._close_button)

        return builder.as_markup()

    async def update_root_message(
        self,
        state: FSMContext,
        event_message: Message,
        field: FormField | None = None,
        **kwargs,
    ):
        form_data = await self.get_form_data(state)

        inline_markup = None
        reply_markup = None

        if field is None or field.prompt_formatter is None:
            text = await self.menu_message(form_data, **kwargs)
        else:
            text = await field.prompt_formatter(form_data, **kwargs)

        if field is None:
            inline_markup = await self._menu_keyboard(form_data, **kwargs)

        elif isinstance(field, InlineReplyField):
            inline_markup = await field.inline_markup(form_data, **kwargs)

        elif isinstance(field, MessageReplyField) and field.text_hints:
            reply_markup = await field.reply_markup(form_data, **kwargs)

        chat_id = event_message.chat.id
        bot = event_message.bot

        if bot is None:
            raise ValueError("Bot is not attached to event message")

        root_message_id = await state.get_value(self.root_message_name)

        message_edited = False

        if form_data.get("finished") and root_message_id is not None:
            await state.update_data({self.root_message_name: None, self.name: None})
            return await delete_message(
                chat_id=chat_id,
                message_id=root_message_id,
                bot=bot,
            )

        if root_message_id is not None:
            if reply_markup is None:
                message_edited = await edit_message(
                    chat_id=chat_id,
                    message_id=root_message_id,
                    bot=bot,
                    text=text,
                    inline_markup=inline_markup,
                )
        if message_edited:
            return

        if root_message_id is not None:
            await delete_message(
                chat_id=chat_id,
                message_id=root_message_id,
                bot=bot,
            )

        root = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=inline_markup if inline_markup else reply_markup,
        )
        await state.update_data({self.root_message_name: root.message_id})

    async def get_form_data(self, state: FSMContext):
        data = await state.get_value(self.name)
        if data is None:
            data = {}

        return data

    async def update_form_data(self, state: FSMContext, data: dict[str, Any]):
        await state.update_data({self.name: data})

    def _create_click_handler(self, field: FormField):
        async def click_handler(
            callback_query: CallbackQuery, state: FSMContext, **kwargs
        ):
            message = callback_query.message
            if not isinstance(message, Message):
                raise ValueError("callback_query does not have message")

            form_data = await self.get_form_data(state)
            if isinstance(field, ClickHandler):
                await field.handle_click(form_data, **kwargs)
                await self.update_form_data(state=state, data=form_data)

                await self.update_root_message(state=state, event_message=message)
                return await callback_query.answer()

            if field.name in self._states:
                await state.set_state(self._states[field.name])

            await self.update_root_message(
                field=field, state=state, event_message=message, **kwargs
            )
            await callback_query.answer()

        return click_handler

    def _form_init_handler(self, router: Router, command_init: str | None = None):
        async def general_action(state: FSMContext):
            await state.set_state(None)

            if not self.preserve_data_on_restart:
                await state.update_data({self.root_message_name: None})
                await self.update_form_data(state, self.initial_form_data)

        async def inline_handler(
            callback_query: CallbackQuery, state: FSMContext, **kwargs
        ):
            message = callback_query.message
            if not isinstance(message, Message):
                raise ValueError("callback_query does not have message")

            await general_action(state)
            await self.update_root_message(state=state, event_message=message, **kwargs)
            await callback_query.answer()

        async def message_handler(message: Message, state: FSMContext, **kwargs):
            await general_action(state)
            await self.update_root_message(state=state, event_message=message, **kwargs)

        if command_init is None:
            router.callback_query.register(
                inline_handler,
                FormFieldCallback.filter(F.form_name == self.name),
                FormFieldCallback.filter(F.field_name.is_(None)),
            )
        else:
            router.message.register(
                message_handler,
                Command(command_init),
            )

    def _form_menu_handler(self, router: Router):
        async def inline_handler(
            callback_query: CallbackQuery, state: FSMContext, **kwargs
        ):
            message = callback_query.message
            if not isinstance(message, Message):
                raise ValueError("callback_query does not have message")

            await self.update_root_message(state=state, event_message=message, **kwargs)
            await callback_query.answer()

        router.callback_query.register(
            inline_handler,
            FormFieldCallback.filter(F.form_name == self.name),
            FormFieldCallback.filter(F.field_name.is_(None)),
        )

    def _form_close_handler(self, router: Router):
        async def close_handler(
            callback_query: CallbackQuery, state: FSMContext, **kwargs
        ):
            message = callback_query.message
            if not isinstance(message, Message):
                raise ValueError("callback_query does not have message")

            if message.bot is None:
                raise ValueError("Bot is not attached to message")

            await delete_message(
                chat_id=message.chat.id,
                message_id=message.message_id,
                bot=message.bot,
            )
            await callback_query.answer()

        router.callback_query.register(
            close_handler,
            FormCloseCallback.filter(F.form_name == self.name),
        )

    def create_callbacks_handlers(
        self, router: Router, command_init: str | None = None
    ):
        self._form_init_handler(router, command_init)
        self._form_menu_handler(router)
        self._form_close_handler(router)

        for name, field in self._fields.items():

            router.callback_query.register(
                self._create_click_handler(field),
                FormFieldCallback.filter(F.form_name == self.name),
                FormFieldCallback.filter(F.field_name == name),
            )

            filters = []
            if field.name in self._states:
                filters.append(self._states[field.name])

            if isinstance(field, MessageReplyField):
                router.message.register(
                    self._create_message_field_handler(field=field),
                    *field.filters,
                    *filters,
                )

            if isinstance(field, InlineReplyField):
                field.assign_handlers(router)

    def _create_message_field_handler(self, field: MessageReplyField):
        async def message_handler(message: Message, state: FSMContext, **kwargs):
            form_data = await self.get_form_data(state)

            if await field.validate_message(message, form_data, **kwargs):
                await field.handle_message(message, form_data, state, **kwargs)

            to_menu = (await state.get_state()) is None

            await self.update_form_data(state=state, data=form_data)
            await self.update_root_message(
                field=None if to_menu else field,
                state=state,
                event_message=message,
                **kwargs,
            )

        return message_handler
