import eventlet
eventlet.monkey_patch()  # Очистка путей

import os
import math
import uuid
import locale
import logging
import threading

from dotenv import load_dotenv
load_dotenv()  # Загрузка виртуальных переменных

from urllib.parse import unquote
from sqlalchemy import asc, desc, or_, and_
from datetime import datetime as dt
from logging.handlers import SMTPHandler

from flask import Flask
from flask import send_from_directory, render_template, redirect, request, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from flask_moment import Moment
from flask_socketio import SocketIO

from data import db_session
from data.models.user import User, Notification
from data.models.post import Post, PostRate, Tag
from data.models.friendship import FriendshipOffer, Friend
from data.models.dialogs import Dialog, Message

from app.config import Config
from app.mail import send_email
from app.forms import RegistrationForm, LoginForm, EditUserForm, AddEditPostForm, DisplayPostForm, \
    SendMessageForm, ConfirmEmailForm, EditPasswordForm, FindUserForm

locale.setlocale(locale.LC_ALL, ('ru_RU', 'UTF-8'))

# Инициализация приложения
app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

# Подключение app для авторизации
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
#

# Подключение WebSocket сервера
socket = SocketIO(app, cors_allowed_origins='http://127.0.0.1:5000')
thread = None
thread_lock = threading.Lock()
#

# Подключение mail и moment app
mail = Mail(app)
moment = Moment(app)
#
#

# Настройка отправления сообщений об ошибках на сервере на почту
# Если сервер в режиме production и определен mail server
if not app.debug and app.config['MAIL_SERVER']:
    auth = None
    if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
        auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])

    secure = None
    if app.config['MAIL_USE_TLS']:
        secure = ()

    mail_handler = SMTPHandler(
        mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
        fromaddr='no-reply@' + app.config['MAIL_SERVER'],
        toaddrs=app.config['ADMINS'],
        subject='SocialNetwork Failure',
        credentials=auth,
        secure=secure
    )

    mail_handler.setLevel(logging.ERROR)
    app.logger.addHandler(mail_handler)
#

# Глобальные переменные
host = '127.0.0.1'
port = 5000
clients = []
filter_by = {'tags': []}
sort_by = {'field': 'create_date', 'type': 'desc'}
#


@app.errorhandler(404)
def not_found_error(e):
    """ Обработка ошибки 404 """
    return render_template('404.html', title='Ошибка'), 404


@app.errorhandler(500)
def internal_error(e):
    """ Обработка ошибки 500 """
    return render_template('500.html', title='Ошибка'), 500


@socket.on('connect')
def connect():
    """ Функция подключения клиента к WebSocket """

    print('connect')
    clients.append(request.sid)

    if current_user.is_authenticated:  # Изменение sid текущего пользователя
        session = db_session.create_session()
        user = session.query(User).get(current_user.id)
        user.set_sid(request.sid)
        session.commit()


@socket.on('disconnect')
def disconnect():
    """ Функция для отключения клиента от WebSocket """

    print('Client disconnected', clients)
    clients.remove(request.sid)


def send(event: str, message: str, receivers: list):
    """ Функция отправляет сообщение от сервера клиентам """

    print(event, message)
    print(receivers, clients)
    for client in receivers:  # Для каждого клиента из получателей
        if client not in clients:  # Вывод предупреждающего сообщения, если клиент неизвестен
            print_warning(f'Unknown client: "{client}". All connected clients: {clients}')
        socket.emit(event, message, room=client)  # Отправление сообщения клиенту


def print_warning(text):
    """ Функция форматирует вывод предупреждающего сообщения в консоль """
    print("\033[33m{}\033[0m".format(text))


def get_user(session, user_id, check_auth=True) -> User:
    """ Функция возвращает объект класса User по user_id. Порождает ValueError в случае ошибки """

    user = session.query(User).get(user_id)

    if not user:
        raise ValueError(f'There are no users with id: {user_id}')
    if check_auth and current_user != user:
        raise ValueError(f'User with id {user_id} doesnt match to current_user, but current_page'
                         f' need this math')
    return user


