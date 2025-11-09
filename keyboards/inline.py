# Інлайн клавіатури
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import RANKS, ROLES, ALL_AGENTS, REGIONS, REGION_SHORT_CODES, MAX_AGENTS_SELECTION, MAX_ROLES_SELECTION, REJECTION_REASONS


def get_ranks_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору рангу"""
    builder = InlineKeyboardBuilder()

    # Додаємо всі кнопки рангів
    for rank in RANKS:
        rank_index = RANKS.index(rank)
        builder.button(text=rank, callback_data=f"r_{rank_index}")

    # Додаємо кнопку скасування
    builder.button(text="❌ Скасувати", callback_data="cancel_app")
    
    # Налаштовуємо розміщення: ранги по 3 в ряд, кнопка скасування окремо
    # adjust() з параметрами означає: перші len(RANKS) кнопок по 3 в ряд, остання 1 кнопка окремо
    num_ranks = len(RANKS)
    # Створюємо список параметрів: по 3 для кожної групи рангів, потім 1 для кнопки скасування
    adjust_params = [3] * (num_ranks // 3) + ([num_ranks % 3] if num_ranks % 3 > 0 else []) + [1]
    builder.adjust(*adjust_params)

    return builder.as_markup()



def get_roles_keyboard(selected_roles: list = None) -> InlineKeyboardMarkup:
    """Клавіатура для вибору ролей з галочками"""
    if selected_roles is None:
        selected_roles = []

    builder = InlineKeyboardBuilder()

    # Додаємо всі ролі
    for role in ROLES:
        prefix = "✅" if role in selected_roles else "☐"
        builder.button(text=f"{prefix} {role}", callback_data=f"role_{role}")

    # Кнопки підтвердження та скасування
    builder.button(text=f"🔸 Підтвердити вибір (до {MAX_ROLES_SELECTION})", callback_data="roles_confirm")
    builder.button(text="❌ Скасувати", callback_data="cancel_app")
    
    # Налаштовуємо розміщення: ролі по 2 в ряд, потім дві кнопки по одній в рядку
    num_roles = len(ROLES)
    # Створюємо список параметрів: по 2 для кожної групи ролей, потім 1, 1 для кнопок
    adjust_params = [2] * (num_roles // 2) + ([num_roles % 2] if num_roles % 2 > 0 else []) + [1, 1]
    builder.adjust(*adjust_params)

    return builder.as_markup()


def get_agents_keyboard(selected_agents: list = None) -> InlineKeyboardMarkup:
    """Клавіатура для вибору агентів з галочками"""
    if selected_agents is None:
        selected_agents = []

    builder = InlineKeyboardBuilder()

    # Додаємо всіх агентів
    for agent in ALL_AGENTS:
        prefix = "✅" if agent in selected_agents else "☐"
        agent_index = ALL_AGENTS.index(agent)
        builder.button(text=f"{prefix} {agent}", callback_data=f"a_{agent_index}")

    # Кнопки підтвердження та скасування
    builder.button(text=f"🔸 Підтвердити вибір (до {MAX_AGENTS_SELECTION})", callback_data="a_confirm")
    builder.button(text="❌ Скасувати", callback_data="cancel_app")
    
    # Налаштовуємо розміщення: агенти по 3 в ряд, потім дві кнопки по одній в рядку
    num_agents = len(ALL_AGENTS)
    # Створюємо список параметрів: по 3 для кожної групи агентів, потім 1, 1 для кнопок
    adjust_params = [3] * (num_agents // 3) + ([num_agents % 3] if num_agents % 3 > 0 else []) + [1, 1]
    builder.adjust(*adjust_params)

    return builder.as_markup()


def get_regions_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору регіону"""
    builder = InlineKeyboardBuilder()

    regions_list = list(REGION_SHORT_CODES.items())
    for region_name, short_code in regions_list:
        builder.button(text=region_name, callback_data=f"reg_{short_code}")

    builder.button(text="❌ Скасувати", callback_data="cancel_app")
    
    # Налаштовуємо розміщення: регіони по 2 в ряд (якщо можливо), кнопка скасування окремо
    num_regions = len(regions_list)
    if num_regions > 2:
        # Регіони по 2 в ряд, кнопка скасування окремо
        adjust_params = [2] * (num_regions // 2) + ([num_regions % 2] if num_regions % 2 > 0 else []) + [1]
        builder.adjust(*adjust_params)
    else:
        # Якщо регіонів мало, всі по одному в рядку
        builder.adjust(1)

    return builder.as_markup()


def get_servers_keyboard(region_name: str, selected_servers: list = None) -> InlineKeyboardMarkup:
    """Клавіатура для вибору серверів в регіоні"""
    if selected_servers is None:
        selected_servers = []

    builder = InlineKeyboardBuilder()
    region_servers = REGIONS.get(region_name, {})

    # Додаємо всі сервери
    for server_name, server_code in region_servers.items():
        prefix = "✅" if server_code in selected_servers else "☐"
        builder.button(text=f"{prefix} {server_name}", callback_data=f"s_{server_code}")

    # Кнопки дій
    builder.button(text="🔸 Підтвердити вибір серверів", callback_data="s_confirm")
    builder.button(text="◀️ Назад до регіонів", callback_data="back_regions")
    builder.button(text="❌ Скасувати", callback_data="cancel_app")
    
    # Налаштовуємо розміщення: всі кнопки по одному в рядку (сервери довгі)
    num_servers = len(region_servers)
    # Створюємо список параметрів: по 1 для кожного сервера, потім 1, 1, 1 для кнопок дій
    adjust_params = [1] * (num_servers + 3)
    builder.adjust(*adjust_params)

    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для підтвердження анкети"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Все вірно, відправити", callback_data="confirm_app")
    builder.button(text="❌ Скасувати", callback_data="cancel_app")
    builder.adjust(1)

    return builder.as_markup()


def get_moderation_keyboard(application_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для модерації"""
    builder = InlineKeyboardBuilder()

    builder.button(text="✅ Схвалити", callback_data=f"app_{application_id}")
    builder.button(text="❌ Відхилити", callback_data=f"rej_{application_id}")
    builder.adjust(2)

    return builder.as_markup()


def get_rejection_reasons_keyboard(application_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для вибору причин відхилення"""
    builder = InlineKeyboardBuilder()

    for reason_code, reason_text in REJECTION_REASONS.items():
        builder.button(text=reason_text, callback_data=f"reason_{application_id}_{reason_code}")

    builder.button(text="🔸 Підтвердити відхилення", callback_data=f"conf_rej_{application_id}")
    builder.button(text="❌ Скасувати відхилення", callback_data=f"cancel_rejection_{application_id}")
    builder.adjust(1)

    return builder.as_markup()


def get_custom_reason_keyboard(application_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для введення своєї причини"""
    builder = InlineKeyboardBuilder()

    builder.button(text="◀️ Назад до вибору причин", callback_data=f"cancel_custom_{application_id}")
    builder.adjust(1)

    return builder.as_markup()


def get_application_management_keyboard(application_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для керування анкетою"""
    builder = InlineKeyboardBuilder()

    builder.button(text="🗑️ Видалити анкету", callback_data=f"del_{application_id}")
    builder.adjust(1)

    return builder.as_markup()