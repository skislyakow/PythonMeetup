from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from asgiref.sync import sync_to_async
from django.utils import timezone

from bot.models.telegram_user import TelegramUser
from bot.models.event import Event
from bot.models.question import Question

ANSWER_QUESTION = 1


@sync_to_async
def is_speaker(user_id):
    return TelegramUser.objects.filter(user_id=user_id, role="speaker").exists()


@sync_to_async
def get_questions(speaker_id):
    return list(
        Question.objects.filter(to_speaker_id=speaker_id, answer__isnull=True)
        .select_related("from_user")
        .order_by("created_at")
    )


@sync_to_async
def get_question(qid):
    return Question.objects.select_related("from_user").get(pk=qid)


@sync_to_async
def save_answer(qid, text):
    q = Question.objects.get(pk=qid)
    q.answer = text
    q.answered_at = timezone.now()
    q.save()
    return q


@sync_to_async
def get_events(speaker_id):
    return list(Event.objects.filter(speaker_id=speaker_id).order_by("start_time"))


@sync_to_async
def get_current_event(speaker_id):
    return Event.objects.filter(speaker_id=speaker_id, is_active=True).first()


@sync_to_async
def get_next_event(speaker_id):
    return Event.objects.filter(
        speaker_id=speaker_id,
        is_active=False,
        start_time__gt=timezone.now(),
    ).order_by("start_time").first()


async def speaker_panel(update, context):
    if not await is_speaker(update.effective_user.id):
        await update.message.reply_text("Нет прав спикера")
        return

    await update.message.reply_text(
        "Панель спикера",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Выступления", callback_data="events")],
            [InlineKeyboardButton("Вопросы", callback_data="questions")],
        ]),
    )


async def events(update, context):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    current = await get_current_event(user_id)
    next_ev = await get_next_event(user_id)
    all_ev = await get_events(user_id)

    text = ""
    if current:
        text += f"Сейчас: {current.title}\nДо {current.end_time.strftime('%H:%M')}\n\n"
    if next_ev:
        text += f"Следующий: {next_ev.title}\nВ {next_ev.start_time.strftime('%H:%M')}\n\n"
    if not current and not next_ev:
        text = "Нет выступлений\n\n"

    for e in all_ev[:5]:
        text += f"{'🟢' if e.is_active else '⏳'} {e.start_time.strftime('%H:%M')} {e.title}\n"

    await query.edit_message_text(
        text or "Нет выступлений",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Обновить", callback_data="events")],
            [InlineKeyboardButton("Назад", callback_data="back")],
        ]),
    )


async def questions(update, context):
    query = update.callback_query
    await query.answer()

    questions_list = await get_questions(query.from_user.id)
    if not questions_list:
        await query.edit_message_text(
            "Нет вопросов",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Обновить", callback_data="questions")],
                [InlineKeyboardButton("Назад", callback_data="back")],
            ]),
        )
        return

    context.user_data["qids"] = [q.id for q in questions_list]
    context.user_data["qi"] = 0
    await show_question(query, questions_list[0], 0, len(questions_list))


async def show_question(query, question, index, total):
    # Все данные уже загружены через select_related в get_question
    from_user_name = question.from_user.full_name if question.from_user else "Аноним"
    
    text = (
        f"Вопрос {index + 1}/{total}\n"
        f"От: {from_user_name}\n"
        f"{question.text or '(пустой вопрос)'}"
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️", callback_data="prev"),
                InlineKeyboardButton("▶️", callback_data="next"),
            ],
            [InlineKeyboardButton("Ответить", callback_data=f"ans_{question.id}")],
            [InlineKeyboardButton("Пропустить", callback_data=f"skip_{question.id}")],
            [InlineKeyboardButton("Назад", callback_data="back")],
        ]),
    )


