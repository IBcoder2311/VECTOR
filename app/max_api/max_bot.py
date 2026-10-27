import asyncio
from maxapi import Bot, Dispatcher
from maxapi.types import MessageCreated
from maxapi.types.attachments.buttons import OpenAppButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from core.config import Config

api_for_max = Config().get_data_maxtoken()

bot = Bot(token=api_for_max)
dp= Dispatcher()


@dp.message_created()
async def start_command(event: MessageCreated):

    builder = InlineKeyboardBuilder()

    builder.add(OpenAppButton(
        text="Открыть VECTOR",
        web_app="https://max.ru/",
        contact_id=event.bot.me.user_id
    ))

    await event.message.answer(text="Добро пожаловать в VECTOR!\n Заходи скорее к нам!", attachments=[builder.as_markup()])


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())