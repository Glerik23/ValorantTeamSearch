# Обробники для звичайних користувачів
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import html
import json
from datetime import datetime, timedelta, timezone

from db.requests import add_user, create_application, get_user_applications, delete_application, get_application_by_id
from db.models import Application
from keyboards.reply import get_main_menu, get_cancel_keyboard
from keyboards.inline import *
from config import RANKS, ALL_AGENTS, REGIONS, REGION_SHORT_CODES, MODERATOR_CHAT_ID, \
    MAX_AGENTS_SELECTION, MAX_ROLES_SELECTION, BOT_OWNER_ID, \
    MAX_BIO_LENGTH, MAX_CONTACT_LENGTH, PUBLIC_CHANNEL_ID, \
    MAX_RIOT_ID_LENGTH, MAX_RANK_LENGTH, MAX_ROLE_LENGTH

logger = logging.getLogger(__name__)
router = Router()


class ApplicationForm(StatesGroup):
    """Стани FSM для створення анкети"""
    riot_id = State()
    age = State()
    rank = State()
    roles = State()
    agents = State()
    server_region = State()
    server = State()
    bio = State()
    contact_info = State()
    confirmation = State()


def is_moderator_chat(chat_id: int) -> bool:
    """Перевіряє, чи є чат модераторським"""
    return MODERATOR_CHAT_ID and chat_id == MODERATOR_CHAT_ID


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обробка команди /start"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    await state.clear()

    # Додаємо користувача в базу
    await add_user(message.from_user.id, message.from_user.username)
    logger.info(f"Користувач {message.from_user.id} (@{message.from_user.username or 'немає username'}) запустив бота")

    welcome_text = (
        "👋 Вітаю в боті для пошуку напарників у Valorant!\n\n"
        "Тут ти можеш створити анкету для пошуку гравців твого рівня. "
        "Після модерації твоя анкета з'явиться в нашому каналі.\n\n"
        "💡 Оберіть дію з меню нижче:"
    )

    # Якщо це власник бота, додаємо інформацію про адмін-команди
    if message.from_user.id == BOT_OWNER_ID:
        welcome_text += "\n\n👑 Ви є власником бота. Доступні команди:\n" \
                        "/add_moderator - додати модератора\n" \
                        "/remove_moderator - видалити модератора\n" \
                        "/list_moderators - список модераторів"

    await message.answer(welcome_text, reply_markup=get_main_menu())


