from abc import ABC, abstractmethod
import dataclasses
from typing import Any, Callable


class FieldVisible(ABC):
    @abstractmethod
    def __call__(self, form_data: dict[str, Any]) -> bool:
        pass


@dataclasses.dataclass
class RequiredFieldsVisible(FieldVisible):
    required_fields: list[str]

    def __call__(self, form_data: dict[str, Any]):
        for field in self.required_fields:
            if field not in form_data:
                return False

        return True


@dataclasses.dataclass
class RequireValueVisible(FieldVisible):
    value_name: str
    value_validator: Callable[[Any], bool] = lambda x: x

    def __call__(self, form_data: dict[str, Any]):
        value = form_data.get(self.value_name)

        return self.value_validator(value)


@dataclasses.dataclass
class FormConditionVisible(FieldVisible):
    validator: Callable[[dict[str, Any]], bool]

    def __call__(self, form_data: dict[str, Any]):
        return self.validator(form_data)
