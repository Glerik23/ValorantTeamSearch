# Обробники для модераторів
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import json
import html

from db.requests import get_application_by_id, update_application_channel_message, get_user_by_telegram_id, \
    get_all_moderators, set_moderator_status, get_user_by_username, get_user_by_id, update_application_status, \
    delete_application
from db.models import User
from keyboards.inline import get_rejection_reasons_keyboard, get_custom_reason_keyboard
from handlers.user_handlers import format_application_for_channel, format_application_preview
from config import PUBLIC_CHANNEL_ID, REJECTION_REASONS, BOT_OWNER_ID, MODERATOR_CHAT_ID

logger = logging.getLogger(__name__)

router = Router()


def is_moderator_chat(chat_id: int) -> bool:
    """Перевіряє, чи є чат модераторським"""
    return MODERATOR_CHAT_ID and chat_id == MODERATOR_CHAT_ID


async def is_moderator(telegram_id: int) -> bool:
    """Перевірка, чи є користувач модератором"""
    user = await get_user_by_telegram_id(telegram_id)
    return user and user.is_moderator


async def is_owner(telegram_id: int) -> bool:
    """Перевірка, чи є користувач власником"""
    return telegram_id == BOT_OWNER_ID


# Стани FSM для процесу відхилення
class RejectionStates(StatesGroup):
    waiting_for_reasons = State()
    waiting_for_custom_reason = State()


@router.message(Command("start"))
async def cmd_start_moderator(message: Message):
    """Обробка команди /start в модераторському чаті"""
    if not is_moderator_chat(message.chat.id):
        return

    welcome_text = "👮 Бот модерації анкет\n\n"

    if await is_owner(message.from_user.id):
        welcome_text += (
            "👑 Ви є власником бота. Доступні команди:\n"
            "/add_moderator - додати модератора\n"
            "/remove_moderator - видалити модератора\n"
            "/list_moderators - список модераторів\n"
            "/check_my_rights - перевірити права\n\n"
        )
    elif await is_moderator(message.from_user.id):
        welcome_text += (
            "🛡️ Ви є модератором. Доступні команди:\n"
            "/check_my_rights - перевірити права\n\n"
        )
    else:
        welcome_text += "❌ У вас немає прав модератора. Зверніться до адміністратора."

    welcome_text += "📋 Модерація анкет відбувається через інлайн-кнопки під повідомленнями про нові анкети."

    await message.answer(welcome_text)


@router.message(Command("help"))
async def cmd_help_moderator(message: Message):
    """Довідка по командах в модераторському чаті"""
    if not is_moderator_chat(message.chat.id):
        return

    help_text = (
        "📖 Довідка по командам модератора:\n\n"
        "Для модераторів:\n"
        "• /check_my_rights - перевірити свої права\n"
        "• Модерація анкет - через інлайн-кнопки під повідомленнями\n\n"
    )

    if await is_owner(message.from_user.id):
        help_text += (
            "Для власника:\n"
            "• /add_moderator @username - додати модератора\n"
            "• /remove_moderator @username - видалити модератора\n"
            "• /list_moderators - список модераторів\n"
        )

    await message.answer(help_text)