def get_user_status_info(questioner_user: User, target_user) -> dict:
    """ Функция возвращает информацию для карточки пользователя в виде json """

    response = {'buttons': None, 'status_text': None, 'status_style_color': None, 'type': None}

    if target_user in questioner_user.friends():  # Карточка друга
        response['buttons'] = [
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>''',
            f'''<a class="btn btn-danger" href="javascript:card_type('remove_friend', {questioner_user.id}, {target_user.id})">Удалить из друзей</a>'''
        ]
        response['status_text'] = ' - Друг'
        response['status_style_color'] = 'green'
        response['type'] = 'friend'
    elif target_user in questioner_user.subscribers():  # Карточка подписчика
        response['buttons'] = [
            f'''<a class="btn btn-success" href="javascript:card_type('add_friend', {questioner_user.id}, {target_user.id})">Принять заявку</a>'''
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>'''
        ]
        if questioner_user.need_answer(target_user):  # Добавление кнопки "Оставить в подписчиках"
            response['buttons'].append(f'''<a id="user_{target_user.id}_sub_btn" class="btn btn-secondary" href="javascript:answer_offer({questioner_user.id}, {target_user.id})">Оставить в подписчиках</a>''')
        response['status_text'] = ' - Подписчик'
        response['status_style_color'] = 'red'
        response['type'] = 'subscriber'
    elif target_user in questioner_user.offers():  # Карточка запроса в друзья
        response['buttons'] = [
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>'''
            f'''<a class="btn btn-danger" href="javascript:card_type('remove_req', {questioner_user.id}, {target_user.id})">Отменить заявку</a>'''
        ]
        response['status_text'] = ' - Заявка в друзья'
        response['status_style_color'] = 'darkgray'
        response['type'] = 'offer'
    else:  # Карточка обычного пользователя
        response['buttons'] = [
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>'''
            f'''<a class="btn btn-success" href="javascript:card_type('add_req', {questioner_user.id}, {target_user.id})">Добавить в друзья</a>'''
        ]
        response['status_text'] = ''
        response['status_style_color'] = 'black'
        response['type'] = 'usual'

    return response


def get_user_pagination_info(objects, referrer):
    """ Функция возвращает данные для пагинации объектов """

    obj_type = 'USERS' if objects and isinstance(objects[0], User) else 'POSTS'
    pp = app.config[f'{obj_type}_PER_PAGE']  # Объектов на страницу
    page = request.args.get('page', 1, type=int) - 1  # Текущая страница
    pages_amount = math.ceil(len(objects) / pp)  # Количество страниц
    referrer = referrer  # предыдущая страница
    objects = objects[page * pp:(page + 1) * pp]  # Объекты для пагинации

    return {'pp': pp, 'cur_page': page, 'pages_amount': pages_amount,
            'referrer': referrer, obj_type.lower(): objects}  # json-представление пагинации


def get_post(session, post_id) -> Post:
    """ Функция возвращает объект Post по его id. Порождает ValueError в случае ошибки """

    post = session.query(Post).get(post_id)
    if not post:
        raise ValueError(f'There are no posts with id : {post_id}')

    return post


def get_suitable_posts(session) -> list:
    """ Метод возвращает список постов, подходящих под условия отбора """

    def suit_tag(p) -> bool:
        """ Внутрення функция проверки поста на соответствие указанным тегам """
        pt = [str(tag.id) for tag in p.tags]
        if set(pt).intersection(filter_tags):
            return True
        return not len(filter_tags)

    filter_tags = filter_by['tags']
    sort_func = {'asc': asc, 'desc': desc}

    # Сортировка и фильтрация постов
    posts = session.query(Post).order_by(sort_func[sort_by['type']](getattr(Post, sort_by['field'])))
    posts = list(filter(suit_tag, posts.all()))
    #

    return posts


def main():
    """ Основная функция сервера """
    db_session.global_init('db/website.db')  # Инициализация сессии обращения к базе данных
    socket.run(app, host=host, port=port)  # Запуск WebSocket сервера вместе с app


