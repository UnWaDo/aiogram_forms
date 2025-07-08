from abc import ABC, abstractmethod
import dataclasses
from gettext import gettext as _
from typing import Any, Hashable

import jinja2


class MessageFormatter(ABC):
    @abstractmethod
    async def __call__(self, form_data: dict[str, Any], **kwargs) -> str: ...


@dataclasses.dataclass
class FixedTextFormatter(MessageFormatter):
    text: str

    async def __call__(self, form_data: dict[str, Any], **kwargs) -> str:
        return self.text


@dataclasses.dataclass
class ConditionalMessageFormatter(MessageFormatter):
    value_name: str
    options: dict[Hashable, str]
    default_text: str = _("😢 Text is missing")

    async def __call__(self, form_data: dict[str, Any], **kwargs) -> str:
        value = form_data.get(self.value_name)
        if value is None:
            return self.default_text

        return self.options.get(value, self.default_text)


class FormDataFormatter(MessageFormatter):
    async def __call__(self, form_data: dict[str, Any], **kwargs) -> str:
        return str(form_data)


@dataclasses.dataclass
class JinjaFormatter(MessageFormatter):
    template: str
    extra_values: dict[str, Any] = dataclasses.field(default_factory=dict)

    async def __call__(self, form_data: dict[str, Any], **kwargs) -> str:
        return jinja2.Template(self.template).render(
            **{**self.extra_values, **form_data}
        )
