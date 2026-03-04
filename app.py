from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__)

def get_coin_data(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
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

        # 2. Список полей, которые вам нужны
        fields = [
            "Драгоценный металл", "Общий вес", "Проба металла", 
            "Чистого драгметалла", "Страна-эмитент монеты", "Номинал монеты", 
            "Валюта номинала", "Тираж монеты", "Год выпуска", 
            "Диаметр", "Качество чеканки монеты", "Упаковка", "Наличие сертификата"
        ]

        # Словарь для поиска (сокращенные ключи для надежности)
        search_map = {
            "Драгоценный металл": ["металл"],
            "Общий вес": ["общий вес", "масса", "вес"],
            "Проба металла": ["проба"],
            "Чистого драгметалла": ["чистого", "чист. драг"],
            "Страна-эмитент монеты": ["страна", "эмитент"],
            "Номинал монеты": ["номинал"],
            "Валюта номинала": ["валюта"],
            "Тираж монеты": ["тираж"],
            "Год выпуска": ["год"],
            "Диаметр": ["диаметр"],
            "Качество чеканки монеты": ["качество"],
            "Упаковка": ["упаковка"],
            "Наличие сертификата": ["сертификат"]
        }

        # БРУТФОРС: Ищем все текстовые элементы на странице
        all_pairs = {}
        for tag in soup.find_all(['div', 'tr', 'li', 'span', 'p']):
            text = tag.get_text(" ", strip=True)
            if ":" in text and len(text) < 150:
                parts = text.split(":", 1)
                k = parts[0].strip().lower()
                v = parts[1].strip()
                if k and v:
                    all_pairs[k] = v

        # Дополнительно ищем классические таблицы
        for row in soup.find_all(['div', 'tr'], class_=re.compile(r'item|row|char')):
            label = row.find(class_=re.compile(r'label|name|title'))
            value = row.find(class_=re.compile(r'value|val'))
            if label and value:
                all_pairs[label.get_text(strip=True).lower().rstrip(':')] = value.get_text(strip=True)

        values_list = []
        for field in fields:
            found = "-"
            aliases = search_map.get(field, [])
            
            # Проверяем все найденные пары на совпадение с ключом или синонимом
            for key, val in all_pairs.items():
                if any(alias in key for alias in aliases) or field.lower() in key:
                    found = val
                    break
            
            # ОЧИСТКА И ФОРМАТИРОВАНИЕ
            # Замена точек на запятые
            found = found.replace('.', ',')
            
            # Удаление "1 тройская унция (31.1 грамм)" -> "31,1 грамм"
            if "унция" in found.lower() and "(" in found:
                match = re.search(r'\((.*?)\)', found)
                if match:
                    found = match.group(1)
            else:
                found = found.replace("1 тройская унция", "").strip()

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
