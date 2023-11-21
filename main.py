import requests
from bs4 import BeautifulSoup
import re
import json
from telegram import Bot, ParseMode
from PIL import Image, ImageOps
from io import BytesIO
import telegram.error 

TELEGRAM_BOT_TOKEN = '6989586871:AAGbWglkeiHJumgQGUivkhbBZVt9TkNjkAM'
CHAT_IDS = ["@testikbotika"]
BACKGROUND_IMAGE_URL = 'https://cdn.discordapp.com/attachments/1172163344610902097/1175741509111402626/IMG_20231119_111630_081.jpg?ex=656c559b&is=6559e09b&hm=f1b53c704188a485a63aef5047c751971cbe21e445190e0c1c38d5d172157ea7&' 
print("Бот успешно запущен!")

def get_game_info(item_id):
    url = f"https://www.rolimons.com/item/{item_id}"
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        item_roblox_page_link_div = soup.find('div', class_='d-flex mx-3')
        if item_roblox_page_link_div:
            roblox_page_link = item_roblox_page_link_div.find('a')['href']
        else:
            roblox_page_link = "Недоступно"
        sale_locations_grid_div = soup.find('div', class_='sale_locations_grid mx-2')
        if sale_locations_grid_div:
            game_links = sale_locations_grid_div.find_all('a', class_='btn btn-flat-play')
            game_names = sale_locations_grid_div.find_all('div', class_='my-auto')
            game_links_and_names = [
                (link['href'], name.text.strip())
                for link, name in zip(game_links, game_names)
            ]
            item_image_url = soup.find('img', class_='top_profile_main_image')['src']
        else:
            game_links_and_names = [("Недоступно", "Недоступно")]
            item_image_url = None
        return roblox_page_link, game_links_and_names, item_image_url
    return None, None, None

def save_processed_item_ids(item_id):
    with open("endlimited.txt", "a") as file:
        file.write(f"{item_id}\n")

def load_processed_item_ids():
    try:
        with open("endlimited.txt", "r") as file:
            return set(map(str.strip, file.readlines()))
    except FileNotFoundError:
        return set()

def add_image_background(item_image_url, background_image_url, main_image_size=(400, 400), final_image_size=(1280, 720), horizontal_alignment=-400):
    response_original = requests.get(item_image_url)
    response_original.raise_for_status()
    original_image = Image.open(BytesIO(response_original.content)).convert("RGBA")
    response_background = requests.get(background_image_url)
    response_background.raise_for_status()
    background_image = Image.open(BytesIO(response_background.content)).convert("RGBA")
    original_image = original_image.resize(main_image_size, Image.LANCZOS)
    result_image = Image.new("RGBA", background_image.size, (255, 255, 255, 0))
    image_position = (
        (background_image.width - original_image.width) // 2 + horizontal_alignment,
        (background_image.height - original_image.height) // 2
    )
    alpha = original_image.split()[3]
    result_image.paste(original_image, image_position, alpha)
    result_image = Image.alpha_composite(background_image.convert("RGBA"), result_image)
    result_image = result_image.resize(final_image_size, Image.LANCZOS)
    result_image_bytesio = BytesIO()
    result_image.save(result_image_bytesio, format="PNG")
    result_image_bytesio.seek(0)
    return result_image_bytesio

def process_and_send_photo(item_id, item_data):
    item_name = item_data[0]
    item_quantity = item_data[2]
    roblox_page_link, game_links_and_names, item_image_url = get_game_info(item_id)
    if item_image_url:
        result_image_bytesio = add_image_background(item_image_url, BACKGROUND_IMAGE_URL)
        if len(result_image_bytesio.getvalue()) > 0:
            message_text = f"<b>Название: {item_name}</b>\n"
            message_text += f"<b>Тип: FREE UGC LIMITED U</b>\n"
            message_text += "<b>Дата и время: Сейчас/Скоро</b>\n"
            message_text += f"<b>Копии: {item_quantity}</b>\n"
            message_text += f"<b>Ссылка: <a href='{roblox_page_link}' style='text-decoration: none; color: inherit;'>{item_name}</a></b>\n"
            for index, (game_link, game_name) in enumerate(game_links_and_names, start=1):
                if game_name != "Недоступно":
                    message_text += f"<b>Ссылка на игру: {index} - <a href='{game_link}' style='text-decoration: none; color: inherit;'>{game_name}</a></b>\n"
                else:
                    message_text += f"<b>Ссылка на игру: {index} - Недоступно</b>\n"
            message_text += "<b>Как получать: Неизвестно</b>\n"
            message_text += "\n"
            try:
                for chat_id in CHAT_IDS:
                    bot.send_photo(chat_id=chat_id, photo=result_image_bytesio, caption=message_text,
                                   parse_mode=ParseMode.HTML, disable_notification=True)
            except telegram.error.BadRequest as e:
                print(f"Error sending photo to chat_id {chat_id}: {e}")
                print("Continuing to the next chat_id...")
                pass
        else:
            print("Error: result_image_bytesio is empty")
    else:
        for chat_id in CHAT_IDS:
            bot.send_message(chat_id=chat_id, text="Error: Image is missing", parse_mode=ParseMode.HTML,
                             disable_notification=True)
    save_processed_item_ids(item_id)

if __name__ == "__main__":
    url = "https://www.rolimons.com/free-roblox-limiteds"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', string=re.compile('var item_details ='))
    if script_tag:
        script_content = script_tag.string
        start_index = script_content.find('{')
        end_index = script_content.rfind('}')
        if start_index != -1 and end_index != -1:
            data = script_content[start_index:end_index + 1]
            item_details = json.loads(data)
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            processed_item_ids = load_processed_item_ids()
            for item_id, item_data in item_details.items():
                if item_id in processed_item_ids:
                    continue
                process_and_send_photo(item_id, item_data)
