import os
import secrets
import random
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, join_room, emit
from webfriends.models import db, User, Event, Like, Message, Gift, UserGift, Match, Status

app = Flask(__name__, template_folder='webfriends/templates', static_folder='webfriends/static')
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///webfriends.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
socketio = SocketIO(app)
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

def get_chat_room(id1: int, id2: int) -> str:
    a, b = sorted([id1, id2])
    return f"chat_{a}_{b}"

# simple in-memory queue for SpeedMeet
speed_waiting = None  # (user_id, sid)

@app.route('/')
def index():
    return render_template('index.html', title='ВебДрузья')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email')
        phone = request.form.get('phone')
        gender = request.form.get('gender')
        age = request.form.get('age')
        about = request.form.get('about')
        social = request.form.get('social')
        photo_file = request.files.get('photo')
        if User.query.filter_by(username=username).first():
            flash('Имя пользователя занято')
        else:
            user = User(
                username=username,
                email=email,
                phone=phone,
                gender=gender,
                age=int(age) if age else None,
                about=about,
                social=social,
                email_token=secrets.token_urlsafe(8) if email else None,
                phone_token=secrets.token_urlsafe(8) if phone else None,
            )
            user.set_password(password)
            if photo_file and photo_file.filename:
                filename = secure_filename(photo_file.filename)
                upload_path = os.path.join(app.static_folder, 'uploads', filename)
                photo_file.save(upload_path)
                user.photo = filename
            db.session.add(user)
            db.session.commit()
            login_user(user)
            if email:
                flash(f'Подтвердите email: {url_for("confirm_email", token=user.email_token, _external=True)}')
            if phone:
                flash(f'Подтвердите телефон: {url_for("confirm_phone", token=user.phone_token, _external=True)}')
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
    events = [
        {"id": e.id, "lat": e.lat, "lng": e.lng, "title": e.title, "description": e.description, "type": "event", "category": e.category, "safe": e.is_safe}
        for e in Event.query.all()
    ]
    users = [
        {
            "id": u.id,
            "lat": u.lat,
            "lng": u.lng,
            "title": u.username,
            "description": u.status,
            "type": "user",
            "gender": u.gender,
            "interests": u.interests,
        }
        for u in User.query.filter_by(is_private=False).all() if u.lat and u.lng
    ]
    return jsonify(events + users)