async def navigate(update, context):
    query = update.callback_query
    await query.answer()

    if "qids" not in context.user_data:
        await query.edit_message_text("Ошибка")
        return

    idx = context.user_data["qi"]
    if query.data == "next" and idx < len(context.user_data["qids"]) - 1:
        idx += 1
    elif query.data == "prev" and idx > 0:
        idx -= 1
    else:
        return

    context.user_data["qi"] = idx
    qid = context.user_data["qids"][idx]
    question = await get_question(qid)
    await show_question(query, question, idx, len(context.user_data["qids"]))


async def skip_question(update, context):
    query = update.callback_query
    await query.answer()

    qid = int(query.data.split("_")[1])
    if "qids" not in context.user_data or qid not in context.user_data["qids"]:
        await query.edit_message_text("Вопрос уже неактивен")
        return

    context.user_data["qids"].remove(qid)
    if not context.user_data["qids"]:
        await query.edit_message_text(
            "Все вопросы обработаны",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back")]
            ]),
        )
        return

    context.user_data["qi"] = 0
    first_qid = context.user_data["qids"][0]
    question = await get_question(first_qid)
    await show_question(query, question, 0, len(context.user_data["qids"]))


async def start_answer(update, context):
    query = update.callback_query
    await query.answer()

    qid = int(query.data.split("_")[1])
    question = await get_question(qid)

    if question.to_speaker_id != query.from_user.id:
        await query.edit_message_text("Не ваш вопрос")
        return

    context.user_data["answer_qid"] = qid
    await query.edit_message_text(
        f"Введите ответ на вопрос:\n\n{question.text}\n\n/cancel — отмена"
    )
    return ANSWER_QUESTION


async def receive_answer(update, context):
    qid = context.user_data.get("answer_qid")
    if not qid:
        await update.message.reply_text("Ошибка")
        return ConversationHandler.END

    question = await save_answer(qid, update.message.text)

    try:
        await context.bot.send_message(
            chat_id=question.from_user_id,
            text=(
                f"Спикер ответил на ваш вопрос:\n\n"
                f"Вопрос: {question.text}\n\n"
                f"Ответ: {update.message.text}"
            ),
        )
        await update.message.reply_text("Ответ отправлен!")
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        await update.message.reply_text("Ответ сохранен, но не отправлен")

    if "qids" in context.user_data and qid in context.user_data["qids"]:
        context.user_data["qids"].remove(qid)

    context.user_data.pop("answer_qid", None)

    if not context.user_data.get("qids"):
        await update.message.reply_text(
            "🎉 Все вопросы отвечены",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back")]
            ]),
        )
        return ConversationHandler.END

    context.user_data["qi"] = 0
    first_qid = context.user_data["qids"][0]
    next_q = await get_question(first_qid)

    from_user_name = next_q.from_user.full_name if next_q.from_user else "Аноним"
    text = (
        f"Вопрос 1/{len(context.user_data['qids'])}\n"
        f"От: {from_user_name}\n"
        f"{next_q.text}"
    )

    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("◀️", callback_data="prev"),
                InlineKeyboardButton("▶️", callback_data="next"),
            ],
            [InlineKeyboardButton("Ответить", callback_data=f"ans_{next_q.id}")],
            [InlineKeyboardButton("Пропустить", callback_data=f"skip_{next_q.id}")],
            [InlineKeyboardButton("Назад", callback_data="back")],
        ]),
    )

    return ConversationHandler.END


async def back(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.edit_message_text(
        "Панель спикера",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Выступления", callback_data="events")],
            [InlineKeyboardButton("Вопросы", callback_data="questions")],
        ]),
    )


async def cancel(update, context):
    await update.message.reply_text("Отменено")
    context.user_data.clear()
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_answer, pattern="^ans_")],
    states={
        ANSWER_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_answer)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

speaker_handlers = [
    CommandHandler("speaker", speaker_panel),
    CallbackQueryHandler(events, pattern="^events$"),
    CallbackQueryHandler(questions, pattern="^questions$"),
    CallbackQueryHandler(back, pattern="^back$"),
    CallbackQueryHandler(navigate, pattern="^(prev|next)$"),
    CallbackQueryHandler(skip_question, pattern="^skip_"),
    conv_handler,
]