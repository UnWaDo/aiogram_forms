# Aiogram Forms

A simple form builder for aiogram

## Installation

```bash
git clone https://github.com/unwado/aiogram_forms
cd aiogram_forms
pip install aiogram_forms
```

## Usage

Usage example is provided in `example.py`. To actually run it, you need to specify `API_TOKEN` environment variable (example is provided, please, create your bot token from [@BotFather](https://t.me/BotFather):

```bash
export API_TOKEN=123456789:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
```

Main idea is to create a form builder, add then add fields to it.

```python
create_task_form = FormBuilder(
    "register_user",
    FormDataFormatter(),
)
create_task_form.add_field(
    StringField(
        "name",
        "🧑 Name",
        prompt_formatter=FixedTextFormatter(text="Specify your name"),
    )
)
```

Fields are grouped by types:

- `MessageReplyField` - (m) fields that expects to receive a message from user
- `InlineReplyField` - (i) fields that expects user to press buttons
- `ClickHandler` - (c) fields that can handle click events (does not create another view when clicked from menu)

Of course, field can be simultaneously used in two or more types (*e.g.*, do something when user clicked it, then handle some text and allow to press inline button to clear entered text).

Available fields are:

- `StringField` (m): single line text input
- `MultiStringField` (m): multiple lines text input, must provide `end_message_text` and `clear_message_text` to constructor of field
- `StaticChoiceField` (i): select from predefined options
- `DynamicChoiceField` (i): select from list of options with predefined options
- `ToggleField` (c): toggle button (alternates between `True` and `False`)
- `ToggleManyField` (c): toggle button with multiple options (specified in `options` parameter)
- `SubmitField` (c): submit button

All values from fields are stored in `form_data` dictionary, which is passed to handlers of the fields. You can define your own fields.

When field is opened to a user, it will show message defined by `prompt_formatter` parameter. This can include:

- text with `FixedTextFormatter`
- mapping of value to text with `ConditionalMessageFormatter`
- whole form data with `FormDataFormatter` (helpful for debugging)
- template based on form_data with `JinjaFormatter`

It is possible to make field visible only when some condition is met. This can be done by specifying `visible` parameter when constructing a field.

- `RequiredFieldsVisible` - field is visible only when some required fields are filled (not that their presence in `form_data` is evaluated, not their value)
- `RequireValueVisible` - field is visible only when some value is `True` (or you can specify another function to check this value)
- `FormConditionVisible` - field is visible only when some function evaluates to `True` on `form_data`

When message fields are considered, it is possible to validate them by specifying `validators` parameter when constructing a field.

- `TextLengthValidator` - validates that message contains text with length between `min_length` and `max_length`
- `RegexValidator` - validates that message contains text that matches `pattern`

