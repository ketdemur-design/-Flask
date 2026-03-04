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
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=20)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Извлекаем название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # 2. Собираем характеристики (Универсальный метод v.9)
        # Мы ищем все блоки, где лежат пары Название-Значение
        data_dict = {}
        
        # Перебираем все возможные блоки с характеристиками
        # Метод 1: По классам сайта
        for item in soup.select('.product-chars-item, .product-info-chars div, tr'):
            lbl = item.select_one('.product-chars-label, .char-name, td:first-child, dt')
            val = item.select_one('.product-chars-value, .char-value, td:last-child, dd')
            if lbl and val:
                key = lbl.get_text(strip=True).rstrip(':')
                data_dict[key] = val.get_text(strip=True)

        # Метод 2: Если первый метод нашел мало, ищем по любому тексту с двоеточием
        if len(data_dict) < 5:
            for element in soup.find_all(['div', 'li', 'p']):
                txt = element.get_text(" ", strip=True)
                if ':' in txt and len(txt) < 150:
                    parts = txt.split(':', 1)
                    data_dict[parts[0].strip()] = parts[1].strip()

        # Список полей, которые вам нужны (добавил Чистого драгметалла)
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        # Подготовка вывода
        char_names_out = "\n".join(fields)
        values_list = []
        
        for f in fields:
            res = "-"
            # Ищем совпадение в словаре
            for k, v in data_dict.items():
                if f.lower() in k.lower() or k.lower() in f.lower():
                    res = v
                    break
            
            # Форматирование: точки на запятые, удаление скобок
            res = res.replace('.', ',')
            if "1 тройская унция (" in res:
                res = res.replace("1 тройская унция (", "").replace(")", "")
            
            values_list.append(res)
        
        char_values_out = "\n".join(values_list)

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
