from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    # Добавляем расширенные заголовки, чтобы сайт думал, что мы человек
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # Название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # Характеристики
        data_dict = {}
        # Ищем все элементы с характеристиками
        items = soup.find_all('div', class_='product-chars-item')
        
        for item in items:
            lbl = item.find('div', class_='product-chars-label')
            val = item.find('div', class_='product-chars-value')
            if lbl and val:
                key = lbl.get_text(strip=True).replace(':', '')
                value = val.get_text(strip=True)
                data_dict[key] = value

        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        char_names_out = "\n".join(fields)
        
        values_list = []
        for f in fields:
            val = data_dict.get(f, "-")
            
            # Заменяем точки на запятые и убираем унции
            val = val.replace('.', ',')
            if "1 тройская унция (" in val:
                val = val.replace("1 тройская унция (", "").replace(")", "")
            
            values_list.append(val)
        
        char_values_out = "\n".join(values_list)
        return coin_name, char_names_out, char_values_out

    except Exception as e:
        return f"Ошибка: {str(e)}", "", ""

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
