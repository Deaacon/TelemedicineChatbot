import asyncio
import logging
import random
from datetime import datetime, timedelta

from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.executor import start_polling

from scripts import constants, database

bot = Bot(constants.API_TOKEN, parse_mode="HTML")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class MainOrder(StatesGroup):
    start = State()
    functional = State()
    reminder = State()
    fact = State()
    question = State()


class RegistrationOrder(StatesGroup):
    start = State()
    username = State()
    additional_information = State()


class DialogOrder(StatesGroup):
    start = State()
    ask_form = State()
    features = State()


class FormOrder(StatesGroup):
    start = State()
    pressure = State()
    temperature = State()
    finish = State()


class ReminderOrder(StatesGroup):
    start = State()
    time_choose = State()
    date_choose = State()
    finish = State()


class DiaryOrder(StatesGroup):
    start = State()
    read = State()
    write = State()


async def answer_message(
        message: types.Message, 
        message_text: str, 
        reply_texts: list[str] | None = None,
        react_time: float = constants.REACT_TIME
) -> None:
    if reply_texts is None:
        keyboard = types.ReplyKeyboardRemove() # type: ignore
    else:
        keyboard = [[types.KeyboardButton(text)] for text in reply_texts]             # type: ignore
        keyboard = types.ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True) # type: ignore

    await asyncio.sleep(react_time)
    await message.answer(message_text, reply_markup=keyboard) # type: ignore


async def answer_delay(
        message: types.Message,
        message_text: str,
        remind_time: str,
        remind_count: int
) -> None:
    message_text = constants.reminder['reminder_send'] + '\n' + message_text

    day_time = 24 * 60 * 60
    current_datetime = datetime.now()
    
    try:
        time_set = datetime.strptime(remind_time.lower(), 'в %H:%M').time()
    except:
        logging.error('Не удалось определить время!')
        quit(-1)
    time_set = datetime.combine(current_datetime.date(), time_set)
    
    time_difference = time_set - current_datetime
    if time_set < current_datetime:
        time_difference += timedelta(days=1)

    wait_time = time_difference.seconds
    
    await asyncio.sleep(wait_time)
    for i in range(remind_count):
        await message.answer(message_text)
        if i != remind_count - 1:
            await asyncio.sleep(day_time)


def random_choice(
        text_list: list[str]
) -> str:
    idx = random.randint(1, len(text_list))
    text = text_list[idx - 1]
    return text