@router.callback_query(F.data.startswith("app_"))
async def approve_application(callback: CallbackQuery):
    """Схвалення анкети"""
    if not await is_moderator(callback.from_user.id):
        await callback.answer("❌ Недостатньо прав!", show_alert=True)
        return

    try:
        application_id = int(callback.data.replace("app_", ""))
    except ValueError:
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    success = await update_application_status(application_id, "approved", callback.from_user.id)

    if success:
        logger.info(f"Анкета #{application_id} схвалено модератором {callback.from_user.id}")
        application = await get_application_by_id(application_id)
        if application:
            if PUBLIC_CHANNEL_ID:
                application_text = format_application_for_channel(application)

                try:
                    message = await callback.bot.send_message(
                        PUBLIC_CHANNEL_ID,
                        application_text,
                        parse_mode="HTML"
                    )
                    # Зберігаємо ID повідомлення в каналі
                    await update_application_channel_message(application_id, message.message_id)
                    logger.info(f"Анкета #{application_id} опублікована в канал {PUBLIC_CHANNEL_ID}")
                except Exception as e:
                    logger.error(f"Помилка при публікації анкети #{application_id} в канал: {e}", exc_info=True)

            # Сповіщаємо користувача
            user = await get_user_by_id(application.user_id)
            if user:
                try:
                    await callback.bot.send_message(
                        user.telegram_id,
                        "✅ Вашу анкету схвалено та опубліковано в каналі!"
                    )
                except Exception as e:
                    logger.warning(f"Помилка при сповіщенні користувача {user.telegram_id} про схвалення анкети: {e}")

        await callback.message.edit_text(
            f"✅ Анкету #{application_id} схвалено та опубліковано!",
            reply_markup=None
        )
    else:
        await callback.answer("❌ Помилка при схваленні анкети!", show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("rej_"))
