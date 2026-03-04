from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
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

        # 2. Собираем характеристики (Метод "Поиск по тексту" v.11)
        # Мы просто сканируем все div-ы и ищем те, где есть текст и значение
        raw_map = {}
        for item in soup.find_all(['div', 'tr', 'li']):
            # Ищем внутри блоки с названиями и значениями
            lbl = item.find(class_=re.compile(r'label|name|char-name'))
            val = item.find(class_=re.compile(r'value|val|char-value'))
            
            if lbl and val:
                key = lbl.get_text(strip=True).rstrip(':').strip()
                value = val.get_text(strip=True).strip()
                if key and value:
                    raw_map[key] = value

        # Список нужных полей
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        # Словарик синонимов, чтобы находить данные, даже если они названы чуть иначе
        synonyms = {
            "Драгоценный металл": ["Металл"],
            "Общий вес": ["Вес", "Масса"],
            "Проба металла": ["Проба"],
            "Чистого драгметалла": ["Чистого металла", "Вес чистого"],
            "Страна-эмитент монеты": ["Страна", "Эмитент"],
            "Номинал монеты": ["Номинал"],
            "Валюта номинала": ["Валюта"],
            "Тираж монеты": ["Тираж"],
            "Год выпуска": ["Год"],
            "Качество чеканки монеты": ["Качество"],
            "Наличие сертификата": ["Сертификат"]
        }

        values_list = []
        for field in fields:
            found = "-"
            # Составляем список слов для поиска
            keys_to_check = [field.lower()] + [s.lower() for s in synonyms.get(field, [])]
            
            # Проверяем наш собранный словарь
            for k, v in raw_map.items():
                k_low = k.lower()
                if any(term == k_low or k_low.startswith(term) for term in keys_to_check):
                    found = v
                    break
            
            # ФОРМАТИРОВАНИЕ
            # 1. Замена точек на запятые
            found = found.replace('.', ',')
            
            # 2. Если это Общий вес, убираем "1 тройская унция (...)" и оставляем только вес в скобках
            if field == "Общий вес" or field == "Чистого драгметалла":
                # Ищем текст внутри скобок, например: (31,1 грамм)
                match_weight = re.search(r'\((.*?)\)', found)
                if match_weight:
                    found = match_weight.group(1)
                else:
                    found = found.replace('1 тройская унция', '').strip()

            values_list.append(found)

        return coin_name, "\n".join(fields), "\n".join(values_list)

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