@dp.message_handler(commands='cancel', state='*')
@dp.message_handler(Text(equals='Отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info('Сброшено состояние %r', current_state)
    await state.finish()
    await answer_message(message, 'Действие отменено.', react_time=0)


@dp.message_handler(commands='about', state='*')
async def cmd_about(message: types.Message):
    await answer_message(message, constants.info['about'], react_time=0)


@dp.message_handler(commands='help', state='*')
async def cmd_help(message: types.Message):
    username = database.read_username(message.from_user.id)
    if username:
        commands_list = ''.join([f'\n/{i} - {constants.botmenu[i]}' for i in constants.botmenu])
        text = constants.info['help'] + commands_list
    else:
        text = constants.info['user_not_set']
    await answer_message(message, text, react_time=0)


@dp.message_handler(commands='question', state='*')
async def cmd_question(message: types.Message):
    await MainOrder.question.set()
    await answer_message(message, constants.info['question'], ['Отмена'])


@dp.message_handler(state=MainOrder.question)
async def question_sent(message: types.Message, state: FSMContext):
    logging_text = message.text.replace('\n', '\n\t')
    logging.info('Задан вопрос:\n\t%s', logging_text)
    database.write_statistics(message.from_user.id, 'Вопрос', message.text)

    await answer_message(message, constants.info['question_reply'])
    await state.reset_state()


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await MainOrder.start.set()

    user_id = message.from_user.id
    username = database.read_username(user_id)

    if username is None:
        await RegistrationOrder.start.set()

        message_text = constants.start_messages['start_message']
        await answer_message(message, message_text)
        
        message_text = database.start_messages['new_user']
        reply_texts = ['Да', 'Отмена']
    else:
        await DialogOrder.start.set()

        message_text = database.start_messages['existing_user'].format(username)
        reply_texts = None
        
    await answer_message(message, message_text, reply_texts)


@dp.message_handler(state=RegistrationOrder.start)
async def start_registration(message: types.Message):
    await RegistrationOrder.username.set()

    username = message.from_user.full_name
    message_text = constants.start_messages['meet_message'].format(username)
    reply_texts = ['Да']

    await answer_message(message, message_text, reply_texts)


@dp.message_handler(state=RegistrationOrder.username)
async def define_username(message: types.Message, state: FSMContext):

    user_id = message.from_user.id

    if message.text.lower() == 'да':
        username = message.from_user.full_name
    else:
        username = message.text

    database.write_username(user_id, username)
    database.write_statistics(user_id, 'Новый пользователь', str(user_id))

    await state.finish()
    await DialogOrder.start.set()

    message_text = constants.start_messages['existing_user'].format(username)
    await answer_message(message, message_text)


async def dialog_functions(message: types.Message):
    await MainOrder.functional.set()

    message_text = constants.dialog['advice']
    reply_texts = ['Интересный факт', 'Напоминания', 'Опрос', 'Дневник']
    await answer_message(message, message_text, reply_texts)


@dp.message_handler(content_types=types.ContentTypes.TEXT, state=DialogOrder.start)
async def start_dialog(message: types.Message):
    await DialogOrder.features.set()

    message_text = random_choice(constants.dialog['reply'])
    await answer_message(message, message_text)

    await dialog_functions(message)


@dp.message_handler(Text(equals='Опрос', ignore_case=True), state=MainOrder.functional)
async def start_form(message: types.Message):
    message_text = constants.form['form_start']
    await answer_message(message, message_text)
    await FormOrder.start.set()


@dp.message_handler(state=FormOrder.start)
async def state_form(message: types.Message, state: FSMContext):
    await state.update_data(state_user=message.text)
    message_text = constants.form['form_pressure']
    await answer_message(message, message_text)
    await FormOrder.pressure.set()


@dp.message_handler(state=FormOrder.pressure)
async def pressure_form(message: types.Message, state: FSMContext):
    await state.update_data(pressure_user=message.text)
    message_text = constants.form['form_temperature']
    await answer_message(message, message_text)
    await FormOrder.temperature.set()


@dp.message_handler(state=FormOrder.temperature)
async def temperature_form(message: types.Message, state: FSMContext):
    await state.update_data(temperature_user=message.text)
    message_text = constants.form['form_blood']
    await answer_message(message, message_text)
    await FormOrder.finish.set()


@dp.message_handler(state=FormOrder.finish)
async def finish_form(message: types.Message, state: FSMContext):
    await state.update_data(blood_user=message.text)
    data = await state.get_data()

    database.write_forms(message.from_user.id, data)
    await state.finish()
    
    await DialogOrder.features.set()

    message_text = constants.form['form_finish']
    await answer_message(message, message_text)
    
    await dialog_functions(message)


@dp.message_handler(Text(equals='Напоминания', ignore_case=True), state=MainOrder.functional)
async def start_reminder(message: types.Message):
    message_text = constants.reminder['reminder_start']
    await answer_message(message, message_text)
    await ReminderOrder.time_choose.set()


@dp.message_handler(state=ReminderOrder.time_choose)
async def time_choose_reminder(message: types.Message, state: FSMContext):
    await state.update_data(reminder_message=message.text)

    message_text = constants.reminder['reminder_time']
    reply_texts = ['В 12:00', 'В 16:00', 'В 18:00', 'В 20:00']
    await answer_message(message, message_text, reply_texts)

    await ReminderOrder.date_choose.set()


@dp.message_handler(state=ReminderOrder.date_choose)
async def date_choose_reminder(message: types.Message, state: FSMContext):
    await state.update_data(time_message=message.text)

    message_text = constants.reminder['reminder_date']
    reply_texts = ['1', '3', '7', '30']
    await answer_message(message, message_text, reply_texts)

    await ReminderOrder.finish.set()
    

@dp.message_handler(state=ReminderOrder.finish)
async def finish_reminder(message: types.Message, state: FSMContext):
    reminder_count = int(message.text)

    state_data = await state.get_data()

    message_text = constants.reminder['reminder_finish']
    message_text = message_text.format(state_data['time_message'].lower())
    await answer_message(message, message_text)
    
    message_text = state_data['reminder_message']
    time_str = state_data['time_message']
    asyncio.ensure_future(answer_delay(message, message_text, time_str, reminder_count))
    
    await state.finish()
    await dialog_functions(message)


@dp.message_handler(Text(equals='Интересный факт', ignore_case=True), state=MainOrder.functional)
async def start_fact(message: types.Message, state: FSMContext):
    await state.reset_state()

    message_text = constants.dialog['fact']
    await answer_message(message, message_text)
    
    message_text = random_choice(constants.facts)
    await answer_message(message, message_text)

    message_text = constants.dialog['fact_end']
    await answer_message(message, message_text)

    await dialog_functions(message)


@dp.message_handler(Text(equals='Дневник', ignore_case=True), state=MainOrder.functional)
async def start_diary(message: types.Message):
    message_text = constants.diary['diary_start']
    reply_texts = ['Записать', 'Прочитать записи']
    await answer_message(message, message_text, reply_texts)
    await DiaryOrder.start.set()


@dp.message_handler(Text(equals='Записать', ignore_case=True), state=DiaryOrder.start)
async def write_diary(message: types.Message):
    message_text = constants.diary['diary_write']
    await answer_message(message, message_text)
    await DiaryOrder.write.set()


@dp.message_handler(state=DiaryOrder.write)
async def done_diary(message: types.Message, state: FSMContext):
    database.write_diary(message.from_id, message.text)

    message_text = constants.diary['diary_done']
    await answer_message(message, message_text)
    await state.finish()

    await dialog_functions(message)


@dp.message_handler(Text(equals='Прочитать записи', ignore_case=True), state=DiaryOrder.start)
async def read_diary(message: types.Message, state: FSMContext):
    message_text = constants.diary['diary_read']
    await answer_message(message, message_text)

    diary_data = database.read_diary(message.from_id)

    if diary_data:
        for date, time, text in diary_data:
            message_text = f'Сообщение от {date} {time}:\n\t{text}'
            await answer_message(message, message_text, react_time=0)
    else:
        message_text = constants.diary['diary_empty']
        await answer_message(message, message_text, react_time=0)
    
    await state.finish()
    await dialog_functions(message)


async def on_startup(dispatcher):
    commands = [types.BotCommand(i, constants.botmenu[i]) for i in constants.botmenu]
    await bot.set_my_commands(commands)


def start_bot():
    database.initializate_database()
    start_polling(dp, on_startup=on_startup)
