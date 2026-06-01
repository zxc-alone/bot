from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import os
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "img")

API_TOKEN = os.getenv('key')

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Конфигурация бота для покупок
PURCHASE_BOT_USERNAME = "ChillVibes_01"  # Замените на username вашего бота для покупок
PURCHASE_BOT_LINK = f"https://t.me/{PURCHASE_BOT_USERNAME}"

# Структура для хранения сообщений
class ChatHistory:
    def __init__(self):
        self.messages = []  # Список всех ID сообщений бота в чате
        self.first_message_id = None
        self.last_cleanup = datetime.now()
    
    def add_message(self, message_id):
        """Добавляет сообщение в историю"""
        self.messages.append(message_id)
        if len(self.messages) == 1:
            self.first_message_id = message_id
    
    def get_last_message(self):
        """Возвращает последнее сообщение"""
        return self.messages[-1] if self.messages else None
    
    def get_first_message(self):
        """Возвращает первое сообщение"""
        return self.messages[0] if self.messages else None
    
    async def delete_oldest_message(self, chat_id):
        """Удаляет самое старое сообщение (кроме случая, когда оно единственное)"""
        if len(self.messages) >= 2:
            try:
                # Удаляем самое старое сообщение (первое в списке)
                await bot.delete_message(chat_id, self.messages[0])
                print(f"✅ Удалено самое старое сообщение {self.messages[0]} в чате {chat_id}")
                
                # Удаляем его из списка
                self.messages.pop(0)
                return True
            except Exception as e:
                print(f"❌ Не удалось удалить {self.messages[0]}: {e}")
        return False
    
    async def cleanup_all_except_last(self, chat_id):
        """Удаляет все сообщения кроме последнего"""
        deleted_count = 0
        while len(self.messages) > 1:
            try:
                await bot.delete_message(chat_id, self.messages[0])
                self.messages.pop(0)
                deleted_count += 1
            except Exception as e:
                print(f"❌ Не удалось удалить {self.messages[0]}: {e}")
                break
        
        self.last_cleanup = datetime.now()
        return deleted_count
    
    def should_cleanup(self):
        """Проверяет, прошло ли 24 часа"""
        return datetime.now() - self.last_cleanup > timedelta(hours=24)

# Хранилище историй для каждого чата
chat_histories = {}

def get_chat_history(chat_id: int) -> ChatHistory:
    """Получает или создает историю для чата"""
    if chat_id not in chat_histories:
        chat_histories[chat_id] = ChatHistory()
    return chat_histories[chat_id]

