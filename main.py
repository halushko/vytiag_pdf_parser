import csv
import datetime
import os
import random
import re
import shutil
import zipfile

import PyPDF2
from telegram.ext import Application, CommandHandler, MessageHandler, filters

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


def sstr(array):
    res = ''
    for a in array:
        res = res + re.sub(r'\n', ' && ', a) + '\n'
    return '\'' + res.strip()


def parse(pdf_folder, csv_path):
    with open(csv_path, 'w', newline='', encoding='Windows-1251') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['№', 'Файл', 'Площа', 'Будинок', 'Квартира', 'Частка', 'Власник', 'ІПН власника', 'Заборона у файлі'])
        nom = 0

        for filename in os.listdir(pdf_folder):
            if filename.endswith('pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                print("pdf_path=" + pdf_path)
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
                            # env_value = os.getenv('BUILD_ADDRESSES')
                            env_value = "вулиця Каблукова Академіка;вулиця Скакуна Віталія;проспект Гузара Любомира;проспект Комарова Космонавта"
                            if env_value:
                                values = env_value.split(';')
                                avr = av
                                print("До = " + avr)
                                for value in values:
                                    print(value)
                                    avr = re.sub('м.Київ, ' + value + ', будинок', '', avr).strip()
                                    print(avr)
                                print("Після = " + avr)
                                address_val_res.append(avr)
                            else:
                                print("Змінна не знайдена")
                        print("Знайдено")
                        chast_val.extend(find_between(rng, chast, price_mn, info_zagolovok, 'ВІДОМОСТІ', owner, stor, vidomosti))
                        for ov in find_between(rng, owner, 'ВІДОМОСТІ', ipn, ',', stor, vidomosti):
                            ovr = re.sub(r'[\n]', ' ', ov)
                            ovr = re.sub('ТОВАРИСТВО З ОБМЕЖЕНОЮ ВІДПОВІДАЛЬНІСТЮ', 'ТОВ', ovr)
                            ovr = re.sub('\" КОМПАНІЯ З УПРАВЛІННЯ АКТИВАМИ', '', ovr)
                            owner_val_res.append(ovr)
                        ipn_val.extend(find_between(rng, ipn, 'ВІДОМОСТІ', vidomosti, ','))
                        nom = nom + 1
                        print(address_val_res)
                        address_full = sstr(address_val_res)
                        print(address_full)
                        kv = '\'' + address_full[address_full.rfind(' '):].strip()
                        bud = address_full[0:address_full.rfind(',')].strip()
                        writer.writerow([nom, filename,
                                         sstr(square_val),
                                         bud,
                                         kv,
                                         sstr(chast_val),
                                         sstr(owner_val_res),
                                         sstr(ipn_val),
                                         sstr(zaborona_val)])
    return csv_path

def rename_files_with_random_hex(directory):
    print(directory)
    for root, dirs, files in os.walk(directory):
        for dir in dirs:
            if dir == '__MACOSX':
                shutil.rmtree(os.path.join(root, dir))
        for file in files:
            file_path = os.path.join(root, file)
            if os.path.isfile(file_path):
                name, extension = os.path.splitext(file)
                new_name = ''.join(random.choice('0123456789ABCDEF') + random.choice('0123456789ABCDEF') for _ in range(len(name)))
                new_filename = new_name + extension

                new_file_path = os.path.join(directory, new_filename)
                print(file_path)
                print(new_file_path)
                os.rename(file_path, new_file_path)

async def unzip_and_proceed(update, context):
    message = update.message
    file_id = message.document.file_id
    today = datetime.datetime.today()
    date_str = today.strftime('%Y_%m_%d_') + str(today.hour) + "_" + str(today.minute) + "_" + str(today.second)
    file_name = message.document.file_name
    file = await context.bot.get_file(file_id)
    downloaded_file = await file.download_as_bytearray()
    directory = f'/app/files/{date_str}'

    # os.rmdir(directory)
    os.makedirs(directory, exist_ok=False)
    print('message.document.mime_type=' + message.document.mime_type)
    if message.document and message.document.mime_type == 'application/zip':
        print('Start unzip')
        zip_file_path = os.path.join(directory, file_name)
        with open(zip_file_path, 'wb') as file:
            file.write(downloaded_file)

        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(directory)
        await message.reply_text('Архів розпаковано, іде обробка вмісту')

    rename_files_with_random_hex(directory)

    for root, dirs, files in os.walk(directory):
        for file in files:
            source_file = os.path.join(root, file)
            destination_file = os.path.join(directory, file)
            while os.path.exists(destination_file):
                filename, extension = os.path.splitext(file)
                destination_file = os.path.join(directory, filename + str(random.randint(1, 999)) + extension)
            destination_file = os.path.join(directory, filename + str(random.randint(1, 999)) + extension)
            shutil.copy2(source_file, destination_file)

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if not file.endswith('.pdf') :
                os.remove(file_path)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            shutil.rmtree(dir_path)

    result_file = parse(directory, date_str + '.csv')
    await context.bot.send_document(chat_id=update.effective_chat.id, document=result_file)

async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привіт, я вмію парсити PDF! Просто скинь мені zip-архів в якому знаходяться PDF-файли або сам PDF")

async def echo(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Просто скинь мені zip архів в якому знаходяться PDF")

async def parse_zip(update, context):
    await unzip_and_proceed(update, context)

def main() -> None:
    bot_token = os.getenv('BOT_TOKEN')
    application = Application.builder().token(bot_token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(MessageHandler(filters.Document.ZIP, parse_zip))
    application.run_polling()

if __name__ == '__main__':
    main()
