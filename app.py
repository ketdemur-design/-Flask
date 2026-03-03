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
        
        if response.status_code != 200:
            return f"Ошибка доступа: {response.status_code}", "-", "-"

        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Извлекаем название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # 2. УНИВЕРСАЛЬНЫЙ СБОР ХАРАКТЕРИСТИК (v.5)
        # Собираем ВООБЩЕ ВСЕ пары "текст - значение" со страницы
        raw_data = {}
        
        # Ищем во всех возможных блоках: div, li, tr
        for element in soup.find_all(['div', 'tr', 'li']):
            # Ищем внутри элементы, похожие на ярлык и значение
            label = element.find(['div', 'span', 'td', 'dt'], class_=re.compile('label|name|title|char-name'))
            value = element.find(['div', 'span', 'td', 'dd'], class_=re.compile('value|val|char-value'))
            
            if label and value:
                l_text = label.get_text(strip=True).rstrip(':')
                v_text = value.get_text(strip=True)
                if l_text and v_text:
                    raw_data[l_text] = v_text

        # Если так не нашли, ищем по всей странице любой текст, содержащий ":"
        if not raw_data:
            for item in soup.find_all(text=re.compile('.:.')):
                if ':' in item:
                    parts = item.split(':', 1)
                    raw_data[parts[0].strip()] = parts[1].strip()

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
            # Ищем максимально похожее название в собранных данных
            for k, v in raw_data.items():
                if f.lower() in k.lower() or k.lower() in f.lower():
                    found_val = v
                    break
            
            # Форматирование
            found_val = found_val.replace('.', ',')
            if "1 тройская унция (" in found_val:
                found_val = found_val.replace("1 тройская унция (", "").replace(")", "")
            
            values_list.append(found_val)
        
        char_values_out = "\n".join(values_list)

        return coin_name, char_names_out, char_values_out

    except Exception as e:
        return f"Системная ошибка: {str(e)}", "-", "-"

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