# Функции для создания клавиатур
def get_main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📱 Телефон", callback_data="product1"),
         InlineKeyboardButton(text="🎧 Наушники", callback_data="product2")],
        [InlineKeyboardButton(text="💻 Ноутбук", callback_data="product3")],
        [InlineKeyboardButton(text="📞 Контакты", callback_data="contacts"),
         InlineKeyboardButton(text="ℹ️ О нас", callback_data="about")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_product_keyboard(product_name: str = ""):
    """Создает клавиатуру для карточки товара с кнопкой покупки"""
    buttons = [
        # Кнопка покупки (открывает бота для покупок)
        [InlineKeyboardButton(text="🛒 Купить", url=PURCHASE_BOT_LINK)],
        # Кнопки навигации
        [InlineKeyboardButton(text="🔙 К товарам", callback_data="back_to_products"),
         InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Функция для создания клавиатуры с информацией о боте для покупок
def get_purchase_info_keyboard():
    buttons = [
        [InlineKeyboardButton(
            text="🛍 Перейти в магазин", 
            url=PURCHASE_BOT_LINK
        )],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

products = {
    "product1": {
        "name": "📱 Телефон",
        "price": "35 000 ₽",
        "photo": "йоу.jpg",
        "description": "Современный смартфон с отличной камерой"
    },
    "product2": {
        "name": "🎧 Наушники",
        "price": "4 500 ₽",
        "photo": "i.webp",
        "description": "Беспроводные наушники с шумоподавлением"
    },
    "product3": {
        "name": "💻 Ноутбук",
        "price": "70 000 ₽",
        "photo": "da9bebc1-91eb-4501-8225-03f674fc717a.jfif",
        "description": "Мощный ноутбук для работы и игр"
    },
}


def resolve_product_photo(filename: str) -> str | None:
    """Абсолютный путь к файлу в папке img."""
    if not filename:
        return None
    path = filename if os.path.isabs(filename) else os.path.join(IMG_DIR, filename)
    return path if os.path.isfile(path) else None


def make_photo_input(photo_path: str) -> FSInputFile:
    """Telegram лучше принимает .jpg/.webp; для .jfif подменяем имя при загрузке."""
    upload_name = os.path.basename(photo_path)
    if upload_name.lower().endswith(".jfif"):
        upload_name = upload_name[:-5] + ".jpg"
    return FSInputFile(photo_path, filename=upload_name)


async def send_and_track(chat_id: int, text: str, reply_markup=None, photo_path=None):
    """Отправляет сообщение и отслеживает его в истории"""
    history = get_chat_history(chat_id)
    
    # Отправляем новое сообщение
    abs_photo = resolve_product_photo(photo_path) if photo_path else None
    if abs_photo:
        sent = await bot.send_photo(
            chat_id=chat_id,
            photo=make_photo_input(abs_photo),
            caption=text,
            reply_markup=reply_markup
        )
    elif photo_path:
        print(f"⚠️ Картинка не найдена: {photo_path} (ожидалось в {IMG_DIR})")
        sent = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
    else:
        sent = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
    
    print(f"📤 Отправлено сообщение {sent.message_id} в чат {chat_id}")
    print(f"   Текущая история до добавления: {history.messages}")
    
    # Добавляем в историю
    history.add_message(sent.message_id)
    
    # Если после добавления стало 2 или более сообщений, удаляем самое старое
    if len(history.messages) >= 2:
        await history.delete_oldest_message(chat_id)
    
    print(f"   История после обработки: {history.messages}")
    
    return sent

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    history = get_chat_history(message.chat.id)
    
    # Очищаем все предыдущие сообщения, оставляя только последнее
    await history.cleanup_all_except_last(message.chat.id)
    
    # Отправляем новое меню
    await send_and_track(
        message.chat.id,
        "🏠 Главное меню\n\nПривет! Какой товар тебя интересует сегодня?",
        get_main_menu_keyboard()
    )
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except:
        pass

@dp.callback_query()
async def product_callback(callback: types.CallbackQuery):
    history = get_chat_history(callback.message.chat.id)
    
    # Обработка возврата в главное меню
    if callback.data == "back_to_main":
        await send_and_track(
            callback.message.chat.id,
            "🏠 Главное меню\n\nПривет! Какой товар тебя интересует сегодня?",
            get_main_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Обработка возврата к товарам
    if callback.data == "back_to_products":
        await send_and_track(
            callback.message.chat.id,
            "📋 Список товаров:",
            get_main_menu_keyboard()
        )
        await callback.answer()
        return
    
    # Обработка контактов
    if callback.data == "contacts":
        await send_and_track(
            callback.message.chat.id,
            "📞 Контакты:\n\n"
            "📱 Телефон: +7 (999) 123-45-67\n"
            "✉️ Email: shop@example.com\n"
            "📍 Адрес: ул. Примерная, д. 123",
            get_back_keyboard()
        )
        await callback.answer()
        return
    
    # Обработка "О нас"
    if callback.data == "about":
        await send_and_track(
            callback.message.chat.id,
            "ℹ️ О нас:\n\n"
            "Мы - современный интернет-магазин электроники.\n"
            "Работаем с 2020 года.\n"
            "✓ Только оригинальная продукция\n"
            "✓ Гарантия качества\n"
            "✓ Быстрая доставка",
            get_back_keyboard()
        )
        await callback.answer()
        return
    
    # Обработка товаров
    if callback.data in products:
        product = products[callback.data]
        text = (f"{product['name']}\n\n"
                f"💰 Цена: {product['price']}\n"
                f"📝 {product['description']}\n\n"
                f"Для покупки нажмите кнопку 'Купить' 👇")
        
        # Используем клавиатуру с кнопкой покупки
        await send_and_track(
            callback.message.chat.id,
            text,
            get_product_keyboard(product['name']),
            product['photo']
        )
        await callback.answer()
        return
    
    # Обработка нажатия на кнопку покупки (если это callback, а не url)
    if callback.data.startswith("buy_"):
        product_name = callback.data.replace("buy_", "")
        await send_and_track(
            callback.message.chat.id,
            f"🛒 Покупка товара: {product_name}\n\n"
            f"Для оформления заказа перейдите в бота:\n"
            f"👉 @{PURCHASE_BOT_USERNAME}\n\n"
            f"Или нажмите кнопку ниже:",
            get_purchase_info_keyboard()
        )
        await callback.answer()
        return
    
    await callback.answer("Неизвестная команда", show_alert=True)

# Команда для получения информации о боте для покупок
@dp.message(Command("shop"))
async def shop_info(message: types.Message):
    await send_and_track(
        message.chat.id,
        f"🛍 Интернет-магазин\n\n"
        f"Бот для покупок: @{PURCHASE_BOT_USERNAME}\n\n"
        f"Нажмите кнопку ниже, чтобы перейти:",
        get_purchase_info_keyboard()
    )
    
    try:
        await message.delete()
    except:
        pass

# Команда для просмотра истории (только для администратора)
@dp.message(Command("history"))
async def show_history(message: types.Message):
    # Проверяем, является ли пользователь администратором
    if message.from_user.id != 123456789:  # Замените на ваш ID
        await send_and_track(
            message.chat.id,
            "❌ У вас нет прав для этой команды",
            get_back_keyboard()
        )
        try:
            await message.delete()
        except:
            pass
        return
    
    history = get_chat_history(message.chat.id)
    
    status = f"📊 История чата:\n"
    status += f"Всего сообщений: {len(history.messages)}\n"
    status += f"ID сообщений: {history.messages}\n"
    status += f"Первое сообщение: {history.first_message_id}\n"
    status += f"Последнее сообщение: {history.get_last_message()}"
    
    await send_and_track(message.chat.id, status, get_back_keyboard())
    
    try:
        await message.delete()
    except:
        pass

# Команда для ручной очистки (только для администратора)
@dp.message(Command("clean"))
async def manual_cleanup(message: types.Message):
    # Проверяем, является ли пользователь администратором
    if message.from_user.id != 123456789:  # Замените на ваш ID
        await send_and_track(
            message.chat.id,
            "❌ У вас нет прав для этой команды",
            get_back_keyboard()
        )
        try:
            await message.delete()
        except:
            pass
        return
    
    history = get_chat_history(message.chat.id)
    
    deleted = await history.cleanup_all_except_last(message.chat.id)
    
    await send_and_track(
        message.chat.id,
        f"🧹 Очистка завершена!\nУдалено сообщений: {deleted}",
        get_back_keyboard()
    )
    
    try:
        await message.delete()
    except:
        pass

async def scheduled_cleanup():
    """Запланированная очистка каждые 24 часа"""
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 часа
        
        print(f"🔄 Запуск плановой очистки: {datetime.now()}")
        
        for chat_id, history in chat_histories.items():
            if history.should_cleanup():
                deleted = await history.cleanup_all_except_last(chat_id)
                
                # Отправляем уведомление об очистке
                try:
                    await send_and_track(
                        chat_id,
                        f"🔄 Меню обновлено!\n\n"
                        f"🏠 Главное меню\n\n"
                        f"Привет! Какой товар тебя интересует сегодня?",
                        get_main_menu_keyboard()
                    )
                except Exception as e:
                    print(f"❌ Ошибка при уведомлении чата {chat_id}: {e}")
                
                print(f"  Чат {chat_id}: удалено {deleted} сообщений")

async def main():
    print("🚀 Бот запущен!")
    print(f"  • Бот для покупок: @{PURCHASE_BOT_USERNAME}")
    print("  • Автоматическая очистка каждые 24 часа")
    
    # Запускаем фоновую задачу очистки
    asyncio.create_task(scheduled_cleanup())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())