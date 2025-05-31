import dataclasses
from typing import Any, Awaitable, Callable, Protocol, runtime_checkable

from aiogram_forms.fields.abstract_fields import FormField


@runtime_checkable
class ClickHandler(Protocol):
    async def handle_click(self, form_data: dict[str, Any]) -> None: ...


@dataclasses.dataclass
class ToggleField(FormField, ClickHandler):
    default_value: Any = False

    async def handle_click(self, form_data: dict[str, Any]):
        form_data[self.name] = not form_data.get(self.name, False)


@dataclasses.dataclass
class ToggleManyField(FormField, ClickHandler):
    options: list[Any] = dataclasses.field(kw_only=True)

    def __post_init__(self):
        if self.default_value is None:
            self.default_value = self.options[0]

    async def handle_click(self, form_data: dict[str, Any]):
        i = form_data.get(f"{self.name}-id", 0)
        value = form_data.get(self.name)

        i %= len(self.options)
        if value is not None and value == self.options[i]:
            i += 1

        form_data[self.name] = self.options[i]
        form_data[f"{self.name}-id"] = i + 1


@dataclasses.dataclass
class SubmitField(FormField, ClickHandler):
    form_action: Callable[[dict[str, Any]], Awaitable[None]] = dataclasses.field(
        kw_only=True
    )

    async def handle_click(self, form_data: dict[str, Any]):
        for validator in self.visible:
            if not validator(form_data):
                return

        form_data["finished"] = True
        await self.form_action(form_data)
