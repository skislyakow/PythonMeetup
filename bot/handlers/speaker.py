from functools import wraps
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
from bot.services.keyboards import speaker_keyboard, BUTTON_SPEAKER

ANSWER_QUESTION = 1


def callback_handler(func):
    @wraps(func)
    async def wrapper(update, context, *args, **kwargs):
        query = update.callback_query
        await query.answer()
        return await func(update, context, query, *args, **kwargs)
    return wrapper


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
        reply_markup=speaker_keyboard(),
    )


@callback_handler
async def events(update, context, query):
    user_id = query.from_user.id
    current = await get_current_event(user_id)
    next_ev = await get_next_event(user_id)
    all_ev = await get_events(user_id)

    text = ""
    if current:
        text += f"Сейчас: {current.title}\nДо {current.end_time.strftime('%d.%m %H:%M')}\n\n"
    if next_ev:
        text += f"Следующий: {next_ev.title}\nВ {next_ev.start_time.strftime('%d.%m %H:%M')}\n\n"
    if not current and not next_ev:
        text = "Нет выступлений\n\n"

    for e in all_ev[:5]:
        text += f"{'🟢' if e.is_active else '⏳'} {e.start_time.strftime('%d.%m %H:%M')} {e.title}\n"

    await query.edit_message_text(
        text or "Нет выступлений",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Обновить", callback_data="events")],
            [InlineKeyboardButton("Назад", callback_data="back")],
        ]),
    )


@callback_handler
async def questions(update, context, query):
    await _show_questions(query.from_user.id, query, context, edit=True)


async def show_questions_from_message(update, context):
    user_id = update.effective_user.id
    if not await is_speaker(user_id):
        await update.message.reply_text("Нет прав спикера")
        return

    await _show_questions(user_id, update.message, context, edit=False)


async def _show_questions(user_id, query_or_msg, context, edit=False):
    questions_list = await get_questions(user_id)
    if not questions_list:
        msg = "<b>Нет вопросов</b>"
        if edit:
            await query_or_msg.edit_message_text(msg, parse_mode="HTML")
        else:
            await query_or_msg.reply_text(msg, reply_markup=speaker_keyboard(), parse_mode="HTML")
        return

    context.user_data["qids"] = [q.id for q in questions_list]
    context.user_data["qi"] = 0
    await _display_question(query_or_msg, questions_list[0], 0, len(questions_list), edit)


def _build_question_text(question, index, total):
    from_user_name = question.from_user.full_name if question.from_user else "Аноним"
    return (
        f"── <b>Вопрос {index + 1}/{total}</b> ──\n"
        f"👤 <b>От:</b> {from_user_name}\n\n"
        f"{question.text or '(пустой вопрос)'}"
    )


def _build_question_keyboard(question_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Предыдущий", callback_data="prev")],
        [InlineKeyboardButton("Следующий ▶️", callback_data="next")],
        [InlineKeyboardButton("Ответить", callback_data=f"ans_{question_id}")],
        [InlineKeyboardButton("Пропустить", callback_data=f"skip_{question_id}")],
        [InlineKeyboardButton("Назад", callback_data="back")],
    ])


async def _display_question(query_or_msg, question, index, total, edit=False):
    text = _build_question_text(question, index, total)
    markup = _build_question_keyboard(question.id)
    if edit:
        await query_or_msg.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await query_or_msg.reply_text(text, reply_markup=markup, parse_mode="HTML")


@callback_handler
async def navigate(update, context, query):

    if "qids" not in context.user_data:
        await query.edit_message_text("<b>Ошибка</b>", parse_mode="HTML")
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
    await _display_question(query, question, idx, len(context.user_data["qids"]), edit=True)


@callback_handler
async def skip_question(update, context, query):
    qid = int(query.data.split("_")[1])
    if "qids" not in context.user_data or qid not in context.user_data["qids"]:
        await query.edit_message_text("<b>Вопрос уже неактивен</b>", parse_mode="HTML")
        return

    context.user_data["qids"].remove(qid)
    if not context.user_data["qids"]:
        await query.edit_message_text(
            "<b>Все вопросы обработаны</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back")]
            ]),
            parse_mode="HTML",
        )
        return

    context.user_data["qi"] = 0
    first_qid = context.user_data["qids"][0]
    question = await get_question(first_qid)
    await _display_question(query, question, 0, len(context.user_data["qids"]), edit=True)


@callback_handler
async def start_answer(update, context, query):
    qid = int(query.data.split("_")[1])
    question = await get_question(qid)

    if question.to_speaker_id != query.from_user.id:
        await query.edit_message_text("<b>Не ваш вопрос</b>", parse_mode="HTML")
        return

    context.user_data["answer_qid"] = qid
    await query.edit_message_text(
        f"Введите ответ на вопрос:\n\n{question.text}\n\n/cancel — отмена"
    )
    return ANSWER_QUESTION


async def receive_answer(update, context):
    qid = context.user_data.get("answer_qid")
    if not qid:
        await update.message.reply_text("<b>Ошибка</b>", parse_mode="HTML")
        return ConversationHandler.END

    question = await save_answer(qid, update.message.text)

    try:
        await context.bot.send_message(
            chat_id=question.from_user_id,
            text=(
                f"<b>Спикер ответил на ваш вопрос:</b>\n\n"
                f"<b>Вопрос:</b> {question.text}\n\n"
                f"<b>Ответ:</b> {update.message.text}"
            ),
            parse_mode="HTML",
        )
        await update.message.reply_text("<b>Ответ отправлен!</b>", parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        await update.message.reply_text(
            "<b>Ответ сохранен, но не отправлен</b>", parse_mode="HTML"
        )

    if "qids" in context.user_data and qid in context.user_data["qids"]:
        context.user_data["qids"].remove(qid)

    context.user_data.pop("answer_qid", None)

    if not context.user_data.get("qids"):
        await update.message.reply_text(
            "<b>🎉 Все вопросы отвечены</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Назад", callback_data="back")]
            ]),
            parse_mode="HTML",
        )
        return ConversationHandler.END

    context.user_data["qi"] = 0
    first_qid = context.user_data["qids"][0]
    next_q = await get_question(first_qid)

    text = _build_question_text(next_q, 0, len(context.user_data["qids"]))
    await update.message.reply_text(
        text,
        reply_markup=_build_question_keyboard(next_q.id),
        parse_mode="HTML",
    )

    return ConversationHandler.END


@callback_handler
async def back(update, context, query):
    context.user_data.clear()

    await query.message.delete()
    await query.message.reply_text("Панель спикера", reply_markup=speaker_keyboard())


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
    MessageHandler(filters.Text([BUTTON_SPEAKER]), show_questions_from_message),
    CallbackQueryHandler(events, pattern="^events$"),
    CallbackQueryHandler(questions, pattern="^questions$"),
    CallbackQueryHandler(back, pattern="^back$"),
    CallbackQueryHandler(navigate, pattern="^(prev|next)$"),
    CallbackQueryHandler(skip_question, pattern="^skip_"),
    conv_handler,
]