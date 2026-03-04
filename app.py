from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    # Максимально "человеческие" заголовки
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
    }
    
    try:
        session = requests.Session()
        # Пробуем зайти сначала на главную, чтобы получить Cookies (как человек)
        session.get("https://zoloto-md.ru/", headers=headers, timeout=10)
        
        # Теперь заходим на страницу монеты
        response = session.get(url, headers=headers, timeout=20)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return f"Ошибка сайта: {response.status_code}. Попробуйте позже.", "-", "-"

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Название
        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else "Не найдено"
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        # 2. Сбор данных
        scraped = {}
        # Ищем все элементы характеристик
        items = soup.find_all('div', class_='product-chars-item')
        if not items:
            items = soup.select('.product-info-chars div, .char-item, tr')

        for item in items:
            lbl = item.find(['div', 'span', 'td'], class_=re.compile(r'label|name|title'))
            val = item.find(['div', 'span', 'td'], class_=re.compile(r'value|val|text'))
            if lbl and val:
                key = lbl.get_text(strip=True).rstrip(':')
                scraped[key] = val.get_text(strip=True)

        # 3. Эталонный список
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        aliases = {
            "Драгоценный металл": ["Металл"], "Общий вес": ["Масса", "Вес"],
            "Чистого драгметалла": ["Чистого металла"], "Страна-эмитент монеты": ["Страна", "Эмитент"],
            "Тираж монеты": ["Тираж"], "Качество чеканки монеты": ["Качество"]
        }

        values = []
        for f in fields:
            res = "-"
            search_keys = [f.lower()] + [a.lower() for a in aliases.get(f, [])]
            for k, v in scraped.items():
                if any(sk in k.lower() for sk in search_keys):
                    res = v
                    break
            
            # Форматирование
            res = res.replace('.', ',')
            if "унция" in res.lower():
                weight_match = re.search(r'\((.*?)\)', res)
                res = weight_match.group(1) if weight_match else res.replace("1 тройская унция", "").strip()
            values.append(res)

        return coin_name, "\n".join(fields), "\n".join(values)

    except Exception as e:
        return f"Ошибка: {str(e)}", "-", "-"

@app.route('/', methods=['GET', 'POST'])
def index():
    res_name, res_names, res_vals = "", "", ""
    if request.method == 'POST':
        url = request.form.get('url')
        if url: res_name, res_names, res_vals = get_coin_data(url)
    return render_template('index.html', name=res_name, names=res_names, vals=res_vals)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
