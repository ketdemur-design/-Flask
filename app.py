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
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Извлекаем название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # 2. СБОР ДАННЫХ (Ультра-гибкий метод v.10)
        data_dict = {}

        # Ищем все элементы, которые могут содержать характеристики (div, tr, li)
        # Мы просто берем все текстовые блоки и ищем в них двоеточия
        for item in soup.find_all(['div', 'tr', 'li']):
            # Если внутри есть два четких блока (метка и значение)
            label_node = item.find(class_=re.compile(r'label|name|title|char_name'))
            value_node = item.find(class_=re.compile(r'value|val|char_value'))
            
            if label_node and value_node:
                k = label_node.get_text(strip=True).rstrip(':')
                v = value_node.get_text(strip=True)
                if k and v:
                    data_dict[k] = v
            
            # Дополнительно проверяем текстовые строки с двоеточием внутри элемента
            direct_text = item.get_text(" ", strip=True)
            if ':' in direct_text and len(direct_text) < 200:
                parts = direct_text.split(':', 1)
                k_raw = parts[0].strip()
                v_raw = parts[1].strip()
                if k_raw and v_raw and k_raw not in data_dict:
                    data_dict[k_raw] = v_raw

        # Список полей, которые вам нужны
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        # Синонимы для поиска (если на сайте поле называется иначе)
        aliases = {
            "Драгоценный металл": ["Металл"],
            "Общий вес": ["Масса", "Вес"],
            "Проба металла": ["Проба"],
            "Чистого драгметалла": ["Чистого металла"],
            "Страна-эмитент монеты": ["Страна"],
            "Тираж монеты": ["Тираж"],
            "Качество чеканки монеты": ["Качество"],
            "Наличие сертификата": ["Сертификат"]
        }

        char_names_out = "\n".join(fields)
        values_list = []
        
        for f in fields:
            val = "-"
            # Составляем список имен для поиска: основное + синонимы
            search_terms = [f.lower()] + [a.lower() for a in aliases.get(f, [])]
            
            # Проверяем наш словарь собранных данных
            for k, v in data_dict.items():
                k_low = k.lower()
                if any(term == k_low or k_low.startswith(term) for term in search_terms):
                    val = v
                    break
            
            # Очистка и форматирование
            val = val.replace('.', ',')
            if "1 тройская унция (" in val:
                val = val.replace("1 тройская унция (", "").replace(")", "")
            
            values_list.append(val)
        
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
