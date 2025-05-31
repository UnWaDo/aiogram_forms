from gettext import gettext as _

from aiogram.types import InlineKeyboardButton

from aiogram_forms.callbacks.factories import FormCloseCallback, FormPageCallback


def create_close_form_button(form_name: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=_("🚫 Close"),
        callback_data=FormCloseCallback(form_name=form_name).pack(),
    )


def create_pagination_buttons(
    form_name: str, field_name: str, page: int, limit: int, is_last_page=False
) -> list[InlineKeyboardButton]:
    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="↩️",
                callback_data=FormPageCallback(
                    form_name=form_name,
                    field_name=field_name,
                    page=page - 1,
                    limit=limit,
                ).pack(),
            )
        )
    else:
        buttons.append(
            InlineKeyboardButton(
                text="🫷",
                callback_data=FormPageCallback(
                    form_name=form_name,
                    field_name=field_name,
                    page=page,
                    limit=limit,
                ).pack(),
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=str(page + 1),
            callback_data=FormPageCallback(
                form_name=form_name,
                field_name=field_name,
                page=page,
                limit=limit,
            ).pack(),
        )
    )

    if not is_last_page:
        buttons.append(
            InlineKeyboardButton(
                text="↪️",
                callback_data=FormPageCallback(
                    form_name=form_name,
                    field_name=field_name,
                    page=page + 1,
                    limit=limit,
                ).pack(),
            )
        )
    else:
        buttons.append(
            InlineKeyboardButton(
                text="🫸",
                callback_data=FormPageCallback(
                    form_name=form_name,
                    field_name=field_name,
                    page=page,
                    limit=limit,
                ).pack(),
            )
        )

    return buttons
