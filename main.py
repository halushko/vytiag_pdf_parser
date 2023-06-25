import PyPDF2
import os
import re
import csv
import datetime
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

object_type = 'Тип об’єкта:'
description = 'Опис об’єкта:'
square = 'Загальна площа (кв.м):'
square_leave = ', житлова площа (кв.м):'
price_mn = 'Ціна'
address = 'Адреса:'
address_real = 'будинок'
info_zagolovok = 'Актуальна інформація про речове право'
chast = 'Розмір частки:'
owner = 'Власники:'
ipn = 'платника податків:'
stor = 'стор'
start_text = 'Актуальна інформація про об’єкт речових прав'
vidomosti = 'Відомості'
enter = '\''

def find_between(page_text, left, *rights):
    texts = []

    pt = page_text
    flag = 1
    left_index = pt.find(left)

    while flag == 1 and left_index != -1:
        text = ''
        next_left = pt.find(left, left_index + 1)
        if next_left == -1:
            next_left = len(pt)
            flag = 0
        for right in rights:
            right_index = pt.find(right, left_index + 1)
            if right_index != -1 and right_index < next_left:
                text1 = pt[left_index + len(left):right_index].strip()
                if text1 != '' and text == '' or len(text1) < len(text):
                    text = text1

        if text == '':
            text = pt[left_index + len(left):next_left]
        pt = pt[next_left:]
        texts.append(text.strip())
        left_index = 0
    return texts


pdf_folder = r'/app/files'


def sstr(array):
    res = ''
    for a in array:
        res = res + re.sub(r'\n', ' && ', a) + '\n'
    return '\'' + res.strip()


def parse():
    # Проходим по всем файлам в папке и извлекаем текст
    print(f'Folder  {pdf_folder}')
    today = datetime.datetime.today()
    csv_path = today.strftime('%Y-%m-%d ') + str(today.hour) + '-' + str(today.minute) + '-' + str(
        today.second) + '.csv'
    print(csv_path)

    with open(csv_path, 'w', newline='', encoding='Windows-1251') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['№', 'Файл', 'Площа', 'Будинок', 'Квартира', 'Частка', 'Власник', 'ІПН власника', 'Заборона у файлі'])
        nom = 0

        for filename in os.listdir(pdf_folder):
            if filename.endswith('pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    page_text = ''
                    for page_num, page in enumerate(pdf_reader.pages):
                        page_text = page_text + page.extract_text() + '\n'
                    ranges = []
                    start_index = page_text.find(start_text)
                    if start_index > 0:
                        ranges.append(page_text[0:start_index])
                    ranges.extend(find_between(page_text[start_index:], start_text, start_text))

                    for rng in ranges:
                        square_val = []
                        address_val_res = []
                        chast_val = []
                        owner_val_res = []
                        ipn_val = []
                        zaborona_val = []

                        zaborona_val.extend(find_between(rng, 'заборона на нерухоме майно', ' ', ',', '.', vidomosti))
                        square_val.extend(find_between(rng, square, square_leave, price_mn, address, stor, ', житлова', vidomosti))
                        address_val = find_between(rng, address, info_zagolovok, 'ВІДОМОСТІ', stor, vidomosti)
                        for av in address_val:
                            env_value = os.getenv(
                                'BUILD_ADDRESSES')
                            if env_value:
                                values = env_value.split(';')
                                avr = av
                                for value in values:
                                    avr = re.sub('м.Київ, вулиця ' + value + ', будинок', '', av).strip()
                                address_val_res.append(avr)
                            else:
                                print("Змінна не знайдена")

                        chast_val.extend(find_between(rng, chast, price_mn, info_zagolovok, 'ВІДОМОСТІ', owner, stor, vidomosti))
                        for ov in find_between(rng, owner, 'ВІДОМОСТІ', ipn, ',', stor, vidomosti):
                            ovr = re.sub(r'[\n]', ' ', ov)
                            ovr = re.sub('ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ', 'ТОВ', ovr)
                            ovr = re.sub('\" КОМПАНІЯ З УПРАВЛІННЯ АКТИВАМИ', '', ovr)
                            owner_val_res.append(ovr)
                        ipn_val.extend(find_between(rng, ipn, 'ВІДОМОСТІ', vidomosti, ','))
                        nom = nom + 1
                        address_full = sstr(address_val_res)
                        kv = '\'' + address_full[address_full.rfind(' '):].strip()
                        bud = address_full[0:address_full.rfind(' ')+1].strip()
                        writer.writerow([nom, filename,
                                         sstr(square_val),
                                         bud,
                                         kv,
                                         sstr(chast_val),
                                         sstr(owner_val_res),
                                         sstr(ipn_val),
                                         sstr(zaborona_val)])

# Обработчик команды /start
async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привіт, я вмію парсити!")

# Обработчик текстовых сообщений
async def echo(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Просто скинь мені zip архів в якому знаходяться PDF. Без папок, просто PDF в одниій папці, яка містить всі PDF")

# async def parse_zip(update, context):
#     await context.bot.send_message(chat_id=update.effective_chat.id, text="Просто скинь мені zip архів в якому знаходяться PDF. Без папок, просто PDF в одниій папці, яка містить всі PDF")

def main() -> None:
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    # application.add_handler(MessageHandler(filters.Document.ZIP, parse_zip))
    application.run_polling()

if __name__ == '__main__':
    main()
