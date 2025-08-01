import dataclasses
from gettext import gettext as _
from typing import Any, Callable, Protocol, Sequence, TypeVar

from aiogram_forms.fields.abstract_fields import Action
from aiogram_forms.fields.inline_fields import ChoiceField
from aiogram_forms.fields.message_fields import StringField

T = TypeVar("T")


class ObjectsLoaderWithFilter[T](Protocol):
    async def __call__(
        self,
        form_data: dict[str, Any],
        filter_str: str | None,
        offset: int = 0,
        limit: int = 5,
        **kwargs,
    ) -> Sequence[T]: ...


class ClearFilterAction(Action):
    name = "clear_filter"
    button_text = _("🧹 Clear filter")

    async def __call__(self, field, form_data, value=None, **kwargs):
        form_data[f"{field.name}-filter"] = None


@dataclasses.dataclass
class DynamicChoiceFieldWithStringFilter[T](StringField, ChoiceField):
    choices_loader: ObjectsLoaderWithFilter[T] = dataclasses.field(kw_only=True)

    option_to_data: Callable[[T], Any] = repr
    option_to_button: Callable[[T], str] = str

    case_sensitive_clear = False

    one_time_state: bool = False

    def __post_init__(self):
        super().__post_init__()

        clear_filter = ClearFilterAction()
        self.additional_actions.append(clear_filter)
        self._additional_actions = {
            action.name: action for action in self.additional_actions
        }

    def get_filter_value(self, form_data: dict[str, Any]):
        return form_data.get(f"{self.name}-filter")

    async def load_options(
        self, form_data: dict[str, Any], offset: int, limit: int, **kwargs
    ):
        filter_str = self.get_filter_value(form_data)

        return await self.choices_loader(
            form_data=form_data,
            filter_str=filter_str,
            offset=offset,
            limit=limit,
            **kwargs,
        )

    async def handle_text(self, text: str, form_data: dict[str, Any], **kwargs):
        filter_text = text
        if not self.case_sensitive_clear:
            text = filter_text.lower()

        form_data[f"{self.name}-filter"] = filter_text
