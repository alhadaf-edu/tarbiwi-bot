from typing import List, Callable, Any
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def build_pagination_keyboard(
    items: List[Any],
    page: int,
    page_size: int,
    item_btn_builder: Callable[[Any], InlineKeyboardButton],
    page_callback_prefix: str,
    extra_buttons: List[List[InlineKeyboardButton]] = None
) -> InlineKeyboardMarkup:
    """
    Builds an inline keyboard with pagination controls.
    """
    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, total_items)
    page_items = items[start_idx:end_idx]

    keyboard: List[List[InlineKeyboardButton]] = []

    # Add item buttons (1 item or row per item)
    for itm in page_items:
        btn = item_btn_builder(itm)
        if isinstance(btn, list):
            keyboard.append(btn)
        else:
            keyboard.append([btn])

    # Navigation row
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="➡️ السابق", callback_data=f"{page_callback_prefix}:{page-1}"))
    
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1} / {total_pages}", callback_data="noop"))

    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ⬅️", callback_data=f"{page_callback_prefix}:{page+1}"))

    if nav_row:
        keyboard.append(nav_row)

    if extra_buttons:
        for row in extra_buttons:
            keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
