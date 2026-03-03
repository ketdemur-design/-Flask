from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Название из кавычек
        h1 = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', h1)
        coin_name = name_match.group(1) if name_match else h1

        # 2. Характеристики
        data_dict = {}
        char_items = soup.find_all('div', class_='product-chars-item')
        for item in char_items:
            lbl = item.find('div', class_='product-chars-label')
            val = item.find('div', class_='product-chars-value')
            if lbl and val:
                data_dict[lbl.get_text(strip=True)] = val.get_text(strip=True)

        # Список нужных полей
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        char_names_out = "\n".join(fields)
        
        # Форматируем значения (точки на запятые, убираем унции)
        values_list = []
        for f in fields:
            val = data_dict.get(f, "-")
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
