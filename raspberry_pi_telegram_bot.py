#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This Python script implements the logic behind the Telegram Bot @amusarra-pi (https://t.me/amusarra_rpi_bot).
This Bot interacts through the commands sent by the user with the Relay
and the LCD display connected to the Raspberry.

For more info read this article  https://www.dontesta.it/2020/05/05/primo-maggio-2020-base-raspberry-pi-bot-telegram-display-lcd-rele
"""

import argparse
import sys
import emoji
import telebot
import logging
import time
import RPi.GPIO as GPIO
from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD

__author__ = "Antonio Musarra <antonio.musarra@gmail.com>"
__copyright__ = "Copyright 2020 Antonio Musarra's Blog"
__version__ = "1.0.0"
__license__ = "MIT"

parser = argparse.ArgumentParser(description='Raspberry Pi Telegram Bot.')
parser.add_argument("-d", "--debug", help='Enable debug log in console', action="store_true")
parser.add_argument("-t", "--token", help='Telegram Bot API Token', required=True)
args = parser.parse_args()

# Get the Telegram Bot API Token from program arguments
TOKEN = args.token

# Setting the log level
logger = telebot.logger

if args.debug:
    telebot.logger.setLevel(logging.DEBUG)
else:
    telebot.logger.setLevel(logging.INFO)

# Check I2C address via command i2cdetect -y 1
PCF8574_address = 0x27  # I2C address of the PCF8574 chip.
PCF8574A_address = 0x3F  # I2C address of the PCF8574A chip.

# Create PCF8574 GPIO adapter.
try:
    mcp = PCF8574_GPIO(PCF8574_address)
except:
    try:
        mcp = PCF8574_GPIO(PCF8574A_address)
    except:
        print('I2C Address Error !')
        exit(1)

# Create LCD, passing in MCP GPIO adapter.
lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4, 5, 6, 7], GPIO=mcp)

# Dictionary of relationship between relay identification and BCM pin
dict_relay_bcm = {
    1: 23,
    2: 24,
    3: 25,
    4: 16
}

# Definition and emoji creation for messages to the user.
# For more emoji https://www.webfx.com/tools/emoji-cheat-sheet/
em_bulb = emoji.emojize(':bulb:', use_aliases=True)
em_status_changed = emoji.emojize(':thumbsup:', use_aliases=True)
em_status_on = emoji.emojize(':red_circle:', use_aliases=True)
em_status_off = emoji.emojize(':black_circle:', use_aliases=True)

# Initialize the TeleBot
bot = telebot.TeleBot(TOKEN)


# /start command handler
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message,
                 'Hi! I am the Raspberry Pi 3 Model B+ Telegram Bot made by Antonio Musarra\'s Blog.\n'
                 'If you want more information on how to use this bot, use the /help command and\n'
                 'if you want to learn more, read the article https://www.dontesta.it')

    lcd.clear()
    lcd.message('Welcome on Bot!\n')
    lcd.message(message.from_user.first_name + ' ' + message.from_user.last_name)


# /help command handler
@bot.message_handler(commands=['help'])
def help_command(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.add(
        telebot.types.InlineKeyboardButton(
            'Go to the developer article', url='https://www.dontesta.it')
    )
    bot.send_message(
        message.chat.id,
        'This bot implements the architecture shown in the figure https://bit.ly/ArchitetturaRaspberryPiTelegramBot\n'
        'Through this bot it is possible:\n\n'
        '\t1) Activate and Deactivate one of the four relays using the command /set_relay_status\n'
        '\t2) Check the status of the four relays using the command /get_relay_status\n'
        '\t3) View schema design using the command /get_schema_design\n\n',
        reply_markup=keyboard
    )

    lcd.clear()
    lcd.message('Request Command\n')
    lcd.message('/help')


# /set_relay_status command handler
@bot.message_handler(commands=['set_relay_status'])
def set_relay_status_command(message):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(f'{em_bulb} Relay 1', callback_data='relay-1'),
        telebot.types.InlineKeyboardButton(f'{em_bulb} Relay 2', callback_data='relay-2')
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton(f'{em_bulb} Relay 3', callback_data='relay-3'),
        telebot.types.InlineKeyboardButton(f'{em_bulb} Relay 4', callback_data='relay-4')
    )

    bot.send_message(message.chat.id,
                     'Select one of the Relays for which to change state.\n' +
                     'After change state you can view the new state with \n' +
                     'the command /get_relay_status', reply_markup=keyboard)

    lcd.clear()
    lcd.message('Request Command\n')
    lcd.message('/set_relay_status')


# /get_relay_status command handler
@bot.message_handler(commands=['get_relay_status'])
def get_relay_status_command(message):
    for relay_id, bcm_value in dict_relay_bcm.items():

        if GPIO.input(bcm_value):
            logger.info(f'Input on GPIO {bcm_value} is HIGH')

            bot.send_message(message.chat.id, f'Status of the RelayId {relay_id:d} {em_status_off}')
        else:
            logger.info(f'Input on GPIO {bcm_value} is LOW')

            bot.send_message(message.chat.id, f'Status of the RelayId {relay_id:d} {em_status_on}')

    lcd.clear()
    lcd.message('Request Command\n')
    lcd.message('/get_relay_status')


# /get_schema_design command handler
@bot.message_handler(commands=['get_schema_design'])
def get_schema_design_command(message):
    bot.reply_to(message, 'This is the wiring diagram behind this Telegram bot'
                          ' https://bit.ly/SchemaElettricoRaspberryPiTelegramBot')

    lcd.clear()
    lcd.message('Request Command\n')
    lcd.message('/get_schema_design')


# An inline button click handler
@bot.callback_query_handler(func=lambda call: True)
def inline_query_callback(query):
    data = query.data
    if data.startswith('relay-'):
        set_relay_status_callback(query)


# Implement the relay status callback
def set_relay_status_callback(query):
    relay_id = int(query.data[6:])
    active = False

    logger.info(f'Changing status for Relay {relay_id:d}')
    logger.info(f'BCM Pin for Relay {relay_id:d} is {dict_relay_bcm[relay_id]:d}')

    if GPIO.input(dict_relay_bcm[relay_id]):
        logger.info(f'Input on GPIO {dict_relay_bcm[relay_id]} is HIGH...setting to LOW')

        GPIO.output(dict_relay_bcm[relay_id], GPIO.LOW)

        lcd.clear()
        lcd.message(f'Act. Relay {relay_id:d}\n')
        lcd.message('In listening...')

        active = True
    else:
        logger.info(f'Input on GPIO {dict_relay_bcm[relay_id]} is LOW...setting to HIGH')

        lcd.clear()
        lcd.message(f'De Act. Relay {relay_id:d}\n')
        lcd.message('In listening...')

        GPIO.output(dict_relay_bcm[relay_id], GPIO.HIGH)

    bot.answer_callback_query(query.id)
    send_set_relay_status_result(query.message, relay_id, active)


# Construct and send message status of the relay to user
def send_set_relay_status_result(message, relay_id, active):
    if active:
        emoji = em_status_on
    else:
        emoji = em_status_off

    bot.send_message(message.chat.id, f'{emoji} Changed status of the RelayId {relay_id:d} {em_status_changed}')


# Initialize the GPIO for the relay module
def initialize_relay():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(23, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(24, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(25, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.setup(16, GPIO.OUT, initial=GPIO.HIGH)


# Initialize the I2C LCD 1602 Display
def initialize_lcd():
    mcp.output(3, 1)  # turn on LCD backlight
    lcd.begin(16, 2)  # set number of LCD lines and columns
    lcd.message('Rasp-Pi Telegram\n')
    lcd.message('Bot in action...')


# Resource CleanUp
def destroy():
    print('Raspberry Pi Telegram Bot is shutdown... ')
    print('GPIO CleanUp... ')
    GPIO.cleanup()
    lcd.clear()
    lcd.message('Shutdown...\n')
    lcd.message('I\'m not active')
    lcd.backlight = False


def main_loop():
    initialize_relay()
    initialize_lcd()

    while 1:
        try:
            bot.polling(none_stop=True, timeout=60)
            while 1:
                time.sleep(3)
        except Exception as er:
            destroy()
            print("Unexpected exception: " + str(er))


if __name__ == '__main__':
    try:
        print('Raspberry Pi Telegram Bot is starting...')
        print('Press CTRL+C to terminate Bot')

        main_loop()
    except KeyboardInterrupt:
        destroy()
        sys.exit(0)
