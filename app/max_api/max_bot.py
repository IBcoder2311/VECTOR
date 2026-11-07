import asyncio
import logging
from itertools import count
from pathlib import Path
from maxapi import Bot, Dispatcher
from maxapi.context import MemoryContext, State, StatesGroup
from maxapi.types import (
    BotCommand,
    BotStarted,
    CallbackButton,
    Command,
    InputMedia,
    MessageCallback,
    MessageCreated,
)
from maxapi.types.attachments.buttons import OpenAppButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder
from app.db.database import SessionFactory
from app.db.crud import (
    get_user_by_id,
    get_user_by_max_id,
    update_user_status,
    get_notifications,
    delete_notification,
)
from core.config import Config



logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config()
bot = Bot(token=config.get_data_maxtoken())
dp = Dispatcher()

class OrgApplication(StatesGroup):
    description = State()

class ReportApplication(StatesGroup):
    description = State()

pending_org_requests: dict[int, dict] = {}
active_org_requests: dict[str, int] = {}
last_org_results: dict[str, str] = {}
request_counter = count(1)
request_lock = asyncio.Lock()


def get_admin_ids() -> set[int]:
    return config.get_admin_max_ids()


async def get_vector_user(max_id: int | str):
    async with SessionFactory() as session:
        return await get_user_by_max_id(session, str(max_id))


async def send_welcome(chat_id: int):
    builder = InlineKeyboardBuilder()
    builder.add(
        OpenAppButton(
            text="Открыть VECTOR",
            web_app=bot.me.username,
            contact_id=bot.me.user_id,
        )
    )

    await bot.send_message(
        chat_id=chat_id,
        text=(
            "Добро пожаловать в VECTOR!\n\n"
            "Здесь ты можешь находить единомышленников, "
            "создавать проекты и собирать команды.\n\n"
            "Нажми кнопку ниже, чтобы начать!"
        ),
        attachments=[builder.as_markup()],
    )


@dp.bot_started()
async def bot_started(event: BotStarted):
    await send_welcome(event.chat_id)


@dp.message_created(Command("start"))
async def start_command(event: MessageCreated):
    await send_welcome(event.message.recipient.chat_id)


@dp.message_created(Command("about"))
async def about_command(event: MessageCreated):
    about_image = (
        Path(__file__).resolve().parents[2]
        / "frontend"
        / "static"
        / "img"
        / "vector_about.png"
    )

    await event.message.answer(
        text=(
            "VECTOR — платформа для поиска единомышленников "
            "и создания команд.\n\n"
            "Создавай идеи, находи участников и развивай проекты!"
        ),
        attachments=[InputMedia(path=str(about_image))],
    )


@dp.message_created(Command("send_org"))
async def send_org_command(event: MessageCreated, context: MemoryContext):
    sender = event.message.sender
    if sender is None:
        await event.message.answer("Не удалось определить твой MAX ID. Попробуй ещё раз в личном чате с ботом.")
        return

    max_id = str(sender.user_id)
    admin_ids = get_admin_ids()

    if not admin_ids:
        await event.message.answer("Приём заявок временно недоступен: у проекта не настроены администраторы.")
        return

    user = await get_vector_user(max_id)
    if user is None:
        await event.message.answer(
            "Сначала открой Mini App VECTOR и авторизуйся, "
            "затем вернись сюда и отправь /send_org ещё раз."
        )
        return

    if user.status in {"organizer", "admin"} or int(max_id) in admin_ids:
        await event.message.answer("У тебя уже есть права организатора или администратора.")
        return

    if max_id in active_org_requests:
        await event.message.answer("Твоя заявка уже отправлена и ожидает рассмотрения.")
        return

    await context.set_state(OrgApplication.description)
    await event.message.answer(
        "Расскажи, почему хочешь стать организатором VECTOR и чем планируешь заниматься.\n\n"
        "Напиши одним сообщением (от 30 до 1000 символов). Для отмены отправь /cancel."
    )


