from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Извлекаем название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # 2. Собираем характеристики в словарь
        data_dict = {}
        
        # Находим контейнер характеристик
        chars_container = soup.find('div', class_='product-chars')
        if not chars_container:
            chars_container = soup.find('div', class_='product-info-chars')

        if chars_container:
            # Ищем каждую строку характеристики
            rows = chars_container.find_all('div', class_='product-chars-item')
            for row in rows:
                label_div = row.find('div', class_='product-chars-label')
                value_div = row.find('div', class_='product-chars-value')
                
                if label_div and value_div:
                    # Извлекаем текст, очищая его от вложенных тегов (типа <span>)
                    key = label_div.get_text(strip=True).rstrip(':')
                    val = value_div.get_text(strip=True)
                    data_dict[key] = val

        # Список полей, которые вам нужны
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        # Подготавливаем вывод названий (левый блок)
        char_names_out = "\n".join(fields)
        
        # Подготавливаем вывод значений (правый блок)
        values_list = []
        for f in fields:
            # Ищем точное совпадение или похожее
            found_val = "-"
            for k, v in data_dict.items():
                if f.lower() in k.lower() or k.lower() in f.lower():
                    found_val = v
                    break
            
            # Чистим результат: точки на запятые, убираем унции
            found_val = found_val.replace('.', ',')
            if "1 тройская унция (" in found_val:
                found_val = found_val.replace("1 тройская унция (", "").replace(")", "")
            
            values_list.append(found_val)
        
        char_values_out = "\n".join(values_list)

        return coin_name, char_names_out, char_values_out

    except Exception as e:
        return f"Ошибка при запросе: {str(e)}", "-", "-"

@app.route('/', methods=['GET', 'POST'])
def index():
    res_name, res_names, res_vals = "", "", ""
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            res_name, res_names, res_vals = get_coin_data(url)
    
    return render_template('index.html', name=res_name, names=res_names, vals=res_vals)

if __name__ == '__main__':
    app.run(host='0.0.0.0'
