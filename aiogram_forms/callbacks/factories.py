from typing import Any
from aiogram.filters.callback_data import CallbackData


class FormFieldCallback(CallbackData, prefix="form"):
    form_name: str
    field_name: str | None = None


class FormFieldActionCallback(CallbackData, prefix="formfieldaction"):
    form_name: str
    field_name: str
    action: str
    value: Any | None = None


class FormChoiceFieldCallback(CallbackData, prefix="formfieldchoice"):
    form_name: str
    field_name: str
    data: Any
    current_page: int


class FormCloseCallback(CallbackData, prefix="formclose"):
    form_name: str


class FormPageCallback(CallbackData, prefix="formpage"):
    form_name: str
    field_name: str
    page: int = 0
    limit: int = 10