@router.message(F.text == "Правила")
async def show_rules(message: Message):
    """Показати правила"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    rules_text = (
        "<b>Правила заповнення анкети та поведінки:</b>\n\n"
        "1. ✅ Заповнюйте анкету правдиво\n"
        "2. ❌ Заборонено образливий контент\n"
        "3. 👤 Не більше 1 активної анкети\n"
        "4. 🤝 Поважайте інших гравців\n"
        "5. 🎯 Вказуйте коректний Riot ID\n\n"
        "<b>Пояснення до правил:</b>\n"
        "• <b>1 активна анкета</b> - ви можете мати лише одну анкету одночасно (на модерації або опубліковану)\n"
        "• Для оновлення анкети - видаліть стару та створіть нову\n"
        "• Після відхилення анкети ви можете негайно створити нову\n\n"
        "Порушення правил призводить до блокування!"
    )
    await message.answer(rules_text, parse_mode="HTML", reply_markup=get_main_menu())


@router.message(F.text == "Подати анкету")
async def start_application(message: Message, state: FSMContext):
    """Початок створення анкети"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    await state.clear()

    # Перевіряємо наявність активних анкет
    user_applications = await get_user_applications(message.from_user.id)
    if user_applications:
        # Фільтруємо тільки активні анкети
        active_applications = [app for app in user_applications if app.status in ['pending', 'approved']]

        if active_applications:
            latest_app = active_applications[0]

            if latest_app.status == 'pending':
                await message.answer(
                    "⏳ У вас вже є анкета, яка очікує на модерацію.\n"
                    "Зачекайте, поки її перевірять, або видаліть її перед створенням нової.",
                    reply_markup=get_main_menu()
                )
                return
            elif latest_app.status == 'approved':
                await message.answer(
                    "✅ У вас вже є активна опублікована анкета.\n"
                    "Видаліть її перед створенням нової.",
                    reply_markup=get_main_menu()
                )
                return

    await state.set_state(ApplicationForm.riot_id)
    await message.answer(
        "🎮 Введіть ваш Riot ID у форматі <b>Nickname#Tag</b>\n\n"
        "Наприклад: Player123#EUW\n\n"
        "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(F.text == "Скасувати")
async def cancel_application_process(message: Message, state: FSMContext):
    """Скасування процесу створення анкети"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    await state.clear()
    await message.answer(
        "❌ Створення анкети скасовано.",
        reply_markup=get_main_menu()
    )


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Скасування поточної дії"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Немає активних дій для скасування.", reply_markup=get_main_menu())
        return

    await state.clear()
    await message.answer("✅ Поточну дію скасовано.", reply_markup=get_main_menu())


@router.message(ApplicationForm.riot_id)
async def process_riot_id(message: Message, state: FSMContext):
    """Обробка Riot ID"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    # Перевіряємо, чи не натиснув користувач "Скасувати"
    if message.text == "Скасувати":
        await cancel_application_process(message, state)
        return

    riot_id = message.text.strip()

    # Валідація формату Riot ID - дозволяємо пробіли в нікнеймі
    if not re.match(r'^[^#]+#[^#\s]+$', riot_id):
        await message.answer(
            "❌ Неправильний формат Riot ID!\n"
            "Введіть у форматі <b>Nickname#Tag</b>\n\n"
            "Наприклад: Player123#EUW\n\n"
            "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Перевірка довжини Riot ID
    if len(riot_id) > MAX_RIOT_ID_LENGTH:
        await message.answer(
            f"❌ Riot ID занадто довгий! Максимум {MAX_RIOT_ID_LENGTH} символів.\n\n"
            "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(riot_id=riot_id)
    await state.set_state(ApplicationForm.age)
    await message.answer(
        "📅 Введіть ваш вік:\n\n"
        "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(ApplicationForm.age)
async def process_age(message: Message, state: FSMContext):
    """Обробка віку"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    # Перевіряємо, чи не натиснув користувач "Скасувати"
    if message.text == "Скасувати":
        await cancel_application_process(message, state)
        return

    try:
        age = int(message.text.strip())
        if age < 13 or age > 100:
            await message.answer(
                "❌ Введіть коректний вік (13-100):\n\n"
                "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
                parse_mode="HTML",
                reply_markup=get_cancel_keyboard()
            )
            return
    except ValueError:
        await message.answer(
            "❌ Введіть числове значення для віку:\n\n"
            "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(age=age)
    await state.set_state(ApplicationForm.rank)
    await message.answer(
        "🏆 Оберіть ваш ранг:",
        reply_markup=get_ranks_keyboard()
    )


@router.callback_query(F.data.startswith("r_"), ApplicationForm.rank)
async def process_rank(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору рангу"""
    try:
        rank_index = int(callback.data.replace("r_", ""))
        if rank_index < 0 or rank_index >= len(RANKS):
            raise ValueError("Invalid rank index")
        rank = RANKS[rank_index]
    except (ValueError, IndexError):
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    # Перевірка довжини рангу
    if len(rank) > MAX_RANK_LENGTH:
        await callback.answer(f"❌ Ранг занадто довгий! Максимум {MAX_RANK_LENGTH} символів.", show_alert=True)
        return

    await state.update_data(rank=rank)
    await state.set_state(ApplicationForm.roles)

    await callback.message.edit_text(
        f"🏆 Ваш ранг: <b>{html.escape(rank)}</b>\n\n"
        f"🎯 Оберіть ваші ролі (до {MAX_ROLES_SELECTION}):",
        parse_mode="HTML",
        reply_markup=get_roles_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("role_"), ApplicationForm.roles)
async def process_role_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору ролей"""
    role = callback.data.replace("role_", "")

    data = await state.get_data()
    selected_roles = data.get("roles", [])

    if role in selected_roles:
        selected_roles.remove(role)
    else:
        if len(selected_roles) >= MAX_ROLES_SELECTION:
            await callback.answer(f"❌ Можна вибрати не більше {MAX_ROLES_SELECTION} ролей!", show_alert=True)
            return
        selected_roles.append(role)

    await state.update_data(roles=selected_roles)

    # Оновлюємо повідомлення з новим станом кнопок
    await callback.message.edit_reply_markup(
        reply_markup=get_roles_keyboard(selected_roles)
    )
    await callback.answer()


@router.callback_query(F.data == "roles_confirm", ApplicationForm.roles)
async def confirm_roles(callback: CallbackQuery, state: FSMContext):
    """Підтвердження вибору ролей"""
    data = await state.get_data()
    selected_roles = data.get("roles", [])

    if not selected_roles:
        await callback.answer("❌ Оберіть хоча б одну роль!", show_alert=True)
        return

    # Перевірка довжини ролей
    roles_text = ", ".join(selected_roles)
    if len(roles_text) > MAX_ROLE_LENGTH:
        await callback.answer(f"❌ Ролі занадто довгі! Максимум {MAX_ROLE_LENGTH} символів.", show_alert=True)
        return

    await state.set_state(ApplicationForm.agents)

    await callback.message.edit_text(
        f"🎯 Ваші ролі: <b>{html.escape(roles_text)}</b>\n\n"
        f"🦸 Оберіть ваших основних агентів (до {MAX_AGENTS_SELECTION}):",
        parse_mode="HTML",
        reply_markup=get_agents_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("a_"), ApplicationForm.agents)
async def process_agent_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору агентів"""
    agent_data = callback.data.replace("a_", "")

    if agent_data == "confirm":
        await confirm_agents(callback, state)
        return

    try:
        agent_index = int(agent_data)
        if agent_index < 0 or agent_index >= len(ALL_AGENTS):
            raise ValueError("Invalid agent index")
        agent = ALL_AGENTS[agent_index]
    except (ValueError, IndexError):
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    data = await state.get_data()
    selected_agents = data.get("agents", [])

    if agent in selected_agents:
        selected_agents.remove(agent)
    else:
        if len(selected_agents) >= MAX_AGENTS_SELECTION:
            await callback.answer(f"❌ Можна вибрати не більше {MAX_AGENTS_SELECTION} агентів!", show_alert=True)
            return
        selected_agents.append(agent)

    await state.update_data(agents=selected_agents)

    # Оновлюємо повідомлення з новим станом кнопок
    await callback.message.edit_reply_markup(
        reply_markup=get_agents_keyboard(selected_agents)
    )
    await callback.answer()


async def confirm_agents(callback: CallbackQuery, state: FSMContext):
    """Підтвердження вибору агентів"""
    data = await state.get_data()
    selected_agents = data.get("agents", [])

    if not selected_agents:
        await callback.answer("❌ Оберіть хоча б одного агента!", show_alert=True)
        return

    agents_text = html.escape(", ".join(selected_agents))
    await state.set_state(ApplicationForm.server_region)

    await callback.message.edit_text(
        f"🦸 Ваші агенти: <b>{agents_text}</b>\n\n"
        "🌍 Оберіть регіон для гри:",
        parse_mode="HTML",
        reply_markup=get_regions_keyboard()
    )


@router.callback_query(F.data.startswith("reg_"), ApplicationForm.server_region)
async def process_region(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору регіону"""
    region_code = callback.data.replace("reg_", "")

    # Знаходимо повну назву регіону по коду
    region_name = None
    for full_name, short_code in REGION_SHORT_CODES.items():
        if short_code == region_code:
            region_name = full_name
            break

    if not region_name:
        await callback.answer("❌ Помилка вибору регіону!", show_alert=True)
        return

    await state.update_data(server_region=region_name)
    await state.set_state(ApplicationForm.server)

    await callback.message.edit_text(
        f"🌍 Регіон: <b>{html.escape(region_name)}</b>\n\n"
        "📍 Оберіть сервери для гри:",
        parse_mode="HTML",
        reply_markup=get_servers_keyboard(region_name)
    )
    await callback.answer()


@router.callback_query(F.data == "back_regions", ApplicationForm.server)
async def back_to_regions(callback: CallbackQuery, state: FSMContext):
    """Повернення до вибору регіону"""
    await state.set_state(ApplicationForm.server_region)

    await callback.message.edit_text(
        "🌍 Оберіть регіон для гри:",
        parse_mode="HTML",
        reply_markup=get_regions_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("s_"), ApplicationForm.server)
async def process_server_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору серверів"""
    server_data = callback.data.replace("s_", "")

    if server_data == "confirm":
        await confirm_servers(callback, state)
        return

    server_code = server_data
    data = await state.get_data()
    selected_servers = data.get("servers", [])
    region_name = data.get("server_region")

    if server_code in selected_servers:
        selected_servers.remove(server_code)
    else:
        selected_servers.append(server_code)

    await state.update_data(servers=selected_servers)

    # Оновлюємо повідомлення з новим станом кнопок
    await callback.message.edit_reply_markup(
        reply_markup=get_servers_keyboard(region_name, selected_servers)
    )
    await callback.answer()


async def confirm_servers(callback: CallbackQuery, state: FSMContext):
    """Підтвердження вибору серверів"""
    data = await state.get_data()
    selected_servers = data.get("servers", [])
    region_name = data.get("server_region")

    if not selected_servers:
        await callback.answer("❌ Оберіть хоча б один сервер!", show_alert=True)
        return

    # Отримуємо назви серверів для відображення
    server_names = []
    region_servers = REGIONS.get(region_name, {})
    for server_code in selected_servers:
        for name, code in region_servers.items():
            if code == server_code:
                server_names.append(name)
                break

    servers_text = html.escape(", ".join(server_names))
    await state.set_state(ApplicationForm.bio)

    await callback.message.edit_text(
        f"📍 Ваші сервери: <b>{servers_text}</b>\n\n"
        "💬 Розкажіть трохи про себе:\n"
        "- Ваш стиль гри\n"
        "- Цілі (рангова, турніри, просто для fun)\n"
        "- Побажання до напарників\n\n"
        "<i>Можна пропустити, відправивши '-'</i>\n\n"
        "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
        parse_mode="HTML"
    )


@router.message(ApplicationForm.bio)
async def process_bio(message: Message, state: FSMContext):
    """Обробка біографії"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    # Перевіряємо, чи не натиснув користувач "Скасувати"
    if message.text == "Скасувати":
        await cancel_application_process(message, state)
        return

    bio = message.text.strip()
    if bio == "-":
        bio = "Не вказано"
    elif len(bio) > MAX_BIO_LENGTH:
        await message.answer(
            f"❌ Біографія занадто довга! Максимум {MAX_BIO_LENGTH} символів.\n\n"
            "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(bio=bio)
    await state.set_state(ApplicationForm.contact_info)

    await message.answer(
        "📞 Введіть контакт для зв'язку:\n"
        "Наприклад: @username в Telegram або Discord username\n\n"
        "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )


@router.message(ApplicationForm.contact_info)
async def process_contact_info(message: Message, state: FSMContext):
    """Обробка контактної інформації"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    # Перевіряємо, чи не натиснув користувач "Скасувати"
    if message.text == "Скасувати":
        await cancel_application_process(message, state)
        return

    contact_info = message.text.strip()

    if not contact_info:
        await message.answer(
            "❌ Будь ласка, введіть контакт для зв'язку:\n\n"
            "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    if len(contact_info) > MAX_CONTACT_LENGTH:
        await message.answer(
            f"❌ Контактна інформація занадто довга! Максимум {MAX_CONTACT_LENGTH} символів.\n\n"
            "<i>Для скасування створення анкети натисніть кнопку 'Скасувати'</i>",
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(contact_info=contact_info)

    # Формуємо попередній перегляд анкети
    data = await state.get_data()
    preview_text = format_application_preview(data)

    await state.set_state(ApplicationForm.confirmation)
    await message.answer(
        f"📋 <b>Попередній перегляд вашої анкети:</b>\n\n{preview_text}\n"
        "✅ Все вірно?",
        parse_mode="HTML",
        reply_markup=get_confirmation_keyboard()
    )


@router.callback_query(F.data == "confirm_app", ApplicationForm.confirmation)
async def confirm_application(callback: CallbackQuery, state: FSMContext):
    """Підтвердження та відправлення анкети на модерацію"""
    data = await state.get_data()

    # Отримуємо або створюємо користувача з правильним ID з БД
    user = await add_user(callback.from_user.id, callback.from_user.username)

    # Створюємо анкету в базі даних з правильним user_id
    application = await create_application(
        user_id=user.id,  # Використовуємо ID з БД, а не telegram_id
        riot_id=data['riot_id'],
        age=data['age'],
        rank=data['rank'],
        role=", ".join(data['roles']),  # Зберігаємо ролі як строку
        agents=data['agents'],
        server=data['servers'],
        bio=data['bio'],
        contact_info=data['contact_info']
    )

    if not application:
        await callback.message.edit_text(
            "❌ У вас вже є активна анкета (на модерації або опублікована)!\n"
            "Видаліть існуючу анкету перед створенням нової.",
            reply_markup=None
        )
        await state.clear()
        return

    # Відправлення в чат модераторів
    from keyboards.inline import get_moderation_keyboard

    moderation_text = f"🆕 Нова анкета на модерацію:\n\n{format_application_preview(data)}"

    if MODERATOR_CHAT_ID:
        try:
            await callback.bot.send_message(
                MODERATOR_CHAT_ID,
                moderation_text,
                parse_mode="HTML",
                reply_markup=get_moderation_keyboard(application.id)
            )
            logger.info(
                f"Анкета #{application.id} створена користувачем {callback.from_user.id} (@{callback.from_user.username or 'немає username'}) та відправлена на модерацію")
        except Exception as e:
            logger.error(f"Помилка при відправці анкети #{application.id} модераторам: {e}", exc_info=True)

    await callback.message.edit_text(
        "✅ Ваша анкета успішно створена та відправлена на модерацію!\n"
        "Ви отримаєте сповіщення, коли її буде перевірено.",
        reply_markup=None
    )
    # Відправляємо головне меню
    await callback.message.answer(
        "Оберіть дію:",
        reply_markup=get_main_menu()
    )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_app")
async def cancel_application_callback(callback: CallbackQuery, state: FSMContext):
    """Скасування створення анкети через інлайн-кнопку"""
    await callback.message.edit_text(
        "❌ Створення анкети скасовано.",
        reply_markup=None
    )
    # Відправляємо головне меню
    await callback.message.answer(
        "Оберіть дію:",
        reply_markup=get_main_menu()
    )
    await state.clear()
    await callback.answer()


@router.message(F.text == "Моя анкета")
async def show_my_application(message: Message):
    """Показати анкету користувача"""
    # Блокуємо функціонал в модераторському чаті
    if is_moderator_chat(message.chat.id):
        return

    user_applications = await get_user_applications(message.from_user.id)

    if not user_applications:
        await message.answer(
            "📭 У вас ще немає активних анкет.\n"
            "Створіть нову анкету за допомогою кнопки 'Подати анкету'.",
            reply_markup=get_main_menu()
        )
        return

    latest_application = user_applications[0]

    if latest_application.status == 'pending':
        await message.answer(
            "⏳ Ваша анкета ще на перевірці модераторами.\n"
            "Будь ласка, зачекайте результат.",
            reply_markup=get_main_menu()
        )
    elif latest_application.status == 'approved':
        application_text = format_application_for_channel(latest_application)
        await message.answer(
            f"✅ Ваша анкета опублікована:\n\n{application_text}",
            parse_mode="HTML",
            reply_markup=get_application_management_keyboard(latest_application.id)
        )
    elif latest_application.status == 'rejected':
        await message.answer(
            "❌ Ваша остання анкета була відхилена модератором.\n"
            "Ви можете створити нову анкету, враховуючи зауваження.",
            reply_markup=get_main_menu()
        )


@router.callback_query(F.data.startswith("del_"))
async def handle_delete_application(callback: CallbackQuery):
    """Видалення анкети"""
    try:
        application_id = int(callback.data.replace("del_", ""))
    except ValueError:
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    # Отримуємо анкету перед видаленням, щоб отримати ID повідомлення в каналі
    application = await get_application_by_id(application_id)

    if not application:
        await callback.answer("❌ Анкету не знайдено!", show_alert=True)
        return

    # Видаляємо повідомлення з каналу, якщо воно існує
    if application.status == 'approved' and application.channel_message_id and PUBLIC_CHANNEL_ID:
        try:
            await callback.bot.delete_message(
                chat_id=PUBLIC_CHANNEL_ID,
                message_id=application.channel_message_id
            )
            logger.info(f"Повідомлення анкети #{application_id} видалено з каналу")
        except Exception as e:
            logger.warning(f"Не вдалося видалити повідомлення з каналу для анкети #{application_id}: {e}")

    # Видаляємо анкету з бази даних
    success = await delete_application(application_id)

    if success:
        logger.info(f"Анкета #{application_id} повністю видалена користувачем {callback.from_user.id}")
        await callback.message.edit_text(
            "✅ Ваша анкета повністю видалена з бази даних!",
            reply_markup=None
        )
        # Відправляємо головне меню
        await callback.message.answer(
            "Оберіть дію:",
            reply_markup=get_main_menu()
        )
    else:
        logger.error(f"КРИТИЧНА ПОМИЛКА: Не вдалося видалити анкету #{application_id} з бази даних")
        await callback.message.edit_text(
            "❌ Сталася помилка при видаленні анкети з бази даних. Зверніться до адміністратора.",
            reply_markup=None
        )

    await callback.answer()


def format_application_preview(data: dict) -> str:
    """Форматування попереднього перегляду анкети"""
    # Отримуємо назви серверів
    server_names = []
    region_servers = REGIONS.get(data.get('server_region', ''), {})
    for server_code in data.get('servers', []):
        for name, code in region_servers.items():
            if code == server_code:
                server_names.append(name)
                break

    # Екрануємо всі текстові поля
    riot_id = html.escape(data['riot_id'])
    age = html.escape(str(data['age']))
    rank = html.escape(data['rank'])
    roles = html.escape(', '.join(data['roles']))
    agents = html.escape(', '.join(data['agents']))
    servers = html.escape(', '.join(server_names))
    bio = html.escape(data['bio'])
    contact_info = html.escape(data['contact_info'])

    return (
        f"🎮 <b>Riot ID:</b> {riot_id}\n"
        f"📅 <b>Вік:</b> {age}\n"
        f"🏆 <b>Ранг:</b> {rank}\n"
        f"🎯 <b>Ролі:</b> {roles}\n"
        f"🦸 <b>Агенти:</b> {agents}\n"
        f"🌍 <b>Сервери:</b> {servers}\n"
        f"💬 <b>Про себе:</b> {bio}\n"
        f"📞 <b>Контакт:</b> {contact_info}"
    )


def format_application_for_channel(application: Application) -> str:
    """Форматування анкети для публікації в каналі"""
    try:
        agents = json.loads(application.agents)
        servers = json.loads(application.server)
    except (json.JSONDecodeError, TypeError):
        # Fallback на порожні списки якщо JSON не валідний
        agents = []
        servers = []

    # Отримуємо назви серверів
    server_names = []
    for server_code in servers:
        for region_name, region_servers in REGIONS.items():
            for name, code in region_servers.items():
                if code == server_code:
                    server_names.append(name)
                    break

    # Екрануємо всі текстові поля
    riot_id = html.escape(application.riot_id)
    rank = html.escape(application.rank)
    role = html.escape(application.role)
    agents_str = html.escape(', '.join(agents))
    servers_str = html.escape(', '.join(server_names))
    bio = html.escape(application.bio)
    contact_info = html.escape(application.contact_info)

    # Формуємо окремі хештеги для кожної ролі
    roles_list = [r.strip() for r in application.role.split(',')]
    role_hashtags = ' '.join([f"#{html.escape(role.lower().replace(' ', '_'))}" for role in roles_list])

    # Хештег для рангу (тільки перше слово)
    rank_words = application.rank.split()
    rank_hashtag = f"#{html.escape(rank_words[0].lower())}" if rank_words else "#rank"

    return (
        f"🎮 <b>Шукаю напарника в Valorant!</b>\n\n"
        f"👤 <b>Гравець:</b> {riot_id}\n"
        f"🏆 <b>Ранг:</b> {rank}\n"
        f"🎯 <b>Ролі:</b> {role}\n"
        f"🦸 <b>Агенти:</b> {agents_str}\n"
        f"🌍 <b>Сервери:</b> {servers_str}\n"
        f"💬 <b>Стиль гри:</b> {bio}\n"
        f"📞 <b>Зв'язок:</b> {contact_info}\n\n"
        f"#valorant {role_hashtags} {rank_hashtag}"
    )