async def start_rejection(callback: CallbackQuery, state: FSMContext):
    """Початок процесу відхилення анкети"""
    # Перевірка прав модератора
    if not await is_moderator(callback.from_user.id):
        await callback.answer("❌ Недостатньо прав!", show_alert=True)
        return

    try:
        application_id = int(callback.data.replace("rej_", ""))
    except ValueError:
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    # Зберігаємо дані в FSM
    await state.set_state(RejectionStates.waiting_for_reasons)
    await state.update_data(
        application_id=application_id,
        reasons=[],
        message_id=callback.message.message_id
    )

    await callback.message.edit_text(
        "❌ Оберіть причину відхилення:\n\nОбрані причини: Не обрано",
        reply_markup=get_rejection_reasons_keyboard(application_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reason_"), RejectionStates.waiting_for_reasons)
async def select_rejection_reason(callback: CallbackQuery, state: FSMContext):
    """Вибір причини відхилення"""
    try:
        parts = callback.data.split("_", 2)
        if len(parts) < 3:
            await callback.answer("❌ Помилка формату даних!", show_alert=True)
            return
        application_id = int(parts[1])
        reason_code = parts[2]
    except (ValueError, IndexError):
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    # Отримуємо поточні дані з FSM
    data = await state.get_data()
    current_application_id = data.get("application_id")

    # Перевіряємо, що це та сама анкета
    if current_application_id != application_id:
        await callback.answer("❌ Помилка даних!", show_alert=True)
        return

    # Якщо обрано свою причину
    if reason_code == "custom":
        await state.set_state(RejectionStates.waiting_for_custom_reason)
        await callback.message.edit_text(
            "💬 Введіть свою причину відхилення анкети:",
            reply_markup=get_custom_reason_keyboard(application_id)
        )
        await callback.answer()
        return

    reasons = data.get("reasons", [])
    reason_text = REJECTION_REASONS.get(reason_code, "Інше")

    if reason_text in reasons:
        reasons.remove(reason_text)
    else:
        reasons.append(reason_text)

    # Оновлюємо дані в FSM
    await state.update_data(reasons=reasons)

    # Формуємо текст обраних причин
    reasons_display = ", ".join(reasons) if reasons else "Не обрано"

    # Оновлюємо повідомлення з новим станом кнопок
    try:
        await callback.message.edit_text(
            f"❌ Оберіть причину відхилення:\n\nОбрані причини: {reasons_display}",
            reply_markup=get_rejection_reasons_keyboard(application_id)
        )
    except TelegramBadRequest:
        # Ігноруємо помилку, якщо повідомлення не змінилося
        pass

    await callback.answer()


@router.message(RejectionStates.waiting_for_custom_reason)
async def process_custom_reason(message: Message, state: FSMContext):
    """Обробка введеної своєї причини з повним видаленням анкети"""
    custom_reason = message.text.strip()

    if not custom_reason:
        await message.answer("❌ Будь ласка, введіть причину відхилення:")
        return

    data = await state.get_data()
    application_id = data.get("application_id")
    message_id = data.get("message_id")

    if not application_id:
        await message.answer("❌ Помилка: не знайдено ID анкети. Спробуйте ще раз.")
        await state.clear()
        return

    # Отримуємо анкету перед видаленням для сповіщення користувача
    application = await get_application_by_id(application_id)
    if not application:
        await message.answer("❌ Анкету не знайдено!")
        await state.clear()
        return

    # Сповіщаємо користувача перед видаленням
    user = await get_user_by_id(application.user_id)
    if user:
        try:
            await message.bot.send_message(
                user.telegram_id,
                f"❌ Вашу анкету відхилено з наступної причини:\n\n💬 {custom_reason}\n\n"
                f"Ви можете створити нову анкету, враховуючи зауваження."
            )
        except Exception as e:
            logger.warning(f"Помилка при сповіщенні користувача {user.telegram_id} про відхилення анкети: {e}")

    # Повністю видаляємо анкету з бази даних
    success = await delete_application(application_id)

    if success:
        logger.info(
            f"Анкета #{application_id} відхилено та видалено модератором {message.from_user.id} з причиною: {custom_reason[:50]}")

        # Оновлюємо оригінальне повідомлення
        if message_id:
            try:
                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=message_id,
                    text=f"❌ Анкету #{application_id} відхилено та видалено!\n<b>Причина:</b> {html.escape(custom_reason)}",
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Помилка при оновленні повідомлення {message_id} в чаті {message.chat.id}: {e}")

        await message.answer(
            f"❌ Анкету #{application_id} відхилено та видалено!\n"
            f"<b>Причина:</b> {html.escape(custom_reason)}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Помилка при відхиленні анкети!")

    # Очищаємо стан
    await state.clear()


@router.callback_query(F.data.startswith("cancel_custom_"))
async def cancel_custom_reason(callback: CallbackQuery, state: FSMContext):
    """Скасування введення своєї причини"""
    try:
        application_id = int(callback.data.replace("cancel_custom_", ""))
    except ValueError:
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    # Повертаємося до вибору причин
    await state.set_state(RejectionStates.waiting_for_reasons)
    await state.update_data(reasons=[])

    await callback.message.edit_text(
        "❌ Оберіть причину відхилення:\n\nОбрані причини: Не обрано",
        reply_markup=get_rejection_reasons_keyboard(application_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("conf_rej_"), RejectionStates.waiting_for_reasons)
async def confirm_rejection(callback: CallbackQuery, state: FSMContext):
    """Підтвердження відхилення анкети з повним видаленням"""
    try:
        application_id = int(callback.data.replace("conf_rej_", ""))
    except ValueError:
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    data = await state.get_data()
    current_application_id = data.get("application_id")

    if current_application_id != application_id:
        await callback.answer("❌ Помилка даних!", show_alert=True)
        return

    reasons = data.get("reasons", [])
    if not reasons:
        await callback.answer("❌ Оберіть хоча б одну причину!", show_alert=True)
        return

    # Отримуємо анкету перед видаленням для сповіщення користувача
    application = await get_application_by_id(application_id)
    if not application:
        await callback.answer("❌ Анкету не знайдено!", show_alert=True)
        return

    # Сповіщаємо користувача перед видаленням
    user = await get_user_by_id(application.user_id)
    if user:
        reasons_text = "\n• ".join(reasons)
        try:
            await callback.bot.send_message(
                user.telegram_id,
                f"❌ Вашу анкету відхилено з наступних причин:\n\n• {reasons_text}\n\n"
                f"Ви можете створити нову анкету, враховуючи зауваження."
            )
        except Exception as e:
            logger.warning(f"Помилка при сповіщенні користувача {user.telegram_id}: {e}")

    # Повністю видаляємо анкету з бази даних
    success = await delete_application(application_id)

    if success:
        reasons_text = ", ".join(reasons)
        logger.info(f"Анкета #{application_id} відхилено та видалено модератором {callback.from_user.id}")

        await callback.message.edit_text(
            f"❌ Анкету #{application_id} відхилено та повністю видалено!\n"
            f"<b>Причини:</b> {', '.join(reasons)}",
            parse_mode="HTML",
            reply_markup=None
        )
    else:
        await callback.answer("❌ Помилка при відхиленні анкети!", show_alert=True)

    # Очищаємо стан
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_rejection_"))
async def cancel_rejection_process(callback: CallbackQuery, state: FSMContext):
    """Скасування процесу відхилення"""
    try:
        application_id = int(callback.data.replace("cancel_rejection_", ""))
    except ValueError:
        await callback.answer("❌ Помилка обробки даних!", show_alert=True)
        return

    # Очищаємо стан
    await state.clear()

    # Повертаємося до оригінального стану модерації
    application = await get_application_by_id(application_id)
    if application:
        from keyboards.inline import get_moderation_keyboard

        try:
            agents_data = json.loads(application.agents)
            servers_data = json.loads(application.server)
        except (json.JSONDecodeError, TypeError) as e:
            await callback.message.edit_text(
                "❌ Помилка при завантаженні даних анкети!",
                reply_markup=None
            )
            await callback.answer()
            return

        application_data = {
            'riot_id': application.riot_id,
            'age': application.age,
            'rank': application.rank,
            'roles': application.role.split(', '),
            'agents': agents_data,
            'servers': servers_data,
            'bio': application.bio,
            'contact_info': application.contact_info
        }
        moderation_text = f"🆕 Нова анкета на модерацію:\n\n{format_application_preview(application_data)}"

        await callback.message.edit_text(
            moderation_text,
            parse_mode="HTML",
            reply_markup=get_moderation_keyboard(application.id)
        )
    else:
        await callback.message.edit_text(
            "❌ Анкету не знайдено!",
            reply_markup=None
        )

    await callback.answer("✅ Процес відхилення скасовано")


# Команди для власника бота
@router.message(Command("add_moderator"))
async def add_moderator_command(message: Message):
    """Додавання модератора"""
    # У модераторському чаті дозволяємо команду тільки власнику
    if is_moderator_chat(message.chat.id) and not await is_owner(message.from_user.id):
        return

    if not await is_owner(message.from_user.id):
        await message.answer("❌ Ця команда доступна тільки власнику бота!")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Використання: /add_moderator <user_id або @username>\n\n"
            "Наприклад:\n"
            "/add_moderator 123456789\n"
            "/add_moderator @username"
        )
        return

    user_identifier = args[1]

    # Спробуємо знайти користувача
    user = None

    # Якщо це числовий ID
    if user_identifier.isdigit():
        user = await get_user_by_telegram_id(int(user_identifier))
    # Якщо це username (починається з @)
    elif user_identifier.startswith('@'):
        user = await get_user_by_username(user_identifier[1:])
    else:
        # Можливо, це username без @
        user = await get_user_by_username(user_identifier)

    if not user:
        await message.answer("❌ Користувача не знайдено! Переконайтесь, що користувач взаємодіяв з ботом.")
        return

    if user.is_moderator:
        await message.answer("❌ Цей користувач вже є модератором!")
        return

    # Додаємо модератора
    success = await set_moderator_status(user.id, True)

    if success:
        logger.info(
            f"Модератор додано: {user.telegram_id} (@{user.username or 'немає username'}) власником {message.from_user.id} (@{message.from_user.username or 'немає username'})")
        await message.answer(f"✅ Користувач {user.username or user_identifier} тепер модератор!")

        # Сповіщаємо нового модератора
        try:
            await message.bot.send_message(
                user.telegram_id,
                "🎉 Вам були надані права модератора! Тепер ви можете перевіряти анкети."
            )
        except Exception as e:
            logger.warning(f"Помилка при сповіщенні нового модератора {user.telegram_id}: {e}")
    else:
        await message.answer("❌ Помилка при додаванні модератора!")


@router.message(Command("remove_moderator"))
async def remove_moderator_command(message: Message):
    """Видалення модератора"""
    # У модераторському чаті дозволяємо команду тільки власнику
    if is_moderator_chat(message.chat.id) and not await is_owner(message.from_user.id):
        return

    if not await is_owner(message.from_user.id):
        await message.answer("❌ Ця команда доступна тільки власнику бота!")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer(
            "❌ Використання: /remove_moderator <user_id або @username>\n\n"
            "Наприклад:\n"
            "/remove_moderator 123456789\n"
            "/remove_moderator @username"
        )
        return

    user_identifier = args[1]

    # Спробуємо знайти користувача
    user = None

    # Якщо це числовий ID
    if user_identifier.isdigit():
        user = await get_user_by_telegram_id(int(user_identifier))
    # Якщо це username (починається з @)
    elif user_identifier.startswith('@'):
        user = await get_user_by_username(user_identifier[1:])
    else:
        # Можливо, це username без @
        user = await get_user_by_username(user_identifier)

    if not user:
        await message.answer("❌ Користувача не знайдено!")
        return

    if not user.is_moderator:
        await message.answer("❌ Цей користувач не є модератором!")
        return

    # Видаляємо модератора
    success = await set_moderator_status(user.id, False)

    if success:
        logger.info(
            f"Модератор видалено: {user.telegram_id} (@{user.username or 'немає username'}) власником {message.from_user.id} (@{message.from_user.username or 'немає username'})")
        await message.answer(f"✅ Користувач {user.username or user_identifier} більше не модератор!")

        # Сповіщаємо колишнього модератора
        try:
            await message.bot.send_message(
                user.telegram_id,
                "ℹ️ Ваші права модератора були відкликані."
            )
        except Exception as e:
            logger.warning(f"Помилка при сповіщенні колишнього модератора {user.telegram_id}: {e}")
    else:
        await message.answer("❌ Помилка при видаленні модератора!")


@router.message(Command("list_moderators"))
async def list_moderators_command(message: Message):
    """Список модераторів"""
    # У модераторському чаті дозволяємо команду тільки власнику
    if is_moderator_chat(message.chat.id) and not await is_owner(message.from_user.id):
        return

    if not await is_owner(message.from_user.id):
        await message.answer("❌ Ця команда доступна тільки власнику бота!")
        return

    moderators = await get_all_moderators()

    if not moderators:
        await message.answer("📭 Модераторів поки що немає.")
        return

    moderators_text = "👥 Список модераторів:\n\n"
    for i, moderator in enumerate(moderators, 1):
        moderators_text += f"{i}. @{moderator.username or 'немає username'} (ID: {moderator.telegram_id})\n"

    await message.answer(moderators_text)


@router.message(Command("check_my_rights"))
async def check_my_rights_command(message: Message):
    """Перевірка своїх прав"""
    user = await get_user_by_telegram_id(message.from_user.id)

    if not user:
        await message.answer("❌ Вас не знайдено в базі даних. Спробуйте /start")
        return

    rights_text = f"👤 Ваші права:\n\n"
    rights_text += f"Telegram ID: {message.from_user.id}\n"
    rights_text += f"Username: @{message.from_user.username or 'немає'}\n"
    rights_text += f"Модератор: {'✅' if user.is_moderator else '❌'}\n"
    rights_text += f"Власник: {'✅' if await is_owner(message.from_user.id) else '❌'}\n"

    await message.answer(rights_text)


# Обробник для скасування всіх станів (опційно)
@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    """Скасування поточного стану"""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("❌ Немає активних дій для скасування.")
        return

    await state.clear()
    await message.answer("✅ Поточну дію скасовано.")