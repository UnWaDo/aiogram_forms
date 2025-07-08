from abc import ABC, abstractmethod
import dataclasses
import re
from typing import Any

from aiogram.types import Message


class Validator(ABC):
    @abstractmethod
    def __call__(self, value: Any, form_data: dict[str, Any], **kwargs) -> bool: ...


class MessageValidator(Validator):
    @abstractmethod
    def __call__(
        self, message: Message, form_data: dict[str, Any], **kwargs
    ) -> bool: ...


class TextValidator(MessageValidator):
    def __call__(self, message: Message, form_data: dict[str, Any], **kwargs) -> bool:
        if message.text is None:
            return False

        return self.validate_text(message.text, form_data)

    @abstractmethod
    def validate_text(self, text: str, form_data: dict[str, Any], **kwargs) -> bool: ...


@dataclasses.dataclass
class TextLengthValidator(TextValidator):
    min_length: int = 0
    max_length: int = 0

    def validate_text(self, text: str, form_data: dict[str, Any], **kwargs) -> bool:
        if self.min_length > 0 and len(text) < self.min_length:
            return False

        if self.max_length > 0 and len(text) > self.max_length:
            return False

        return True


@dataclasses.dataclass
class RegexValidator(TextValidator):
    pattern: str

    def validate_text(self, text: str, form_data: dict[str, Any], **kwargs) -> bool:
        if not re.match(self.pattern, text):
            return False

        return True
