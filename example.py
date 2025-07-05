import asyncio
import os
from typing import Any

from aiogram import Bot, Dispatcher, Router

from aiogram_forms.builder import FormBuilder
from aiogram_forms.fields.click_fields import SubmitField, ToggleField, ToggleManyField
from aiogram_forms.fields.complex_fields import DynamicChoiceFieldWithStringFilter
from aiogram_forms.fields.inline_fields import DynamicChoiceField, StaticChoiceField
from aiogram_forms.fields.message_fields import MultiStringField, StringField
from aiogram_forms.modifiers.formatters import FixedTextFormatter
from aiogram_forms.modifiers.formatters import FormDataFormatter
from aiogram_forms.modifiers.formatters import (
    ConditionalMessageFormatter,
    JinjaFormatter,
)
from aiogram_forms.modifiers.visibles import (
    FormConditionVisible,
    RequireValueVisible,
    RequiredFieldsVisible,
)


register_user_form = FormBuilder(
    "register_user",
    FormDataFormatter(),
)
register_user_form.add_field(
    StringField(
        "name",
        "🧑 Name",
        prompt_formatter=FixedTextFormatter(text="Specify your name"),
    )
)

template = """
Tell us about yourself, when finished, write "{{ end }}"
To clear the entered text, write "{{ clear }}"

{% if abstract %}
Current text:
{{ abstract | join('\n') }}

{% else %}
You haven't written anything yet

{% endif %}
"""

register_user_form.add_field(
    MultiStringField(
        name="abstract",
        button_text="📝 Tell us about yourself",
        prompt_formatter=JinjaFormatter(
            template=template,
            extra_values={"end": "Finish", "clear": "Clear"},
        ),
        end_of_input_message="Finish",
        clear_message="Clear",
    )
)


register_user_form.add_field(
    ToggleManyField(
        name="work_type",
        button_text=ConditionalMessageFormatter(
            value_name="work_type",
            options={
                "science": "🔬 I'm a scientist",
                "business": "💼 I'm a businessman",
                "education": "🧑‍🎓 I'm a student",
            },
        ),
        default_value="science",
        options=["science", "business", "education"],
    )
)

register_user_form.add_field(
    StaticChoiceField(
        name="work_place",
        button_text="🥼 Where do you work",
        visible=[RequireValueVisible("work_type", lambda x: x == "science")],
        choices={
            "mit": "Massachusetts Institute of Technology",
            "caltec": "California Institute of Technology",
            "harvard": "Harvard University",
            "oxford": "Oxford University",
            "peking": "Peking University",
            "msu": "Moscow State University",
        },
    )
)


async def get_all_users(limit: int = 5, page: int = 0):
    names = ["John", "Mary", "Kate", "Margo", "Liza", "Anna", "Alex", "Bob"]
    teachers = [{"id": i, "name": name} for i, name in enumerate(names)]

    return teachers[page * limit : (page + 1) * limit]


register_user_form.add_field(
    DynamicChoiceField(
        name="teacher",
        visible=[RequireValueVisible("work_type", lambda x: x == "education")],
        button_text="🧑‍🏫 Choose your teachers",
        max_options=2,
        choices_loader=get_all_users,
        option_to_data=lambda x: x["id"],
        option_to_button=lambda x: x["name"],
        option_data_type=int,
    )
)


async def get_companies(filter_str: str | None, limit: int = 5, page: int = 0):
    names = ["Apple", "Google", "Microsoft", "X", "Amazon", "Samsung", "Maven"]
    companies = [(i, name) for i, name in enumerate(names)]

    if filter_str is None:
        return companies[page * limit : (page + 1) * limit]

    selected = list(filter(lambda x: filter_str in x[1], companies))
    return selected[page * limit : (page + 1) * limit]


register_user_form.add_field(
    DynamicChoiceFieldWithStringFilter(
        name="company_name",
        visible=[RequireValueVisible("work_type", lambda x: x == "business")],
        button_text="🏢 Choose your company",
        choices_loader=get_companies,
        option_to_data=lambda x: x[0],
        option_to_button=lambda x: x[1],
        option_data_type=int,
        prompt_formatter=FixedTextFormatter(
            text='Specify your company. Type anything to filter the companies listed. Press "Clear" to clear the filter'
        ),
    )
)

register_user_form.add_field(
    ToggleField(
        name="agree",
        button_text=ConditionalMessageFormatter(
            value_name="agree",
            options={
                True: "✅ I agree that all the data is correct",
                False: "❌ Some data may be incorrect",
            },
        ),
        default_value=False,
    )
)


async def register_user(form_data: dict[str, Any]):
    print(form_data)


register_user_form.add_field(
    SubmitField(
        name="submit",
        button_text="🚀 Register",
        form_action=register_user,
        visible=[
            RequiredFieldsVisible(required_fields=["name"]),
            RequireValueVisible("agree"),
            RequireValueVisible("abstract"),
            FormConditionVisible(
                lambda data: (
                    bool(data.get("teacher"))
                    if data.get("work_type") == "education"
                    else True
                )
            ),
            FormConditionVisible(
                lambda data: (
                    bool(data.get("work_place"))
                    if data.get("work_type") == "science"
                    else True
                )
            ),
            FormConditionVisible(
                lambda data: (
                    bool(data.get("company_name"))
                    if data.get("work_type") == "business"
                    else True
                )
            ),
        ],
    )
)

bot = Bot(token=os.environ["API_TOKEN"])
dispatcher = Dispatcher()
test_form_builder_router = Router()

# second argument is command name, which is used to start form
# if you don't specify it, form will be started when FormFieldCallback with the form_name value set to form name will be called
register_user_form.create_callbacks_handlers(test_form_builder_router, "test_form")
dispatcher.include_router(test_form_builder_router)


async def main():
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
