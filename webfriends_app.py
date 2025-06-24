from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from webfriends.models import db, User, Event, Like, Message, Gift, UserGift

app = Flask(__name__, template_folder='webfriends/templates', static_folder='webfriends/static')
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///webfriends.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

CARDS = [
    {"id": 1, "image": "https://source.unsplash.com/random/400x300?sig=1", "question": "Выбери мем, который тебе ближе"},
    {"id": 2, "image": "https://source.unsplash.com/random/400x300?sig=2", "question": "Какую музыку ты слушаешь?"},
    {"id": 3, "image": "https://source.unsplash.com/random/400x300?sig=3", "question": "Любимое место в городе?"},
]

@app.route('/')
def index():
    return render_template('index.html', title='ВебДрузья')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя занято')
        else:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('profile_view'))
    return render_template('register.html', title='Регистрация')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверные учетные данные')
    return render_template('login.html', title='Вход')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/map')
def map_view():
    return render_template('map.html', title='Карта')

@app.route('/events', methods=['GET'])
def events_api():
    events = Event.query.all()
    return jsonify([
        {"id": e.id, "lat": e.lat, "lng": e.lng, "title": e.title, "description": e.description}
        for e in events
    ])

@app.route('/add_event', methods=['POST'])
def add_event():
    event = Event(
        title=request.form['title'],
        description=request.form['description'],
        lat=float(request.form['lat']),
        lng=float(request.form['lng']),
        creator_id=current_user.id if current_user.is_authenticated else None,
    )
    db.session.add(event)
    db.session.commit()
    return redirect('/map')

@app.route('/cards')
def cards_view():
    return render_template('cards.html', title='Челленджи', cards=CARDS)


@app.route('/swipe')
@login_required
def swipe_view():
    user = User.query.filter(User.id != current_user.id).order_by(db.func.random()).first()
    return render_template('swipe.html', title='Поиск друзей', target=user)


@app.route('/like/<int:user_id>/<action>')
@login_required
def like_user(user_id, action):
    target = db.session.get(User, user_id)
    if not target:
        flash('Пользователь не найден')
        return redirect(url_for('swipe_view'))
    like = Like.query.filter_by(user_id=current_user.id, target_id=user_id).first()
    if not like:
        like = Like(user_id=current_user.id, target_id=user_id, liked=(action=='like'))
        db.session.add(like)
    else:
        like.liked = (action=='like')
    db.session.commit()
    # check for match
    if action == 'like':
        back = Like.query.filter_by(user_id=user_id, target_id=current_user.id, liked=True).first()
        if back:
            flash('У вас новый матч!')
    return redirect(url_for('swipe_view'))


@app.route('/send_gift/<int:user_id>', methods=['GET', 'POST'])
@login_required
def send_gift(user_id):
    target = db.session.get(User, user_id)
    if not target:
        flash('Пользователь не найден')
        return redirect(url_for('index'))
    gifts = Gift.query.all()
    if request.method == 'POST':
        gift_id = int(request.form['gift_id'])
        g = db.session.get(Gift, gift_id)
        if g:
            ug = UserGift(sender_id=current_user.id, recipient_id=user_id, gift_id=gift_id)
            db.session.add(ug)
            db.session.commit()
            flash('Подарок отправлен')
            return redirect(url_for('profile_view'))
    return render_template('send_gift.html', title='Подарок', target=target, gifts=gifts)

@app.route('/feed')
def feed_view():
    events = Event.query.order_by(Event.id.desc()).all()
    return render_template('feed.html', title='Пульс города', feed=events)

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat_view(user_id):
    other = db.session.get(User, user_id)
    if not other:
        flash('Пользователь не найден')
        return redirect(url_for('index'))
    if request.method == 'POST':
        text = request.form['text']
        msg = Message(sender_id=current_user.id, recipient_id=other.id, text=text)
        db.session.add(msg)
        db.session.commit()
        return redirect(url_for('chat_view', user_id=user_id))
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).all()
    return render_template('chat.html', title='Чат', other=other, messages=messages)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_view():
    if request.method == 'POST':
        current_user.city = request.form.get('city', '')
        current_user.status = request.form.get('status', '')
        current_user.interests = request.form.get('interests', '')
        db.session.commit()
        flash('Профиль обновлен')
    return render_template('profile.html', title='Профиль', user=current_user)


@app.route('/create-event', methods=['GET', 'POST'])
@login_required
def create_event_view():
    if request.method == 'POST':
        return add_event()
    return render_template('create_event.html', title='Создать событие')


@app.cli.command('initdb')
def init_db_command():
    with app.app_context():
        db.create_all()
        if not Gift.query.first():
            db.session.add_all([
                Gift(name='Цветок', description='Виртуальный цветок'),
                Gift(name='Сердце', description='Смайлик-сердечко'),
            ])
            db.session.commit()
        print('Database initialized')

if __name__ == '__main__':
    app.run(debug=True)