@dp.message_created(OrgApplication.description)
async def receive_org_description(event: MessageCreated, context: MemoryContext):
    body = event.message.body
    text = (body.text or "").strip() if body else ""
    sender = event.message.sender

    if sender is None:
        await context.clear()
        await event.message.answer("Не удалось определить отправителя. Начни заявку заново: /send_org")
        return

    if text.lower().split(maxsplit=1)[0:1] == ["/cancel"]:
        await context.clear()
        await event.message.answer("Подача заявки отменена.")
        return

    if len(text) < 30:
        await event.message.answer("Описание слишком короткое. Напиши хотя бы 30 символов.")
        return

    if len(text) > 1000:
        await event.message.answer("Описание слишком длинное. Максимум — 1000 символов.")
        return

    max_id = str(sender.user_id)
    user = await get_vector_user(max_id)
    if user is None:
        await context.clear()
        await event.message.answer("Не нашёл твой аккаунт VECTOR. Открой Mini App, затем начни заново: /send_org")
        return

    if max_id in active_org_requests:
        await context.clear()
        await event.message.answer("У тебя уже есть заявка на рассмотрении.")
        return

    request_id = next(request_counter)
    pending_org_requests[request_id] = {
        "user_id": user.id,
        "max_id": max_id,
        "name": user.name,
        "description": text,
    }
    active_org_requests[max_id] = request_id
    last_org_results[max_id] = "pending"
    await context.clear()

    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        CallbackButton(text="Одобрить", payload=f"org:approve:{request_id}"),
        CallbackButton(text="Отклонить", payload=f"org:reject:{request_id}"),
    )

    admin_text = (
        "📩 Новая заявка на роль организатора VECTOR\n\n"
        f"Пользователь: {user.name}\n"
        f"MAX ID: {max_id}\n"
        f"ID аккаунта VECTOR: {user.id}\n\n"
        f"Описание заявки:\n{text}"
    )

    sent_count = 0
    for admin_id in get_admin_ids():
        try:
            await bot.send_message(
                user_id=admin_id,
                text=admin_text,
                attachments=[keyboard.as_markup()],
            )
            sent_count += 1
        except Exception:
            logger.exception("Не удалось отправить заявку администратору MAX ID %s", admin_id)

    if sent_count == 0:
        pending_org_requests.pop(request_id, None)
        active_org_requests.pop(max_id, None)
        last_org_results.pop(max_id, None)
        await event.message.answer(
            "Не получилось доставить заявку администраторам. "
            "Убедись, что они запускали бота, и попробуй позже."
        )
        return

    await event.message.answer("✅ Заявка отправлена администрации VECTOR. Я сообщу, когда её рассмотрят.")


@dp.message_callback()
async def handle_org_decision(event: MessageCallback):
    payload = event.callback.payload or ""
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "org" or parts[1] not in {"approve", "reject"}:
        return

    _, admin_id = event.get_ids()
    if admin_id not in get_admin_ids():
        await event.answer(notification="У тебя нет прав для рассмотрения заявок.")
        return

    try:
        request_id = int(parts[2])
    except ValueError:
        await event.answer(notification="Некорректный номер заявки.")
        return

    async with request_lock:
        application = pending_org_requests.get(request_id)
        if application is None:
            await event.answer(notification="Эта заявка уже рассмотрена или больше недоступна.")
            return

        if parts[1] == "approve":
            async with SessionFactory() as session:
                user = await get_user_by_id(session, application["user_id"])
                if user is None:
                    pending_org_requests.pop(request_id, None)
                    active_org_requests.pop(application["max_id"], None)
                    await event.answer(notification="Пользователь больше не найден в VECTOR.")
                    return

                await update_user_status(session, user.id, "organizer")

            result_text = "✅ Заявка одобрена. Пользователю выдана роль организатора."
            user_text = "🎉 Твою заявку одобрили! Теперь у тебя есть роль организатора VECTOR."
            last_org_results[application["max_id"]] = "approved"
        else:
            result_text = "Заявка отклонена."
            user_text = "Твою заявку на роль организатора VECTOR пока не одобрили. Ты можешь подать её повторно командой /send_org."
            last_org_results[application["max_id"]] = "rejected"

        pending_org_requests.pop(request_id, None)
        active_org_requests.pop(application["max_id"], None)

    await event.answer(new_text=result_text, attachments=[])

    try:
        await bot.send_message(
            user_id=int(application["max_id"]),
            text=user_text,
        )
    except Exception:
        logger.exception("Не удалось уведомить пользователя MAX ID %s о решении по заявке", application["max_id"])