@app.route('/add_event', methods=['POST'])
def add_event():
    event = Event(
        title=request.form['title'],
        description=request.form['description'],
        category=request.form.get('category'),
        is_safe=bool(request.form.get('is_safe')),
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
        like = Like(user_id=current_user.id, target_id=user_id, liked=(action=='like'), super=(action=='super'))
        db.session.add(like)
    else:
        like.liked = (action!='dislike')
        like.super = (action=='super')
    db.session.commit()
    # check for match
    if action in ['like', 'super']:
        back = Like.query.filter_by(user_id=user_id, target_id=current_user.id).filter(Like.liked==True).first()
        if back:
            if not Match.query.filter(
                ((Match.user1_id==current_user.id) & (Match.user2_id==user_id)) |
                ((Match.user1_id==user_id) & (Match.user2_id==current_user.id))
            ).first():
                db.session.add(Match(user1_id=current_user.id, user2_id=user_id))
                db.session.commit()
            q = random.choice(CARDS)['question']
            flash('У вас новый матч! Вопрос для начала разговора: ' + q)
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
            msg = 'Подарок отправлен'
            if g.coupon_url:
                msg += f". Купон: {g.coupon_url}"
            flash(msg)
            return redirect(url_for('profile_view'))
    return render_template('send_gift.html', title='Подарок', target=target, gifts=gifts)

@app.route('/feed')
def feed_view():
    events = Event.query.order_by(Event.id.desc()).all()
    statuses = Status.query.order_by(Status.timestamp.desc()).limit(20).all()
    feed = events + statuses
    feed.sort(key=lambda x: getattr(x, 'timestamp', x.id), reverse=True)
    return render_template('feed.html', title='Пульс города', feed=feed)


@app.route('/status', methods=['GET', 'POST'])
@login_required
def status_view():
    if request.method == 'POST':
        text = request.form['text']
        s = Status(user_id=current_user.id, text=text)
        db.session.add(s)
        db.session.commit()
        return redirect(url_for('feed_view'))
    return render_template('status.html', title='Статус')

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat_view(user_id):
    other = db.session.get(User, user_id)
    if not other:
        flash('Пользователь не найден')
        return redirect(url_for('index'))
    # allow chat only for взаимных лайков
    l1 = Like.query.filter_by(user_id=current_user.id, target_id=other.id).filter(Like.liked==True).first()
    l2 = Like.query.filter_by(user_id=other.id, target_id=current_user.id).filter(Like.liked==True).first()
    if not (l1 and l2):
        flash('Чат доступен только после взаимного лайка')
        return redirect(url_for('swipe_view'))
    if request.method == 'POST':
        text = request.form['text']
        msg = Message(sender_id=current_user.id, recipient_id=other.id, text=text)
        db.session.add(msg)
        db.session.commit()
        room = get_chat_room(current_user.id, other.id)
        socketio.emit('new_message', {
            'sender': current_user.username,
            'text': text
        }, room=room)
        return redirect(url_for('chat_view', user_id=user_id))
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other.id)) |
        ((Message.sender_id == other.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp).all()
    return render_template('chat.html', title='Чат', other=other, messages=messages)


@app.route('/matches')
@login_required
def matches_view():
    matches = Match.query.filter(
        (Match.user1_id == current_user.id) | (Match.user2_id == current_user.id)
    ).all()
    ids = [m.user1_id if m.user2_id == current_user.id else m.user2_id for m in matches]
    users = User.query.filter(User.id.in_(ids)).all() if ids else []
    return render_template('matches.html', title='Матчи', users=users)


@app.route('/confirm_email/<token>')
def confirm_email(token):
    user = User.query.filter_by(email_token=token).first_or_404()
    user.email_confirmed = True
    user.email_token = None
    db.session.commit()
    flash('Email подтвержден')
    return redirect(url_for('profile_view'))


@app.route('/confirm_phone/<token>')
def confirm_phone(token):
    user = User.query.filter_by(phone_token=token).first_or_404()
    user.phone_confirmed = True
    user.phone_token = None
    db.session.commit()
    flash('Телефон подтвержден')
    return redirect(url_for('profile_view'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        if not current_user.check_password(request.form['old_password']):
            flash('Неверный текущий пароль')
        else:
            current_user.set_password(request.form['new_password'])
            db.session.commit()
            flash('Пароль обновлен')
            return redirect(url_for('profile_view'))
    return render_template('change_password.html', title='Сменить пароль')


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile_view():
    if request.method == 'POST':
        current_user.city = request.form.get('city', '')
        current_user.status = request.form.get('status', '')
        current_user.interests = request.form.get('interests', '')
        current_user.about = request.form.get('about', '')
        current_user.social = request.form.get('social', '')
        current_user.is_private = bool(request.form.get('is_private'))
        current_user.trusted_user_id = request.form.get('trusted_user_id') or None
        current_user.lat = request.form.get('lat') or None
        current_user.lng = request.form.get('lng') or None
        photo_file = request.files.get('photo')
        if photo_file and photo_file.filename:
            filename = secure_filename(photo_file.filename)
            upload_path = os.path.join(app.static_folder, 'uploads', filename)
            photo_file.save(upload_path)
            current_user.photo = filename
        db.session.commit()
        flash('Профиль обновлен')
    return render_template('profile.html', title='Профиль', user=current_user)


@app.route('/verify', methods=['GET', 'POST'])
@login_required
def verify_view():
    if request.method == 'POST':
        photo = request.files.get('photo')
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            upload_path = os.path.join(app.static_folder, 'uploads', filename)
            photo.save(upload_path)
            current_user.verification_photo = filename
            current_user.is_verified = True
            db.session.commit()
            flash('Верификация пройдена')
            return redirect(url_for('profile_view'))
    return render_template('verify.html', title='Верификация')


@app.route('/speedmeet')
@login_required
def speedmeet_view():
    return render_template('speedmeet.html', title='SpeedMeet')


@socketio.on('join')
def on_join(data):
    if not current_user.is_authenticated:
        return
    room = get_chat_room(current_user.id, data.get('other_id'))
    join_room(room)


@socketio.on('send_message')
def on_send_message(data):
    if not current_user.is_authenticated:
        return
    other_id = data.get('other_id')
    text = data.get('text')
    if not other_id or not text:
        return
    msg = Message(sender_id=current_user.id, recipient_id=other_id, text=text)
    db.session.add(msg)
    db.session.commit()
    room = get_chat_room(current_user.id, other_id)
    emit('new_message', {
        'sender': current_user.username,
        'text': text
    }, room=room)


@socketio.on('speed_join')
def speed_join():
    if not current_user.is_authenticated:
        return
    global speed_waiting
    if speed_waiting and speed_waiting[0] != current_user.id:
        partner_id, partner_sid = speed_waiting
        speed_waiting = None
        room = f"speed_{min(current_user.id, partner_id)}_{max(current_user.id, partner_id)}"
        join_room(room, sid=request.sid)
        join_room(room, sid=partner_sid)
        socketio.emit('speed_start', {'initiator': False}, room=partner_sid)
        emit('speed_start', {'initiator': True})
    else:
        speed_waiting = (current_user.id, request.sid)


@socketio.on('speed_signal')
def speed_signal(data):
    emit('speed_signal', data, broadcast=True, include_self=False)


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
                Gift(name='Сердце', description='Смайлик-сердечко', coupon_url='https://example.com/coupon')
            ])
            db.session.commit()
        print('Database initialized')

if __name__ == '__main__':
    socketio.run(app, debug=True)
