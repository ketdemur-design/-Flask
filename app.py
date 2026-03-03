from flask import Flask, render_template, request
import json
import re

import requests
from bs4 import BeautifulSoup

app = Flask(__name__)


def _clean_text(text):
    if text is None:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned.rstrip(':').strip()


def _normalize_key(key):
    normalized = _clean_text(key).lower().replace('ё', 'е')
    normalized = re.sub(r'[^a-zа-я0-9]+', ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def _is_placeholder(value):
    return _normalize_key(value) in {'', '-', '—', 'нет', 'n a', 'na'}


def _extract_characteristics(soup):
    pairs = {}

    def add_pair(key, value):
        clean_key = _clean_text(key)
        clean_value = _clean_text(value)
        if not clean_key or not clean_value:
            return
        if len(clean_key) > 120 or len(clean_value) > 200:
            return
        pairs[clean_key] = clean_value

    def walk_json(data):
        if isinstance(data, dict):
            name = data.get('name')
            value = data.get('value')
            if isinstance(name, str) and isinstance(value, (str, int, float)):
                add_pair(name, str(value))
            for item in data.values():
                walk_json(item)
        elif isinstance(data, list):
            for item in data:
                walk_json(item)

    for script in soup.find_all('script', attrs={'type': 'application/ld+json'}):
        raw = script.string or script.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        walk_json(data)

    for tr in soup.select('tr'):
        cells = tr.find_all(['th', 'td'])
        if len(cells) >= 2:
            add_pair(cells[0].get_text(' ', strip=True), cells[1].get_text(' ', strip=True))

    for dl in soup.find_all('dl'):
        dts = dl.find_all('dt')
        dds = dl.find_all('dd')
        for dt, dd in zip(dts, dds):
            add_pair(dt.get_text(' ', strip=True), dd.get_text(' ', strip=True))

    for container in soup.select('[class*="char"], [class*="spec"], [class*="prop"], [class*="feature"]'):
        label = container.select_one('[class*="label"], [class*="name"], [class*="title"]')
        value = container.select_one('[class*="value"], [class*="val"], [class*="text"]')
        if label and value:
            add_pair(label.get_text(' ', strip=True), value.get_text(' ', strip=True))

    for item in soup.select('[class*="item"], [class*="row"]'):
        label = item.select_one('[class*="name"], [class*="label"], [class*="title"], dt')
        value = item.select_one('[class*="value"], [class*="val"], [class*="text"], dd')
        if label and value:
            add_pair(label.get_text(' ', strip=True), value.get_text(' ', strip=True))

    for element in soup.find_all(['li', 'p', 'div', 'span']):
        text = _clean_text(element.get_text(' ', strip=True))
        if ':' in text and len(text) < 180:
            left, right = text.split(':', 1)
            add_pair(left, right)

    return pairs


def get_coin_data(url):
    if not url.startswith(('http://', 'https://')):
        return 'Ошибка: укажите ссылку с http:// или https://', '-', '-'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://zoloto-md.ru/'
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        response.encoding = 'utf-8'

        lowered_body = response.text.lower()
        if 'запрошенный url не может быть получен' in lowered_body:
            return 'Ошибка: сайт недоступен через текущий сетевой прокси.', '-', '-'

        soup = BeautifulSoup(response.text, 'html.parser')

        h1 = soup.find('h1')
        title_text = h1.get_text(strip=True) if h1 else 'Не найдено'
        name_match = re.search(r'[«"“](.*?)[»"”]', title_text)
        coin_name = name_match.group(1) if name_match else title_text

        all_text_data = _extract_characteristics(soup)

        fields = [
            'Драгоценный металл', 'Проба металла', 'Общий вес',
            'Страна-эмитент монеты', 'Номинал монеты', 'Валюта номинала',
            'Тираж монеты', 'Год выпуска', 'Диаметр',
            'Качество чеканки монеты', 'Упаковка'
        ]

        aliases = {
            'Драгоценный металл': ['металл', 'драгметалл'],
            'Проба металла': ['проба'],
            'Общий вес': ['общий вес', 'масса', 'вес', 'вес монеты'],
            'Страна-эмитент монеты': ['страна', 'эмитент', 'страна эмитент'],
            'Номинал монеты': ['номинал', 'номинал монеты'],
            'Валюта номинала': ['валюта'],
            'Тираж монеты': ['тираж'],
            'Год выпуска': ['год выпуска', 'год', 'дата выпуска'],
            'Диаметр': ['диаметр'],
            'Качество чеканки монеты': ['качество', 'чеканки', 'пруф', 'unc'],
            'Упаковка': ['упаковка', 'капсула', 'футляр']
        }

        norm_pairs = {_normalize_key(k): v for k, v in all_text_data.items()}

        values_list = []
        for field in fields:
            found_val = '-'
            norm_field = _normalize_key(field)
            terms = [norm_field] + [_normalize_key(a) for a in aliases.get(field, [])]

            if norm_field in norm_pairs:
                found_val = norm_pairs[norm_field]
            else:
                candidates = []
                for key, value in norm_pairs.items():
                    if any(term in key or key in term for term in terms):
                        if not _is_placeholder(value):
                            candidates.append((len(key), value))
                if candidates:
                    found_val = min(candidates, key=lambda item: item[0])[1]

            values_list.append(found_val.replace('.', ','))

        char_names_out = '\n'.join(fields)
        char_values_out = '\n'.join(values_list)

        return coin_name, char_names_out, char_values_out

    except requests.RequestException as exc:
        return f'Ошибка сети: {str(exc)}', '-', '-'
    except Exception as exc:
        return f'Ошибка: {str(exc)}', '-', '-'


@app.route('/', methods=['GET', 'POST'])
def index():
    res_name, res_names, res_vals = '', '', ''
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            res_name, res_names, res_vals = get_coin_data(url)
    return render_template('index.html', name=res_name, names=res_names, vals=res_vals)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
