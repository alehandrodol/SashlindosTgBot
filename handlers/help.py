from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


router = Router()

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Создает основную клавиатуру."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 База", callback_data="activation"))
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="stats"))
    builder.row(InlineKeyboardButton(text="🎮 Фан", callback_data="fun"))
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close"))
    return builder.as_markup()

def get_activation_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру базы."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Активироваться", callback_data="cmd_addme"))
    builder.row(InlineKeyboardButton(text="Деактивироваться", callback_data="cmd_disableme"))
    builder.row(InlineKeyboardButton(text="Статус локатора", callback_data="cmd_daily_status"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back"))
    return builder.as_markup()

def get_stats_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру статистики."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Рейтинг", callback_data="cmd_ratings"))
    builder.row(InlineKeyboardButton(text="Пидорасы", callback_data="cmd_masters"))
    builder.row(InlineKeyboardButton(text="Пассивы", callback_data="cmd_slaves"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back"))
    return builder.as_markup()

def get_fun_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру развлечений."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Картинка", callback_data="cmd_picture"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back"))
    return builder.as_markup()

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    await message.reply(
        "Вот пидорское меню команд:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "activation")
async def show_activation(callback: CallbackQuery):
    if callback.message.reply_to_message and callback.message.reply_to_message.from_user.id != callback.from_user.id:
        return
    await callback.message.edit_text(
        "Вот пидорские команды:",
        reply_markup=get_activation_keyboard()
    )

@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    if callback.message.reply_to_message and callback.message.reply_to_message.from_user.id != callback.from_user.id:
        return
    await callback.message.edit_text(
        "Вот пидорские команды:",
        reply_markup=get_stats_keyboard()
    )

@router.callback_query(F.data == "fun")
async def show_fun(callback: CallbackQuery):
    if callback.message.reply_to_message and callback.message.reply_to_message.from_user.id != callback.from_user.id:
        return
    await callback.message.edit_text(
        "Вот пидорские команды:",
        reply_markup=get_fun_keyboard()
    )

@router.callback_query(F.data == "back")
async def go_back(callback: CallbackQuery):
    if callback.message.reply_to_message and callback.message.reply_to_message.from_user.id != callback.from_user.id:
        return
    await callback.message.edit_text(
        "Вот пидорское меню команд:",
        reply_markup=get_main_keyboard()
    )

@router.callback_query(F.data == "close")
async def close_menu(callback: CallbackQuery):
    if callback.message.reply_to_message and callback.message.reply_to_message.from_user.id != callback.from_user.id:
        return
    await callback.message.reply_to_message.delete()
    await callback.message.delete()

@router.callback_query(F.data.startswith("cmd_"))
async def handle_command_button(callback: CallbackQuery):
    """Обработчик кнопок команд."""
    # Проверяем, что кнопку нажал тот же пользователь, который вызвал меню
    if callback.message.reply_to_message and callback.message.reply_to_message.from_user.id != callback.from_user.id:
        return

    command = callback.data.replace("cmd_", "")
    user_mention = f"@{callback.from_user.username if callback.from_user.username else callback.from_user.id}"
    await callback.message.answer(f"{user_mention}\nвот нужная тебе команда: /{command}")
    await callback.message.reply_to_message.delete()
    await callback.message.delete()
    