@dp.message_created(Command("my_status"))
async def my_status_command(event: MessageCreated):
    sender = event.message.sender
    if sender is None:
        await event.message.answer("Не удалось определить твой MAX ID.")
        return

    max_id = str(sender.user_id)
    user = await get_vector_user(max_id)
    if user is None:
        await event.message.answer("Сначала открой Mini App VECTOR и авторизуйся.")
        return

    if int(max_id) in get_admin_ids() or user.status == "admin":
        role = "Администратор"
    elif user.status in {"organizer", "organization"}:
        role = "Организатор"
    else:
        role = "Пользователь"

    application_status = last_org_results.get(max_id)
    status_text = {
        "pending": "Заявка на организатора: на рассмотрении",
        "approved": "Последняя заявка на организатора: одобрена",
        "rejected": "Последняя заявка на организатора: отклонена",
    }.get(application_status, "Заявок на организатора нет")

    await event.message.answer(
        f"Твой статус в VECTOR\n\nРоль: {role}\n{status_text}"
    )


@dp.message_created(Command("report"))
async def report_command(event: MessageCreated, context: MemoryContext):
    if not get_admin_ids():
        await event.message.answer(
            "Отправка обращений временно недоступна."
        )
        return

    await context.set_state(ReportApplication.description)

    await event.message.answer(
        "Опиши проблему или предложение для администрации VECTOR.\n\n"
        "Напиши одним сообщением (от 10 до 2000 символов).\n"
        "Для отмены отправь /cancel."
    )

@dp.message_created(ReportApplication.description)
async def receive_report(event: MessageCreated, context: MemoryContext):
    body = event.message.body
    text = (body.text or "").strip() if body else ""
    sender = event.message.sender

    if sender is None:
        await context.clear()
        await event.message.answer("Не удалось определить отправителя.")
        return

    if text.lower().split(maxsplit=1)[0:1] == ["/cancel"]:
        await context.clear()
        await event.message.answer("Отправка обращения отменена.")
        return

    if len(text) < 10:
        await event.message.answer(
            "Слишком короткое обращение. Напиши хотя бы 10 символов."
        )
        return

    if len(text) > 2000:
        await event.message.answer(
            "Обращение слишком длинное. Максимум — 2000 символов."
        )
        return

    max_id = str(sender.user_id)
    user = await get_vector_user(max_id)

    name = user.name if user else "Не зарегистрирован в VECTOR"

    admin_text = (
        "📨 Новое обращение VECTOR\n\n"
        f"Пользователь: {name}\n"
        f"MAX ID: {max_id}\n\n"
        f"Сообщение:\n{text}"
    )

    sent_count = 0

    for admin_id in get_admin_ids():
        try:
            await bot.send_message(
                user_id=admin_id,
                text=admin_text,
            )
            sent_count += 1
        except Exception:
            logger.exception(
                "Не удалось отправить обращение администратору %s",
                admin_id,
            )

    await context.clear()

    if sent_count == 0:
        await event.message.answer(
            "Не удалось доставить обращение администрации. "
            "Попробуй позже."
        )
        return

    await event.message.answer(
        "✅ Обращение отправлено администрации VECTOR. Спасибо!"
    )

async def notification_listener():
    while True:
        try:
            async with SessionFactory() as session:
                notifications = await get_notifications(session, limit=10)

                for notification in notifications:
                    try:
                        user = await get_user_by_id(
                            session,
                            notification.user_id,
                        )

                        if user is None:
                            await delete_notification(session, notification.id)
                            continue

                        await bot.send_message(
                            user_id=int(user.max_id),
                            text=notification.message,
                        )

                        await delete_notification(
                            session,
                            notification.id,
                        )

                        logging.info(
                            "Уведомление %s отправлено пользователю %s",
                            notification.id,
                            user.max_id,
                        )

                    except Exception:
                        logging.exception(
                            "Не удалось отправить уведомление %s",
                            notification.id,
                        )

        except Exception:
            logging.exception("Ошибка listener уведомлений")

        await asyncio.sleep(5)

async def main():
    await bot.set_commands(
        BotCommand(name="start", description="Открыть VECTOR"),
        BotCommand(name="send_org", description="Подать заявку на организатора"),
        BotCommand(name="about", description="Информация о проекте"),
        BotCommand(name="my_status", description="Моя роль и статус заявки"),
        BotCommand(name="report", description="Сообщить о проблеме"),
    )

    listener_task = asyncio.create_task(
        notification_listener()
    )

    try:
        await dp.start_polling(bot)
    finally:
        listener_task.cancel()

        try:
            await listener_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