@login_manager.user_loader
def load_user(user_id):
    """ Обработчик загрузки пользователя (при логине или обращении к current_user """
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/favicon.ico')
def favicon():
    """ Обработчик иконки социальной сети """
    return send_from_directory(os.path.join(app.root_path, 'static/img'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.context_processor
def app_context():
    """ Обработчик для создания контекста в шаблонах """
    context = {'date': dt.utcnow, 'user_info': get_user_status_info, 'isinstance': isinstance,
               'Post': Post}
    return context


@app.before_request
def before_request():
    """ Обработчик для действий до запроса """

    # Обновление времени последнего посещения пользователя
    if current_user.is_authenticated:
        session = db_session.create_session()
        user = session.query(User).get(current_user.id)

        user.last_seen = dt.utcnow()
        session.commit()
        print(current_user.sid, clients)
    #


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    """ Обработчик страницы новостей """

    # Если пользователь не авторизован, то перевести на страницу авторизации
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    session = db_session.create_session()

    # получение тегов, постов, и оценок посты
    tags = session.query(Tag).all()
    posts = get_suitable_posts(session)

    rates = {post_rate.post.id: post_rate.value for post_rate in current_user.rates}
    #

    form = DisplayPostForm()  # Инициализация формы

    if request.method == 'POST':  # Обработка POST запроса
        if request.form.get('apply_btn'):  # Фильтровать и сортировать посты по указанным значениям
            filter_by['tags'] = form.tags.data
            sort_by['field'] = form.sort_by.data
            sort_by['type'] = form.sort_type.data
        elif request.form.get('default_btn'):  # Стандартный вариант постов (показать все посты)
            filter_by['tags'] = []
            sort_by['field'] = 'create_date'
            sort_by['type'] = 'desc'
        else:
            raise ValueError(f'Server got POST from form without any known buttons. POST data: '
                             f'{request.form}')
        return redirect(url_for('index'))

    # Загрузка данных, по которым фильтруются посты
    form.tags.choices = [(tag.id, tag.name) for tag in tags]
    form.tags.data = filter_by['tags']
    form.sort_by.data = sort_by['field']
    form.sort_type.data = sort_by['type']
    #

    return render_template('posts.html', title='Новости', form=form, rates=rates, referrer='index',
                           pagination=get_user_pagination_info(posts, 'index'), id=0)


@app.route('/registration', methods=["GET", "POST"])
def registration():
    """ Обработчик для регистрации пользователя """

    form = RegistrationForm()
    if form.validate_on_submit():
        session = db_session.create_session()

        # Проверка на существование пользователя с указанной почтой
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('registration.html', title='Регистрация', form=form,
                                   message='Пользователь с такой почтой уже существует')
        #

        # Создание нового пользователя
        user = User(
            nickname=form.nickname.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)
        #

        # Отправка сообщения на указанную почту для подтверждения почты
        link = f'http://{host}:{port}/verifying_email/{user.nickname}/{user.email}' \
               f'/{user.password}/{user.get_token()}'
        send_email(
            app=app, mail=mail,
            subject='Change email',
            sender=app.config['ADMINS'][0],
            recipients=[form.email.data],
            html_body=render_template('email_template.html', username=user.nickname, link=link)
        )
        #

        return redirect(url_for('check_email'))

    return render_template('registration.html', title='Регистрация', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """ Обработчик для авторизации пользователя """

    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()

        # Проверка на корректность введенных значений
        if not user or not user.check_password(form.password.data):
            return render_template('login.html', title='Авторизация', form=form,
                                   message='Неправильный логин или пароль')
        #

        # Авторизация пользователя и перевод на его страницу #
        login_user(user)
        return redirect(url_for('home_page', user_id=current_user.id))

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    """ Обработчик для выхода пользователя """
    logout_user()
    return redirect(url_for('login'))


@app.route('/home_page/<int:user_id>')
@login_required
def home_page(user_id):
    """ Обработчик для домашней страницы пользователя """

    session = db_session.create_session()

    # Получение пользователя, его постов и оценок этих постов
    us = get_user(session, user_id, check_auth=False)
    posts = session.query(Post).filter(Post.user == us).order_by(desc(Post.create_date)).all()
    rates = {post_rate.post.id: post_rate.value for post_rate in current_user.rates}
    #

    return render_template('home.html', title='Моя страница', user=us, rates=rates, referrer='home',
                           pagination=get_user_pagination_info(posts, 'home_page'), id=user_id)


@app.route('/edit_user/<int:user_id>', methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    """ Обработчик для изменения информации о пользователе """

    session = db_session.create_session()
    user = get_user(session, user_id)

    form = EditUserForm()
    if request.method == "GET":  # Загрузка информации в поля ввода
        form.avatar.data         = f'static/img/users_img/{user.img}.jpg'
        form.nickname.data       = user.nickname
        form.status.data         = user.status
        form.sex.data            = user.sex
        form.education.data      = user.education
        form.marital_status.data = user.marital_status
        form.birthday.data       = user.birthday.date() if user.birthday != dt(1800, 1, 1) else None
        form.about_me.data       = user.about_me

    if form.validate_on_submit():  # Обновление информации у пользователя
        user.nickname       = form.nickname.data
        user.status         = form.status.data or 'Не указано'
        user.sex            = form.sex.data
        user.education      = form.education.data or 'Не указано'
        user.marital_status = form.marital_status.data
        user.about_me       = form.about_me.data or 'Не указано'
        try:  # Установление даты рождения у пользователя
            user.birthday   = dt.strptime(form.birthday.data, '%Y-%m-%d')
        except ValueError:
            user.birthday   = dt(1800, 1, 1)  # Заглушка, для сокрытия даты рождения пользователя

        if form.remove_birthday.data:  # События для сокрытия даты
            user.birthday   = dt(1800, 1, 1)

        if form.avatar.data:  # Если выбран аватар пользователя
            if user.img != 'default':
                try:  # Если изображение не стандартное, то пытаемся удалить старое
                    os.remove(f'static/img/users_img/{user.img}.jpg')
                except FileNotFoundError:
                    print_warning(f'File not found: static/img/users_img/{user.img}.jpg')

            # Создание нового аватара
            filename = str(uuid.uuid4())  # Генерация случайного имени файла
            request.files['avatar'].save(f'static/img/users_img/{filename}.jpg')
            user.img = filename
            #

        session.commit()

        return redirect(url_for('home_page', user_id=current_user.id))

    return render_template("edit_user.html", title='Редактирование', form=form)


@app.route('/change_email/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_email(user_id):
    """ Обработчик для отправки сообщения для подтверждения смены почты """

    session = db_session.create_session()
    user = get_user(session, user_id)
    emails = {user.email for user in session.query(User).all()}

    form = ConfirmEmailForm(emails, user.email)

    if request.method == 'GET':  # Текущая почта
        form.email.data = user.email
    if form.validate_on_submit():  # Отправление письма на новую почту
        link = f'http://{host}:{port}/finish_changing/{user_id}/{form.email.data}/{user.get_token()}'
        send_email(
            app=app, mail=mail,
            subject='Change email',
            sender=app.config['ADMINS'][0],
            recipients=[form.email.data],
            html_body=render_template('email_template.html', username=user.nickname, link=link)
        )
        return redirect(url_for('check_email'))

    return render_template('confirm_email_form.html', title='Изменение почты', form=form)


@app.route('/verifying_email/<nickname>/<email>/<password>/<token>')
def finish_registration(nickname, email, password, token):
    """ Обработчик для завершения регистрации """

    session = db_session.create_session()
    user = User(
        nickname=nickname,
        email=email,
        password=password
    )

    if user.verify_token(token):  # Если токен действительный, то добавление пользователя в бд
        session.add(user)
        session.commit()

        login_user(user)
        return redirect(url_for('home_page', user_id=user.id))

    # Вывод сообщения при недействительном токене
    h3 = 'Недействительный токен! Попробуйте зарегистрироваться заново.'
    return render_template('message_page.html', title='Ошибка', h1='Ошибка!', h3=h3)


@app.route('/finish_changing/<string:user_id>/<string:email>/<string:token>')
@login_required
def finish_changing(user_id, email, token):
    """ Обработчик для завершения изменения почты """

    session = db_session.create_session()
    user = get_user(session, int(user_id))

    if user.verify_token(token):  # Изменение почты при действительном токене
        user.email = email
        session.commit()

        h3 = f'Вы успешно сменили почту. Ваша новая почта: {email}'
        return render_template('message_page.html', title='Успешно', h1='Успех!', h3=h3)

    # Вывод сообщения при недействительном токене
    h3 = 'Недействительный токен! Попробуйте изменить почту заново'
    return render_template('message_page.html', title='Ошибка', h1='Ошибка!', h3=h3)


@app.route('/recover_password', methods=['GET', 'POST'])
def recover_password():
    """ Обработчик для отправления письма на почту для смены пароля """

    session = db_session.create_session()
    emails = {user.email for user in session.query(User).all()}

    form = ConfirmEmailForm(emails, is_email_edit=False)
    if form.validate_on_submit():  # Отправка письма для подтверждения почты
        user = session.query(User).filter(User.email == form.email.data).first()
        link = f'http://{host}:{port}/new_password/{user.id}/{user.get_token()}'
        send_email(
            app=app, mail=mail,
            subject='Recover password',
            sender=app.config['ADMINS'][0],
            recipients=[form.email.data],
            html_body=render_template('email_template.html', username=user.nickname, link=link)
        )
        return redirect(url_for('check_email'))

    return render_template('confirm_email_form.html', title='Восстановление пароля', form=form,
                           rec_pas=True)


@app.route('/new_password/<int:user_id>/<token>', methods=['GET', 'POST'])
def new_password(user_id, token):
    """ Обработчик для проверки доступа к изменению пароля """
    session = db_session.create_session()
    user = get_user(session, int(user_id), False)

    if user.verify_token(token):  # Перевод на форму с изменением пароля при действительном токене
        return redirect(url_for('change_password', user_id=user_id))

    # Вывод сообщения при недействительном токене
    h3 = 'Недействительный токен! Попробуйте изменить почту заново'
    return render_template('message_page.html', title='Ошибка', h1='Ошибка!', h3=h3)


@app.route('/change_password/<int:user_id>', methods=['GET', 'POST'])
def change_password(user_id):
    """ Обработчик для завершения изменения пароля """

    session = db_session.create_session()
    user = get_user(session, int(user_id), False)

    form = EditPasswordForm()
    if form.validate_on_submit():  # Изменение пароля
        user.set_password(form.password.data)
        login_user(user)
        session.commit()

        h3 = f'Вы успешно сменили пароль'
        return render_template('message_page.html', title='Успешно', h1='Успех!', h3=h3)

    return render_template('edit_password_page.html', title='Новый пароль', form=form)


@app.route('/check_email')
def check_email():
    """ Обработчик для уведомления пользователе об отправленном на почту письме """
    h3 = 'На указанную вами почту отправлено письмо для подтверждения вашей почты'
    return render_template('message_page.html', title='Проверка', h1='Проверьте вашу почту', h3=h3)


@app.route('/delete_avatar/<int:user_id>')
@login_required
def delete_user_avatar(user_id):
    """ Обработчик для удаления аватара """

    session = db_session.create_session()
    user = get_user(session, user_id)

    if user.img != 'default':  # Если изображение не стандартное, то удалить файл с аватаркой
        os.remove(f'static/img/users_img/{user.img}.jpg')
        user.img = 'default'

    session.commit()

    return redirect(url_for('home_page', user_id=user.id))


@app.route('/edit_post_rate', methods=['POST'])
@login_required
def edit_post_rate():
    """ Обработчик для изменения состояния лайка/дизлайка у поста """

    # Получение данных
    value = int(request.form['value'])
    post_id = int(request.form['id'])

    session = db_session.create_session()
    post = get_post(session, post_id)

    response = {'is_like': 0, 'is_dislike': 0, 'likes': post.likes, 'dislikes': post.dislikes}
    post_rate = session.query(PostRate).filter(PostRate.post == post,
                                               PostRate.user == current_user).first()
    #

    if value == 2:  # Заглушка для начальной загрузки информации о лайках
        if post_rate:
            response['is_like'] = post_rate.value == 1
            response['is_dislike'] = post_rate.value == -1
        return jsonify(response)

    if not post_rate:  # Если данный пользователь не оценивал пост, то создаем новый объект PostRate
        post_rate = PostRate(
            post_id=post_id,
            user_id=current_user.id,
            value=value
        )
        session.add(post_rate)
        if value == 1:  # Добавляем лайк
            post.likes += 1
        elif value == -1:  # Добавляем дизлайк
            post.dislikes += 1
        else:
            raise ValueError(f"Incorrect value. Expected -1 or 1, got {value}")
    else:  # Если пользователь уже оценивал пост, то изменяем его оценку
        if value == 1:  # Если ставится и лайк и ..
            if post_rate.value == 1:  # .. стоял лайк - убираем лайк
                post_rate.value = 0
                post.likes -= 1
            elif post_rate.value in (0, -1):  # .. ничего не стояло или стоял дизлайк - ставим лайк
                if post_rate.value == -1:  # Убираем запись о дизлайке, если такая была
                    post.dislikes -= 1
                post_rate.value = 1
                post.likes += 1
            else:
                raise ValueError(f"Incorrect post_rate.value. Expected -1 or 0 or 1, got "
                                 f"{post_rate.value}")
        elif value == -1:  # Если ставится дизлайк и ..
            if post_rate.value == -1:  # .. стоял дизлайк - убираем дизлайк
                post_rate.value = 0
                post.dislikes -= 1
            elif post_rate.value in (0, 1):  # .. ничего не стояло или стоял лайк - ставим дизлайк
                if post_rate.value == 1:  # Убираем запись о лайке, если такая была
                    post.likes -= 1
                post_rate.value = -1
                post.dislikes += 1
            else:
                raise ValueError(f"Incorrect post_rate.value. Expected -1 or 0 or 1, got "
                                 f"{post_rate.value}")
        else:
            raise ValueError(f"Incorrect value. Expected -1 or 1, got {value}")

    response = {'is_like': post_rate.value == 1, 'is_dislike': post_rate.value == -1,
                'likes': post.likes, 'dislikes': post.dislikes}
    session.commit()

    return jsonify(response)


@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    """ Обработчик для добавления нового поста """
    form = AddEditPostForm()
    session = db_session.create_session()
    form.tags.choices = [(tag.name, tag.name) for tag in session.query(Tag).all()]

    if form.validate_on_submit():
        # Информация поста
        title = form.title.data
        content = form.content.data
        img = form.img.data
        #

        if not (title or content or img):  # Проверка, что пост не пустой
            return render_template('add_edit_post.html', title='Создать пост', form=form,
                                   message='Хотя бы одно поле должно быть заполнено')

        # Создание нового поста и тегов к нему
        post = Post(
            title=title,
            content=content,
            author=current_user.id
        )
        post.tags = [session.query(Tag).filter(Tag.name == tag).first() for tag in form.tags.data]
        session.add(post)
        session.commit()
        #

        if request.files.get('img'):  # Если добавлена картинка, то сохраняем ее
            image_path = str(uuid.uuid4())  # Генерация случайного имени файла
            post.img = image_path
            session.commit()

            request.files['img'].save(f'static/img/post_img/{post.id}_{image_path}.jpg')

        return redirect(url_for('home_page', user_id=current_user.id))

    return render_template('add_edit_post.html', title='Изменить пост', form=form, post=0)


@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """ Обработчик изменения поста """

    session = db_session.create_session()
    post = get_post(session, post_id)

    form = AddEditPostForm()
    form.tags.choices = [(tag.name, tag.name) for tag in session.query(Tag).all()]
    if request.method == 'GET':  # Загрузка информации о посте в формы ввода
        form.title.data   = post.title
        form.content.data = post.content
        form.img.data     = post.img
        form.tags.data    = [tag.name for tag in post.tags]

    if form.validate_on_submit():  # Сохранение измененной информации в post
        post.title   = form.title.data
        post.content = form.content.data
        post.tags    = [session.query(Tag).filter(Tag.name == tag).first() for tag in form.tags.data]

        if request.files.get('img'):  # Если изменяли картинку ..
            try:  # Удалить старую картинку, если возможно
                os.remove(f'static/img/post_img/{post.id}_{post.img}.jpg')
            except FileNotFoundError:
                print_warning(f'File not found: static/img/post_img/{post.id}_{post.img}.jpg')

            # .. то добавляем новую
            filename = str(uuid.uuid4())  # Генерация случайного имени файла
            request.files['img'].save(f'static/img/post_img/{post.id}_{filename}.jpg')
            post.img = filename
            #

        session.commit()

        return redirect(url_for('home_page', user_id=post.author, _anchor=post_id))

    return render_template('add_edit_post.html', title='Изменить пост', form=form, post=post)


@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    """ Обработчик удаления поста """

    session = db_session.create_session()
    post = get_post(session, post_id)

    # Удаление всей информации поста
    post.rates.clear()
    session.delete(post)
    session.commit()
    #

    return redirect(url_for('home_page', user_id=current_user.id, _anchor='news'))


@app.route('/friends/<int:user_id>', methods=['GET', 'POST'])
@login_required
def friends(user_id):
    """ Обработчик отображения всех друзей """

    session = db_session.create_session()

    user = get_user(session, user_id, check_auth=False)
    users = user.friends()
    title = 'Мои друзья' if user == current_user else f'Друзья {user.nickname}'

    form = FindUserForm()
    if form.validate_on_submit():  # Поиск среди всех друзей по nickname
        if not form.nickname.data:
            return redirect(url_for('friends', user_id=user_id))
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title=title, users=users, form=form,
                           method=request.method, c_user=user)


@app.route('/subscribers/<int:user_id>', methods=['GET', 'POST'])
@login_required
def subscribers(user_id):
    """ Обработчик отображения всех подписчиков """

    session = db_session.create_session()

    user = get_user(session, user_id, check_auth=False)
    users = user.subscribers()
    title = 'Мои подписчики' if user == current_user else f'Подписчики {user.nickname}'

    form = FindUserForm()
    if form.validate_on_submit():  # Поиск среди всех подписчиков по nickname
        if not form.nickname.data:
            return redirect(url_for('subscribers', user_id=user_id))
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title=title, users=users, form=form,
                           method=request.method, c_user=user)


@app.route('/offers/<int:user_id>', methods=['GET', 'POST'])
@login_required
def offers(user_id):
    """ Обработчик отображения всех заявок в друзья """

    session = db_session.create_session()

    user = get_user(session, user_id, check_auth=False)
    users = user.offers()

    form = FindUserForm()
    if form.validate_on_submit():  # Поиск среди всех заявок в друзья по nickname
        if not form.nickname.data:
            return redirect(url_for('offers', user_id=user_id))
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title='Мои заявки', users=users, form=form,
                           method=request.method, c_user=user)


@app.route('/add_friend_list/<int:user_id>', methods=['GET', 'POST'])
@login_required
def add_friend_page(user_id):
    """ Обработчик отображения всех пользователей социальной сети """

    session = db_session.create_session()
    user = get_user(session, user_id, check_auth=False)

    users = session.query(User).filter(User.id != user_id).all()

    form = FindUserForm()
    if form.validate_on_submit():  # Поиск среди всех пользователей по nickname
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title='Добавить друга', form=form,
                           method=request.method, c_user=user,
                           pagination=get_user_pagination_info(users, 'add_friend_page'), id=user_id)


@app.route('/friendship_requests', methods=['POST'])
@login_required
def friendship_requests():
    """ Обработчик входящих запросов дружбы """

    def get_offer_by_ids(from_: list, to_: list):
        """ Внутренняя функция для получения запроса дружбы по id пользователей """
        req = session.query(FriendshipOffer).filter(FriendshipOffer.id_from.in_(from_),
                                                    FriendshipOffer.id_to.in_(to_)).first()
        if not req:
            raise ValueError(f'There are no offers from user {id_from} to user {id_to}')
        if req.id_from == req.id_to:
            raise RuntimeError(f'Detected incorrect data in offers table. '
                               f'There is offer note with same ids. Note id: {req.id}')
        return req

    session = db_session.create_session()
    requests = ('add_req', 'remove_req', 'add_friend', 'remove_friend')

    # Получение информации о запросе
    request_type = request.form['request_type']
    id_from = request.form['id_from']
    id_to = request.form['id_to']
    #

    # Получение пользователей запроса
    user_from = get_user(session, id_from)
    user_to = get_user(session, id_to, check_auth=False)
    #

    if request_type not in requests:  # Проверка корректности запроса
        raise ValueError(f'Incorrect request_type. Expected one of {requests}, got {request_type}')

    try:  # Пытаемся обработать запрос
        if request_type == 'add_req':  # Если отправляем пользователю запрос дружбы
            of = session.query(FriendshipOffer).filter(FriendshipOffer.id_from.in_([id_to]),
                                                       FriendshipOffer.id_to.in_([id_from])).first()
            if of:  # Проверяем что такого запроса еще нет
                raise ValueError(f'There is offer from user {id_to} to user {id_from}')

            # Создаем новый запрос
            offer = FriendshipOffer(id_from=id_from, id_to=id_to)
            session.add(offer)
            session.commit()
            #

            # Отправляем информацию о новом запросе дружбы на клиент
            count = len(user_to.unanswered_subscribers())
            info = get_user_status_info(user_to, user_from)
            user_to.add_notification(session, 'new_friendship_request', f'{count}+{info}')
            send('update', 'add friendship request', [user_to.sid])
            #
        elif request_type == 'remove_req':  # Если удаляем запрос дружбы
            # Проверяем существование запроса и удаляем его (если запрос найден)
            offer = get_offer_by_ids([id_from], [id_to])
            update_uns = user_to.need_answer(user_from)
            session.delete(offer)
            session.commit()
            #

            # Если указанный пользователь ожидал ответ, то отправляем уведомление об изменении
            # пользователей, ожидающих ответ на запрос, на клиент
            if update_uns:
                k, user_id = len(user_to.unanswered_subscribers()), user_from.id
                info = get_user_status_info(user_to, user_from)
                user_to.add_notification(session, 'new_friendship_request', f'{k}+{info}+{user_id}')
                send('update', 'delete friendship request', [user_to.sid])
        elif request_type == 'add_friend':  # Если добавляем в друзья
            # Проверяем наличие запроса дружбы и удаляем его
            offer = get_offer_by_ids([id_from, id_to], [id_to, id_from])
            session.delete(offer)
            #

            # Проверка что такой пары друзей уже нет
            friend = session.query(Friend).filter(Friend.id1.in_([id_from, id_to]),
                                                  Friend.id2.in_([id_from, id_to])).first()
            if friend:
                raise ValueError(f'There are also exists friends with pair ids: ({id_from},{id_to})')

            # Создаем новую пару друзей
            friend = Friend(id1=id_from, id2=id_to)
            session.add(friend)
            #
        elif request_type == 'remove_friend':  # Если удаляем из друзей
            # Проверяем что есть такая дружба ..
            friend = session.query(Friend).filter(Friend.id1.in_([id_from, id_to]),
                                                  Friend.id2.in_([id_from, id_to])).first()
            if not friend:
                raise ValueError(f'There are no friends with pair ids ({id_from}, {id_to})')
            if friend.id1 == friend.id2:
                raise RuntimeError(f'Detected incorrect data in friends table. '
                                   f'There is friend note with same ids. Note id: {friend.id}')
            session.delete(friend)  # .. и удаляем ее

            # Создаем новый запрос дружбы**
            # ** Нет необходимости проверять существование такого запроса,
            #    тк существование дружбы исключало этот вариант
            offer = FriendshipOffer(id_to=id_from, id_from=id_to, is_answered=True)
            session.add(offer)
    except ValueError as e:  # Если при обработке запроса произошел ValueError - запрос устарел**
        # ** Запрос устарел из-за того, что на другой стороне пользователь изменил состояние дружбы,
        #    поэтому текущему пользователю отправлено уведомление об этом, а карточка изменилась
        #    на актуальную
        print_warning(e.__str__())
        text = '''При отправке запроса произошла ошибка.</br>Другой пользователь поменял состояние 
                  вашей дружбы.</br>Сейчас вы видите актуальное состояние дружбы.'''
        send('warning', text, [user_from.sid])

    session.commit()

    response = get_user_status_info(user_from, user_to)  # Получение информации для карточки
    return jsonify(response)


@app.route('/answer_offer', methods=['POST'])
@login_required
def answer_for_friendship_offer():
    """ Обработчик для ответа на запрос дружбы """

    session = db_session.create_session()

    user_from = get_user(session, request.form['user_from'], check_auth=False)
    user_to = get_user(session, request.form['user_to'])

    offer = session.query(FriendshipOffer).filter(FriendshipOffer.user_from == user_from,
                                                  FriendshipOffer.user_to == user_to).first()
    if not offer:  # Проверка существования предложения дружбы
        print_warning(f'There are no FriendshipOffer between {user_from.id} and {user_to.id}')
        text = '''При отправке запроса произошла ошибка.</br>Другой пользователь поменял состояние 
                  вашей дружбы.</br>Обновите страницу, для получения актуальной информации.'''
        send('error', text, [user_to.sid])  # Отправка ошибки на клиент
        return {'response': 'fail'}

    offer.is_answered = True
    session.commit()

    return {'response': 'success'}


@app.route('/dialogs/<int:user_id>')
@login_required
def user_dialogs(user_id):
    """ Обработчик для отображения всех диалогов пользователя """

    session = db_session.create_session()
    user = get_user(session, user_id, check_auth=False)

    # Информация о диалоге и его последнем сообщении
    data = {dialog: dialog.messages[-1] for dialog in user.dialogs if list(dialog.messages)}
    data = {dialog: data[dialog] for dialog in
            sorted(data, key=lambda d: data[d].send_date, reverse=True)}
    #

    return render_template('dialogs.html', title='Диалоги', data=data, sender=current_user)


@app.route('/dialog/<int:id_from>/<int:id_to>', methods=['GET', 'POST'])
@login_required
def users_dialog(id_from, id_to):
    """ Обработчик для отображения диалога между 2-мя пользователями """

    session = db_session.create_session()

    user_from = get_user(session, id_from)
    user_to = get_user(session, id_to, check_auth=False)

    dialog = session.query(Dialog).filter(or_(and_(Dialog.id1 == id_from, Dialog.id2 == id_to),
                                              and_(Dialog.id1 == id_to,
                                                   Dialog.id2 == id_from))).first()
    if not dialog:  # Проверка на существование диалога, и создание пустого если его нет
        dialog = Dialog(id1=id_from, id2=id_to)
        session.add(dialog)
        session.commit()

    msg_ids = []  # При открытии окна диалога все сообщения читаются
    for message in dialog.unread_messages(id_from):
        message.is_read = True
        msg_ids.append(str(message.id))
    data = f'{user_from.id} {user_to.id},{" ".join(msg_ids)}'

    session.commit()

    # Отправка всех уведомлений на клиент
    unm = len(user_from.unread_dialogs())
    user_from.add_notification(session, 'unread_messages', unm)
    user_to.add_notification(session, 'messages_read', data)
    send('update', 'messages read (user opened dialog)', [user_to.sid, user_from.sid])
    #

    form = SendMessageForm()  # Инициализация формы для отправки сообщений
    return render_template('dialog_page.html', title='Диалоги', messages=list(dialog.messages),
                           user_to=user_to, form=form, dialog=dialog, unm=unm)


@app.route('/append_message', methods=['POST'])
@login_required
def append_message():
    """ Обработчик для добавления сообщения """

    session = db_session.create_session()

    # Получение информации о сообщении
    dialog_id = request.form['dialog']
    id_from = request.form['id_from']
    id_to = request.form['id_to']
    content = unquote(request.form['form'].split('=')[1]).replace('+', ' ')
    #

    # Получение пользователей сообщения
    user_from = get_user(session, id_from)
    user_to = get_user(session, id_to, check_auth=False)
    #

    # Создание нового сообщения
    message = Message(
        dialog_id=dialog_id,
        id_from=id_from,
        id_to=id_to,
        content=content
    )
    session.add(message)
    session.commit()

    # Создание блоков сообщения для обоих пользователей
    own_msg = f'''<div id="time_{message.id}" style="color: gray; text-align: right"></div>
                  <div id="message_{message.id}" class="alert alert-primary user-from-message">
                  <span id="message_text_{message.id}" style="color: orangered">Не прочитано - 
                  </span>{message.content}</div>'''
    rec_msg = f'''<div id="time_{message.id}" style="color: gray"></div>
                  <div id="message_{message.id}" class="alert alert-secondary user-to-message">
                  {message.content}</div>'''
    #

    # Создание информации о диалоге и его последнем сообщении у пользователя
    data = {dialog: dialog.messages[-1] for dialog in user_to.dialogs if list(dialog.messages)}
    data = {dialog: data[dialog] for dialog in
            sorted(data, key=lambda d: data[d].send_date, reverse=True)}
    #

    # Отправка всех уведомлений на клиент
    user_to.add_notification(session, 'unread_messages', len(user_to.unread_dialogs()))
    user_to.add_notification(session, 'need_update_dialogs',
                             render_template('_dialogs_card.html', data=data, sender=user_to))
    user_to.add_notification(session, 'need_add_message',
                             f'{message.id}+++{message.send_date}+++{rec_msg}+++{id_from}')
    user_from.add_notification(session, 'need_add_message',
                               f'{message.id}+++{message.send_date}+++{own_msg}')
    send('update', 'new user message', [user_to.sid, user_from.sid])
    #

    return {'response': 'success'}


@app.route('/messages_read', methods=['POST'])
@login_required
def messages_read():
    """ Обработчик для чтения сообщений """

    session = db_session.create_session()

    # Получение пользователей сообщения
    user = get_user(session, request.form['user'], check_auth=False)
    c_user = get_user(session, current_user.id)
    #

    # Изменение состояния сообщения (становится прочитанным)
    message = session.query(Message).get(request.form['id'])
    message.is_read = True
    session.commit()
    #

    # Отправка всех уведомлений на клиент
    user.add_notification(session, 'messages_read', f',{message.id}')
    c_user.add_notification(session, 'unread_messages', len(c_user.unread_dialogs()))
    send('update', 'messages read (user in dialog page)', [user.sid])
    #

    return {'response': 'success'}


@app.route('/notifications')
@login_required
def notifications():
    """ Обработчик для получения всех уведомлений для пользователя """

    session = db_session.create_session()
    since = request.args.get('since', 0.0, type=float)

    # Получение всех подходящих уведомлений
    n = session.query(Notification).filter(Notification.timestamp > since, Notification.user ==
                                           current_user).order_by(Notification.timestamp)
    response = [{'name': ntf.name, 'data': ntf.get_data(), 'timestamp': ntf.timestamp}
                for ntf in n]

    # Удаление всех просмотренных уведомлений
    for ntf in n:
        session.delete(ntf)
    session.commit()
    #

    return jsonify(response)


if __name__ == '__main__':
    main()
