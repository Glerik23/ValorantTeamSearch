# Реплай клавіатури
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    """Головне меню"""
    keyboard = [
        [KeyboardButton(text="Подати анкету")],
        [KeyboardButton(text="Моя анкета"), KeyboardButton(text="Правила")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавіатура для скасування під час заповнення анкети"""
    keyboard = [
        [KeyboardButton(text="Скасувати")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)