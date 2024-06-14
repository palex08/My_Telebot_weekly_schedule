import json
import os
import threading
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Убедитесь, что токен был загружен корректно
if not TOKEN:
    raise ValueError("No TELEGRAM_BOT_TOKEN found in environment variables")

bot = telebot.TeleBot(TOKEN)

schedule_file = 'schedule.json'

commands = [
    telebot.types.BotCommand('/start', 'Запустить бота'),
    telebot.types.BotCommand('/help', 'Помощь'),
    telebot.types.BotCommand('/day_manager', 'Управление расписанием'),
    telebot.types.BotCommand('/weekly_schedule', 'Расписание на неделю'),
    telebot.types.BotCommand('/reminder_list', 'Список напоминаний')

]

bot.set_my_commands(commands)
def load_schedule():
    """Loads schedule data from a JSON file."""
    if os.path.exists(schedule_file):
        with open(schedule_file, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data.get('schedule', {}), data.get('reminders', [])
    else:
        return {}, []

def save_schedule(schedule, reminders):
    """Saves schedule and reminders data to a JSON file."""
    data = {'schedule': schedule, 'reminders': reminders}
    with open(schedule_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def start_markup():
    """Creates and returns the initial reply keyboard markup for the bot."""
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    markup.add('Менеджер расписания', 'Показать расписание на неделю', 'Показать установленные напоминания')
    return markup

def day_action_markup():
    """Creates and returns the reply keyboard markup for daily actions."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Добавить событие', 'Показать расписание', 'Удалить событие', 'Добавить напоминание',
               'Удалить напоминание')
    return markup

def day_schedule_markup():
    """Creates and returns the reply keyboard markup for selecting a day of the week."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add('Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье')
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    """Handles the '/start' command sent by the user."""
    msg = bot.send_message(message.chat.id,
                           'Привет, {0.first_name}! \nЯ бот для управления расписанием. \nВыбери команду'.format(
                               message.from_user), reply_markup=start_markup())
    bot.register_next_step_handler(msg, start_perform_actions)

@bot.message_handler(commands=['help'])
def help(message):
    """Provides a help message including a list of all available bot commands."""
    help_text = """
Привет! Вот список команд, которые я могу выполнить:
/start - начать работу с ботом
/help - получить список доступных команд
/day_manager - получить расписание на выбранный день недели, добавить или удалить событие, установить напоминание
/weekly_schedule - получить расписание на всю неделю
/reminder_list - получить список установленных напоминаний

"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['day_manager'])
def day_schedule(message):
    """Allows the user to manage the schedule for a specific day."""
    msg = bot.send_message(message.chat.id, 'Выберите день недели:', reply_markup=day_schedule_markup())

@bot.message_handler(commands=['weekly_schedule'])
def weekly_schedule(message):
    """Shows the schedule for the entire week."""
    show_weekly_schedule(message)

@bot.message_handler(commands=['reminder_list'])
def reminder_list(message):
    """Lists all set reminders."""
    show_reminders(message)

@bot.message_handler(
    func=lambda message: message.text in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота',
                                          'Воскресенье'])
def handle_day(message):
    day = message.text
    msg = bot.send_message(message.chat.id, f"Выберите действие для дня {day}:", reply_markup=day_action_markup())
    bot.register_next_step_handler(msg, day_perform_action, day)

def start_perform_actions(message):
    """Determines actions based on user's choice from the start menu."""
    if message.text == 'Менеджер расписания':
        msg = bot.send_message(message.chat.id, 'Выберите день недели:', reply_markup=day_schedule_markup())
    elif message.text == 'Показать расписание на неделю':
        show_weekly_schedule(message)
    elif message.text == 'Показать установленные напоминания':
        show_reminders(message)

def show_weekly_schedule(message):
    """Compiles and sends the weekly schedule to the user."""
    schedule, _ = load_schedule()
    response = ""
    for day in ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']:
        day_schedule = schedule.get(day, {})
        if day_schedule:
            sorted_events = sorted(day_schedule.items())
            events_str = "\n".join(f"{time} - {event}" for time, event in sorted_events)
            response += f"{day}:\n{events_str}\n"
        else:
            response += f"{day}: пока нет запланированных событий.\n"
    bot.send_message(message.chat.id, response.strip())

def show_reminders(message):
    """Sorts and displays all reminders to the user."""
    _, reminders = load_schedule()
    if reminders != []:
        # Sorting the reminders by time
        sorted_reminders = sorted(reminders, key=parse_time)

        # Create a response string with all reminders
        response = "Установленные напоминания:\n"
        for reminder in sorted_reminders:
            response += f"{reminder['time']} - {reminder['message']}\n"
        bot.send_message(message.chat.id, response.strip())
    else:
        bot.send_message(message.chat.id, "Нет установленных напоминаний.")

def day_perform_action(message, day):
    """Handles actions related to daily schedule management based on user input."""
    if message.text == 'Добавить событие':
        msg = bot.send_message(message.chat.id,
                               f"Введите время и описание события для {day} в формате 'ЧЧ:ММ Событие':")
        bot.register_next_step_handler(msg, add_event, day)
    elif message.text == 'Показать расписание':
        show_schedule(message, day)
    elif message.text == 'Удалить событие':
        delete_event_prompt(message, day)
    elif message.text == 'Добавить напоминание':
        set_reminders(message, day)
    elif message.text == 'Удалить напоминание':
        delete_reminder(message)


def add_event(message, day):
    """Adds a new event to the schedule for a specified day."""
    try:
        time, event = message.text.split(maxsplit=1)
        schedule, reminders = load_schedule()
        if day not in schedule:
            schedule[day] = {}
        schedule[day][time] = event
        save_schedule(schedule, reminders)
        bot.send_message(message.chat.id, f"Событие '{event}' добавлено на {time} в {day}.")

    except ValueError:
        bot.send_message(message.chat.id, "Неправильный формат ввода. Пожалуйста, используйте формат 'ЧЧ:ММ Событие'.")
    day_schedule(message)

def show_schedule(message, day):
    """Displays the schedule for a specified day."""

    # Correctly unpack the tuple returned by load_schedule
    schedule, _ = load_schedule()
    # Check if the day exists in the schedule and has events
    if day in schedule and schedule[day]:
        # Sort the day's schedule by time
        sort_day_schedule = {key: schedule[day][key] for key in sorted(schedule[day])}
        # Create a response string with all events of that day
        response = f"Расписание на {day}:\n" + "\n".join(
            f"{time} - {event}" for time, event in sort_day_schedule.items())
    else:
        # Provide a response indicating no events are scheduled for that day
        response = f"На {day} пока нет запланированных событий."

    # Send the response to the user
    bot.send_message(message.chat.id, response)
    day_schedule(message)

def delete_event_prompt(message, day):
    """Prompts user to select an event for deletion."""
    schedule, _ = load_schedule()
    if day in schedule and schedule[day]:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for time in schedule[day]:
            markup.add(time)
        msg = bot.send_message(message.chat.id, "Выберите время события для удаления:", reply_markup=markup)
        bot.register_next_step_handler(msg, delete_event, day)
    else:
        bot.send_message(message.chat.id, "В этот день нет запланированных событий для удаления.")
        day_schedule(message)

def delete_event(message, day):
    """Deletes a selected event from the schedule."""
    time = message.text
    schedule, reminders = load_schedule()
    if day in schedule and time in schedule[day]:
        del schedule[day][time]
        save_schedule(schedule, reminders)
        bot.send_message(message.chat.id, f"Событие в {time} удалено из расписания.")
    else:
        bot.send_message(message.chat.id, "Событие не найдено.")
    day_schedule(message)

def set_reminders(message, day):
    """Sets a reminder for a specified day based on user input."""
    chat_id = message.chat.id
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    today = datetime.now()
    target_weekday = days_of_week.index(day)
    days_until_target = (target_weekday - today.weekday()) % 7

    if days_until_target == 0:
        next_date = today
    else:
        next_date = today + timedelta(days=days_until_target)

    msg = bot.send_message(chat_id,
                           f"Введите время и текст напоминания для {day}, {next_date.strftime('%d-%m-%Y')} в формате 'ЧЧ:ММ Текст напоминания':")
    bot.register_next_step_handler(msg, process_reminder_input, day, next_date)


def process_reminder_input(message, day, next_date):
    """Processes user input for setting a reminder."""
    try:
        time_str, reminder_text = message.text.split(maxsplit=1)
        reminder_time = datetime.strptime(f"{next_date.strftime('%d-%m-%Y')} {time_str}", "%d-%m-%Y %H:%M")
        if reminder_time < datetime.now():
            raise ValueError("Past time")
    except ValueError:
        bot.send_message(message.chat.id,
                         "Неправильный формат ввода или время уже прошло. Пожалуйста, используйте формат 'ЧЧ:ММ Текст напоминания'.")
        return set_reminders(message, day)

    schedule, reminders = load_schedule()
    reminders.append({
        'time': reminder_time.strftime("%d-%m-%Y %H:%M"),
        'chat_id': message.chat.id,
        'message': reminder_text
    })
    save_schedule(schedule, reminders)
    bot.send_message(message.chat.id, f"Напоминание установлено на {day} {reminder_time.strftime('%d-%m-%Y %H:%M')}.")


def parse_time(reminder):
    """Converts a string time from a reminder into a datetime object for sorting."""
    return datetime.strptime(reminder["time"], "%d-%m-%Y %H:%M")


def delete_reminder(message):
    """Initiates the process to delete a reminder."""
    schedule, reminders = load_schedule()
    if reminders != []:
        to_del_reminders = sorted(reminders, key=parse_time)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for reminder in to_del_reminders:
            button_text = f"{reminder['message']}:{reminder['time']}"
            markup.add(button_text)
        msg = bot.send_message(message.chat.id, "Выберите время события для удаления:", reply_markup=markup)
        bot.register_next_step_handler(msg, delete_reminder_event)
    else:
        bot.send_message(message.chat.id, "Нет установленных напоминаний.")


def delete_reminder_event(message):
    """Deletes a selected reminder based on user input."""
    schedule, reminders = load_schedule()
    reminder_text, time = message.text.split(':', maxsplit=1)
    print(time)
    for reminder in reminders:
        print(reminder['time'])
        if time == reminder['time']:
            reminders.remove(reminder)
            bot.send_message(message.chat.id,
                             f"Напоминание {reminder['message']}: {reminder['time']} удалено из списка.")
    save_schedule(schedule, reminders)


def send_reminders():
    """Checks and sends reminders at their scheduled time."""

    while True:
        schedule, reminders = load_schedule()
        now = datetime.now()
        for reminder in reminders[:]:  # Create a copy of the list for safe removal
            reminder_time = datetime.strptime(reminder['time'], "%d-%m-%Y %H:%M")
            if reminder_time <= now:
                for i in range(3):
                    bot.send_message(reminder['chat_id'], "Напоминание: " + reminder['message'] + '!!!!!!!')
                reminders.remove(reminder)
                save_schedule(schedule, reminders)
                time.sleep(60)
        time.sleep(1)

def setup_reminder_thread():
    """Sets up a background thread to continuously send reminders."""
    reminder_thread = threading.Thread(target=send_reminders)
    #reminder_thread.daemon = True
    reminder_thread.start()


if __name__ == '__main__':
    setup_reminder_thread()
    bot.polling(none_stop=True)
