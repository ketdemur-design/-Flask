from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://zoloto-md.ru/'
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=20)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # 2. Собираем ВСЕ текстовые пары со страницы (Метод "Грубая сила")
        all_text_data = {}
        
        # Вариант А: Ищем стандартные блоки сайта
        items = soup.find_all(class_=re.compile("product-chars-item|char-item|product-info-chars"))
        for item in items:
            lbl = item.find(class_=re.compile("label|name|title"))
            val = item.find(class_=re.compile("value|val"))
            if lbl and val:
                key = lbl.get_text(strip=True).rstrip(':')
                all_text_data[key] = val.get_text(strip=True)

        # Вариант Б: Если Вариант А дал мало данных, ищем все элементы, где есть двоеточие
        if len(all_text_data) < 5:
            for element in soup.find_all(['div', 'li', 'tr', 'p']):
                text = element.get_text(strip=True)
                if ':' in text and len(text) < 200:
                    parts = text.split(':', 1)
                    if len(parts) == 2:
                        all_text_data[parts[0].strip()] = parts[1].strip()

        # Вариант В: Ищем по тегам span (часто характеристики там)
        for span in soup.find_all('span'):
            parent = span.parent
            if parent and ':' in parent.get_text():
                txt = parent.get_text(strip=True)
                parts = txt.split(':', 1)
                all_text_data[parts[0].strip()] = parts[1].strip()

        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        char_names_out = "\n".join(fields)
        values_list = []
        
        for f in fields:
            found_val = "-"
            # Ищем совпадение по смыслу
            for k, v in all_text_data.items():
                if f.lower() in k.lower() or k.lower() in f.lower():
                    found_val = v
                    break
            
            # Чистим данные
            found_val = found_val.replace('.', ',')
            if "1 тройская унция (" in found_val:
                found_val = found_val.replace("1 тройская унция (", "").replace(")", "")
            
            values_list.append(found_val)
        
        char_values_out = "\n".join(values_list)

        # Отладочный хвост (поможет понять, что видит код)
        if all(v == "-" for v in values_list):
            char_values_out += "\n\n(Внимание: Данные не найдены. Скрипт увидел " + str(len(all_text_data)) + " пар данных на странице)"

        return coin_name, char_names_out, char_values_out

    except Exception as e:
        return f"Ошибка: {str(e)}", "-", "-"

@app.route('/', methods=['GET', 'POST'])
def index():
    res_name, res_names, res_vals = "", "", ""
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            res_name, res_names, res_vals = get_coin_data(url)
    return render_template('index.html', name=res_name, names=res_names, vals=res_vals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
