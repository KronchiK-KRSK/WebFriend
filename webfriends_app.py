from flask import Flask, render_template, jsonify

app = Flask(__name__, template_folder='webfriends/templates', static_folder='webfriends/static')

# Демонстрационные данные
EVENTS = [
    {"id": 1, "lat": 55.751244, "lng": 37.618423, "title": "Кофе в парке", "description": "Ищу компанию для настолок"},
    {"id": 2, "lat": 55.757, "lng": 37.615, "title": "Гуляем с собакой", "description": "Присоединяйся!"},
    {"id": 3, "lat": 55.75, "lng": 37.605, "title": "Бег по набережной", "description": "Легкая пробежка"}
]

CARDS = [
    {"id": 1, "image": "https://source.unsplash.com/random/400x300?sig=1", "question": "Выбери мем, который тебе ближе"},
    {"id": 2, "image": "https://source.unsplash.com/random/400x300?sig=2", "question": "Какую музыку ты слушаешь?"},
    {"id": 3, "image": "https://source.unsplash.com/random/400x300?sig=3", "question": "Любимое место в городе?"}
]

@app.route('/')
def index():
    return render_template('index.html', title='ВебДрузья')

@app.route('/map')
def map_view():
    return render_template('map.html', title='Карта')

@app.route('/events')
def events_api():
    return jsonify(EVENTS)

@app.route('/cards')
def cards_view():
    return render_template('cards.html', title='Челленджи', cards=CARDS)

@app.route('/feed')
def feed_view():
    return render_template('feed.html', title='Пульс города', feed=EVENTS)

@app.route('/chat')
def chat_view():
    return render_template('chat.html', title='SpeedMeet')

if __name__ == '__main__':
    app.run(debug=True)
