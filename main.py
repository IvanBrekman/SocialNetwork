import os
import math
import uuid
import locale
import logging

from dotenv import load_dotenv

load_dotenv()

from urllib.parse import unquote
from sqlalchemy import asc, desc, or_, and_
from datetime import datetime as dt
from logging.handlers import SMTPHandler

from flask import Flask
from flask import send_from_directory, render_template, redirect, request, url_for, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail
from flask_moment import Moment

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

app = Flask(__name__, template_folder='templates')
app.config.from_object(Config)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

mail = Mail(app)
moment = Moment(app)

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

host = '127.0.0.1'
port = 5000
filter_by = {'tags': []}
sort_by = {'field': 'create_date', 'type': 'desc'}


@app.errorhandler(404)
def not_found_error(e):
    return render_template('404.html', title='Ошибка'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html', title='Ошибка'), 500


def print_warning(text):
    print("\033[33m{}\033[0m".format(text))


def get_user(session, user_id, check_auth=True) -> User:
    user = session.query(User).get(user_id)

    if not user:
        raise ValueError(f'There are no users with id: {user_id}')
    if check_auth and current_user != user:
        raise ValueError(f'User with id {user_id} doesnt match to current_user, but current_page'
                         f' need this math')
    return user


def get_user_status_info(questioner_user: User, target_user) -> dict:
    response = {'buttons': None, 'status_text': None, 'status_style_color': None, 'type': None}

    if target_user in questioner_user.friends():
        response['buttons'] = [
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>''',
            f'''<a class="btn btn-danger" href="javascript:card_type('remove_friend', {questioner_user.id}, {target_user.id})">Удалить из друзей</a>'''
        ]
        response['status_text'] = ' - Друг'
        response['status_style_color'] = 'green'
        response['type'] = 'friend'
    elif target_user in questioner_user.subscribers():
        response['buttons'] = [
            f'''<a class="btn btn-success" href="javascript:card_type('add_friend', {questioner_user.id}, {target_user.id})">Принять заявку</a>'''
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>'''
        ]
        response['status_text'] = ' - Подписчик'
        response['status_style_color'] = 'red'
        response['type'] = 'subscriber'
    elif target_user in questioner_user.offers():
        response['buttons'] = [
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>'''
            f'''<a class="btn btn-danger" href="javascript:card_type('remove_req', {questioner_user.id}, {target_user.id})">Отменить заявку</a>'''
        ]
        response['status_text'] = ' - Заявка в друзья'
        response['status_style_color'] = 'darkgray'
        response['type'] = 'offer'
    else:
        response['buttons'] = [
            f'''<a class="btn btn-primary" href="{url_for('users_dialog', id_from=questioner_user.id, id_to=target_user.id)}">Написать</a>'''
            f'''<a class="btn btn-success" href="javascript:card_type('add_req', {questioner_user.id}, {target_user.id})">Добавить в друзья</a>'''
        ]
        response['status_text'] = ''
        response['status_style_color'] = 'black'
        response['type'] = 'usual'

    return response


def get_user_pagination_info(objects, referrer):
    obj_type = 'USERS' if objects and isinstance(objects[0], User) else 'POSTS'
    pp = app.config[f'{obj_type}_PER_PAGE']
    page = request.args.get('page', 1, type=int) - 1
    pages_amount = math.ceil(len(objects) / pp)
    referrer = referrer
    objects = objects[page * pp:(page + 1) * pp]

    return {'pp': pp, 'cur_page': page, 'pages_amount': pages_amount,
            'referrer': referrer, obj_type.lower(): objects}


def get_post(session, post_id) -> Post:
    post = session.query(Post).get(post_id)
    if not post:
        raise ValueError(f'There are no posts with id : {post_id}')

    return post


def get_suitable_posts(session) -> list:
    def suit_tag(p) -> bool:
        pt = [str(tag.id) for tag in p.tags]
        if set(pt).intersection(filter_tags):
            return True
        return not len(filter_tags)

    filter_tags = filter_by['tags']
    sort_func = {'asc': asc, 'desc': desc}

    posts = session.query(Post).order_by(sort_func[sort_by['type']](getattr(Post, sort_by['field'])))
    posts = list(filter(suit_tag, posts.all()))

    return posts


def main():
    db_session.global_init('db/website.db')
    app.run(host, port)


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(user_id)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/img'), 'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.context_processor
def app_context():
    context = {'date': dt.utcnow, 'user_info': get_user_status_info}
    return context


@app.before_request
def before_request():
    # Обновление времени последнего посещения пользователя
    if current_user.is_authenticated:
        session = db_session.create_session()
        user = session.query(User).get(current_user.id)

        user.last_seen = dt.utcnow()
        session.commit()
    #


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    session = db_session.create_session()

    tags = session.query(Tag).all()
    posts = get_suitable_posts(session)

    rates = {post_rate.post.id: post_rate.value for post_rate in current_user.rates}

    form = DisplayPostForm()

    if request.method == 'POST':
        if request.form.get('apply_btn'):
            filter_by['tags'] = form.tags.data
            sort_by['field'] = form.sort_by.data
            sort_by['type'] = form.sort_type.data
        elif request.form.get('default_btn'):
            filter_by['tags'] = []
            sort_by['field'] = 'create_date'
            sort_by['type'] = 'desc'
        else:
            raise ValueError(f'Server got POST from form without any known buttons. POST data: '
                             f'{request.form}')
        return redirect(url_for('index'))

    form.tags.choices = [(tag.id, tag.name) for tag in tags]
    form.tags.data = filter_by['tags']
    form.sort_by.data = sort_by['field']
    form.sort_type.data = sort_by['type']

    return render_template('posts.html', title='Новости', form=form, rates=rates,
                           pagination=get_user_pagination_info(posts, 'index'), id=0)


@app.route('/registration', methods=["GET", "POST"])
def registration():
    form = RegistrationForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        if session.query(User).filter(User.email == form.email.data).first():
            return render_template('registration.html', title='Регистрация', form=form,
                                   message='Пользователь с такой почтой уже существует')
        user = User(
            nickname=form.nickname.data,
            email=form.email.data,
        )
        user.set_password(form.password.data)

        link = f'http://{host}:{port}/verifying_email/{user.nickname}/{user.email}' \
               f'/{user.password}/{user.get_token()}'
        send_email(
            app=app, mail=mail,
            subject='Change email',
            sender=app.config['ADMINS'][0],
            recipients=[form.email.data],
            html_body=render_template('email_template.html', username=user.nickname, link=link)
        )
        return redirect(url_for('check_email'))

    return render_template('registration.html', title='Регистрация', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.email == form.email.data).first()
        if not user or not user.check_password(form.password.data):
            return render_template('login.html', title='Авторизация', form=form,
                                   message='Неправильный логин или пароль')
        login_user(user)
        return redirect(url_for('home_page', user_id=current_user.id))

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/home_page/<int:user_id>')
@login_required
def home_page(user_id):
    session = db_session.create_session()
    user = get_user(session, user_id, check_auth=False)
    posts = session.query(Post).filter(Post.user == user).order_by(desc(Post.create_date)).all()

    rates = {post_rate.post.id: post_rate.value for post_rate in current_user.rates}

    return render_template('home.html', title='Моя страница', user=user, rates=rates,
                           pagination=get_user_pagination_info(posts, 'home_page'), id=user_id)


@app.route('/edit_user/<int:user_id>', methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    session = db_session.create_session()
    user = get_user(session, user_id)

    form = EditUserForm()
    if request.method == "GET":
        form.avatar.data = f'static/img/users_img/{user.img}.jpg'
        form.nickname.data = user.nickname
        form.status.data = user.status
        form.sex.data = user.sex
        form.education.data = user.education
        form.marital_status.data = user.marital_status
        form.birthday.data = user.birthday.date() if user.birthday != dt(1800, 1, 1) else None
        form.about_me.data = user.about_me

    if form.validate_on_submit():
        user.nickname = form.nickname.data
        user.status = form.status.data or 'Не указано'
        user.sex = form.sex.data
        user.education = form.education.data or 'Не указано'
        user.marital_status = form.marital_status.data
        user.about_me = form.about_me.data or 'Не указано'
        try:
            user.birthday = dt.strptime(form.birthday.data, '%Y-%m-%d')
        except ValueError:
            user.birthday = dt(1800, 1, 1)

        if form.remove_birthday.data:
            user.birthday = dt(1800, 1, 1)

        if form.avatar.data:
            if user.img != 'default':
                try:
                    os.remove(f'static/img/users_img/{user.img}.jpg')
                except FileNotFoundError:
                    print_warning(f'File not found: static/img/users_img/{user.img}.jpg')
            filename = str(uuid.uuid4())
            request.files['avatar'].save(f'static/img/users_img/{filename}.jpg')
            user.img = filename

        session.commit()

        return redirect(url_for('home_page', user_id=current_user.id))

    return render_template("edit_user.html", title='Редактирование', form=form)


@app.route('/change_email/<int:user_id>', methods=['GET', 'POST'])
@login_required
def change_email(user_id):
    session = db_session.create_session()
    user = get_user(session, user_id)
    emails = {user.email for user in session.query(User).all()}

    form = ConfirmEmailForm(emails, user.email)

    if request.method == 'GET':
        form.email.data = user.email
    if form.validate_on_submit():
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
    session = db_session.create_session()
    user = User(
        nickname=nickname,
        email=email,
        password=password
    )

    if user.verify_token(token):
        session.add(user)
        session.commit()

        login_user(user)
        return redirect(url_for('home_page', user_id=user.id))

    h3 = 'Недействительный токен! Попробуйте зарегистрироваться заново.'
    return render_template('message_page.html', title='Ошибка', h1='Ошибка!', h3=h3)


@app.route('/finish_changing/<string:user_id>/<string:email>/<string:token>')
@login_required
def finish_changing(user_id, email, token):
    session = db_session.create_session()
    user = get_user(session, int(user_id))

    if user.verify_token(token):
        user.email = email
        session.commit()

        h3 = f'Вы успешно сменили почту. Ваша новая почта: {email}'
        return render_template('message_page.html', title='Успешно', h1='Успех!', h3=h3)

    h3 = 'Недействительный токен! Попробуйте изменить почту заново'
    return render_template('message_page.html', title='Ошибка', h1='Ошибка!', h3=h3)


@app.route('/recover_password', methods=['GET', 'POST'])
def recover_password():
    session = db_session.create_session()
    emails = {user.email for user in session.query(User).all()}

    form = ConfirmEmailForm(emails, is_email_edit=False)
    if form.validate_on_submit():
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
    session = db_session.create_session()
    user = get_user(session, int(user_id), False)

    if user.verify_token(token):
        return redirect(url_for('change_password', user_id=user_id))

    h3 = 'Недействительный токен! Попробуйте изменить почту заново'
    return render_template('message_page.html', title='Ошибка', h1='Ошибка!', h3=h3)


@app.route('/change_password/<int:user_id>', methods=['GET', 'POST'])
def change_password(user_id):
    session = db_session.create_session()
    user = get_user(session, int(user_id), False)

    form = EditPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        login_user(user)
        session.commit()

        h3 = f'Вы успешно сменили пароль'
        return render_template('message_page.html', title='Успешно', h1='Успех!', h3=h3)

    return render_template('edit_password_page.html', title='Новый пароль', form=form)


@app.route('/check_email')
def check_email():
    h3 = 'На указанную вами почту отправленно письмо для подтверждения вашей почты'
    return render_template('message_page.html', title='Проверка', h1='Проверьте вашу почту', h3=h3)


@app.route('/delete_avatar/<int:user_id>')
@login_required
def delete_user_avatar(user_id):
    session = db_session.create_session()
    user = get_user(session, user_id)

    if user.img != 'default':
        os.remove(f'static/img/users_img/{user.img}.jpg')
        user.img = 'default'

    session.commit()

    return redirect(url_for('home_page', user_id=user.id))


@app.route('/edit_post_rate', methods=['POST'])
@login_required
def edit_post_rate():
    value = int(request.form['value'])
    post_id = int(request.form['id'])

    session = db_session.create_session()
    post = get_post(session, post_id)

    response = {'is_like': 0, 'is_dislike': 0, 'likes': post.likes, 'dislikes': post.dislikes}
    post_rate = session.query(PostRate).filter(PostRate.post == post,
                                               PostRate.user == current_user).first()

    if value == 2:
        if post_rate:
            response['is_like'] = post_rate.value == 1
            response['is_dislike'] = post_rate.value == -1
        return jsonify(response)

    if not post_rate:
        post_rate = PostRate(
            post_id=post_id,
            user_id=current_user.id,
            value=value
        )
        session.add(post_rate)
        if value == 1:
            post.likes += 1
        elif value == -1:
            post.dislikes += 1
        else:
            raise ValueError(f"Incorrect value. Expected -1 or 1, got {value}")
    else:
        if value == 1:
            if post_rate.value == 1:
                post_rate.value = 0
                post.likes -= 1
            elif post_rate.value in (0, -1):
                if post_rate.value == -1:
                    post.dislikes -= 1
                post_rate.value = 1
                post.likes += 1
            else:
                raise ValueError(f"Incorrect post_rate.value. Expected -1 or 0 or 1, got "
                                 f"{post_rate.value}")
        elif value == -1:
            if post_rate.value == -1:
                post_rate.value = 0
                post.dislikes -= 1
            elif post_rate.value in (0, 1):
                if post_rate.value == 1:
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
    form = AddEditPostForm()
    session = db_session.create_session()
    form.tags.choices = [(tag.name, tag.name) for tag in session.query(Tag).all()]

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        img = form.img.data

        if not (title or content or img):
            return render_template('add_edit_post.html', title='Создать пост', form=form,
                                   message='Хотя бы одно поле должно быть заполненно')

        post = Post(
            title=title,
            content=content,
            author=current_user.id
        )
        post.tags = [session.query(Tag).filter(Tag.name == tag).first() for tag in form.tags.data]
        session.add(post)
        session.commit()

        if request.files.get('img'):
            image_path = str(uuid.uuid4())
            post.img = image_path
            session.commit()

            request.files['img'].save(f'static/img/post_img/{post.id}_{image_path}.jpg')

        return redirect(url_for('home_page', user_id=current_user.id))

    return render_template('add_edit_post.html', title='Изменить пост', form=form, post=0)


@app.route('/edit_post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    session = db_session.create_session()
    post = get_post(session, post_id)

    form = AddEditPostForm()
    form.tags.choices = [(tag.name, tag.name) for tag in session.query(Tag).all()]
    if request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.img.data = post.img
        form.tags.data = [tag.name for tag in post.tags]

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.tags = [session.query(Tag).filter(Tag.name == tag).first() for tag in form.tags.data]

        if request.files.get('img'):
            try:
                os.remove(f'static/img/post_img/{post.id}_{post.img}.jpg')
            except FileNotFoundError:
                print_warning(f'File not found: static/img/post_img/{post.id}_{post.img}.jpg')

            filename = str(uuid.uuid4())
            request.files['img'].save(f'static/img/post_img/{post.id}_{filename}.jpg')
            post.img = filename

        session.commit()

        return redirect(url_for('home_page', user_id=post.author, _anchor=post_id))

    return render_template('add_edit_post.html', title='Изменить пост', form=form, post=post)


@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    session = db_session.create_session()
    post = get_post(session, post_id)

    post.rates.clear()
    session.delete(post)
    session.commit()

    return redirect(url_for('home_page', user_id=current_user.id, _anchor='news'))


@app.route('/friends/<int:user_id>', methods=['GET', 'POST'])
@login_required
def friends(user_id):
    session = db_session.create_session()

    user = get_user(session, user_id, check_auth=False)
    users = user.friends()
    title = 'Мои друзья' if user == current_user else f'Друзья {user.nickname}'

    form = FindUserForm()
    if form.validate_on_submit():
        if not form.nickname.data:
            return redirect(url_for('friends', user_id=user_id))
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title=title, users=users, form=form,
                           method=request.method, c_user=user)


@app.route('/subscribers/<int:user_id>', methods=['GET', 'POST'])
@login_required
def subscribers(user_id):
    session = db_session.create_session()

    user = get_user(session, user_id, check_auth=False)
    users = user.subscribers()
    title = 'Мои подписчики' if user == current_user else f'Подписчики {user.nickname}'

    form = FindUserForm()
    if form.validate_on_submit():
        if not form.nickname.data:
            return redirect(url_for('subscribers', user_id=user_id))
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title=title, users=users, form=form,
                           method=request.method, c_user=user)


@app.route('/offers/<int:user_id>', methods=['GET', 'POST'])
@login_required
def offers(user_id):
    session = db_session.create_session()

    user = get_user(session, user_id, check_auth=False)
    users = user.offers()

    form = FindUserForm()
    if form.validate_on_submit():
        if not form.nickname.data:
            return redirect(url_for('offers', user_id=user_id))
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title='Мои заявки', users=users, form=form,
                           method=request.method, c_user=user)


@app.route('/add_friend_list/<int:user_id>', methods=['GET', 'POST'])
@login_required
def add_friend_page(user_id):
    session = db_session.create_session()
    user = get_user(session, user_id, check_auth=False)

    users = session.query(User).filter(User.id != user_id).all()

    form = FindUserForm()
    if form.validate_on_submit():
        users = list(filter(lambda u: form.nickname.data.lower() in u.nickname.lower(), users))

    return render_template('users_list.html', title='Добавить друга', form=form,
                           method=request.method, c_user=user,
                           pagination=get_user_pagination_info(users, 'add_friend_page'), id=user_id)


@app.route('/friendship_requests', methods=['POST'])
@login_required
def friendship_requests():
    def get_offer_by_ids(from_: list, to_: list):
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

    request_type = request.form['request_type']
    id_from = request.form['id_from']
    id_to = request.form['id_to']

    user_from = get_user(session, id_from)
    user_to = get_user(session, id_to, check_auth=False)
    if request_type not in requests:
        raise ValueError(f'Incorrect request_type. Expected one of {requests}, got {request_type}')

    if request_type == 'add_req':
        offer = FriendshipOffer(id_from=id_from, id_to=id_to)
        session.add(offer)
        user_to.add_notification(session, 'new_friendship_request',
                                 len(user_to.unanswered_subscribers()) + 1)
    elif request_type == 'remove_req':
        offer = get_offer_by_ids([id_from], [id_to])
        session.delete(offer)
        if user_to.need_answer(user_from):
            user_to.add_notification(session, 'new_friendship_request',
                                     len(user_to.unanswered_subscribers()) - 1)
    elif request_type == 'add_friend':
        offer = get_offer_by_ids([id_from, id_to], [id_to, id_from])
        session.delete(offer)

        friend = Friend(id1=id_from, id2=id_to)
        session.add(friend)
    elif request_type == 'remove_friend':
        friend = session.query(Friend).filter(Friend.id1.in_([id_from, id_to]),
                                              Friend.id2.in_([id_from, id_to])).first()
        if not friend:
            raise ValueError(f'There are no friends with pair ids ({id_from}, {id_to})')
        if friend.id1 == friend.id2:
            raise RuntimeError(f'Detected incorrect data in friends table. '
                               f'There is friend note with same ids. Note id: {friend.id}')
        session.delete(friend)

        offer = FriendshipOffer(id_to=id_from, id_from=id_to, is_answered=True)
        session.add(offer)

    session.commit()

    response = get_user_status_info(user_from, user_to)
    return jsonify(response)


@app.route('/answer_offer', methods=['POST'])
@login_required
def answer_for_friendship_offer():
    session = db_session.create_session()

    user_from = get_user(session, request.form['user_from'], check_auth=False)
    user_to = get_user(session, request.form['user_to'])

    offer = session.query(FriendshipOffer).filter(FriendshipOffer.user_from == user_from,
                                                  FriendshipOffer.user_to == user_to).first()
    if not offer:
        raise ValueError(f'There are no FriendshipOffer between {user_from.id} and {user_to.id}')

    offer.is_answered = True
    session.commit()

    return {}


@app.route('/dialogs/<int:user_id>')
@login_required
def user_dialogs(user_id):
    session = db_session.create_session()
    user = get_user(session, user_id, check_auth=False)

    data = {dialog: dialog.messages[-1] for dialog in user.dialogs if list(dialog.messages)}
    data = {dialog: data[dialog] for dialog in
            sorted(data, key=lambda d: data[d].send_date, reverse=True)}

    return render_template('dialogs.html', title='Диалоги', data=data, sender=current_user)


@app.route('/dialog/<int:id_from>/<int:id_to>', methods=['GET', 'POST'])
@login_required
def users_dialog(id_from, id_to):
    session = db_session.create_session()

    user_from = get_user(session, id_from)
    user_to = get_user(session, id_to, check_auth=False)

    dialog = session.query(Dialog).filter(or_(and_(Dialog.id1 == id_from, Dialog.id2 == id_to),
                                              and_(Dialog.id1 == id_to,
                                                   Dialog.id2 == id_from))).first()
    if not dialog:
        dialog = Dialog(id1=id_from, id2=id_to)
        session.add(dialog)
        session.commit()

    msg_ids = []
    for message in dialog.unread_messages(id_from):
        message.is_read = True
        msg_ids.append(str(message.id))
    data = f'{user_from.id} {user_to.id},{" ".join(msg_ids)}'

    session.commit()
    user_from.add_notification(session, 'unread_messages', len(user_from.unread_dialogs()))
    user_to.add_notification(session, 'messages_read', data)

    form = SendMessageForm()
    return render_template('dialog_page.html', title='Диалоги', messages=dialog.messages,
                           user_to=user_to, form=form, dialog=dialog)


@app.route('/append_message', methods=['POST'])
@login_required
def append_message():
    session = db_session.create_session()

    dialog_id = request.form['dialog']
    id_from = request.form['id_from']
    id_to = request.form['id_to']
    content = unquote(request.form['form'].split('=')[1]).replace('+', ' ')

    user_to = get_user(session, id_to, check_auth=False)

    message = Message(
        dialog_id=dialog_id,
        id_from=id_from,
        id_to=id_to,
        content=content
    )
    session.add(message)
    session.commit()

    own_msg = f'''<div id="time_{message.id}" style="color: gray; text-align: right"></div>
                  <div id="message_{message.id}" class="alert alert-primary user-from-message">
                  <span id="message_text_{message.id}" style="color: orangered">Не прочитано - 
                  </span>{message.content}</div>'''
    rec_msg = f'''<div id="time_{message.id}" style="color: gray"></div>
                  <div id="message_{message.id}" class="alert alert-secondary user-to-message">
                  {message.content}</div>'''

    data = {dialog: dialog.messages[-1] for dialog in user_to.dialogs if list(dialog.messages)}
    data = {dialog: data[dialog] for dialog in
            sorted(data, key=lambda d: data[d].send_date, reverse=True)}

    user_to.add_notification(session, 'unread_messages', len(user_to.unread_dialogs()))
    user_to.add_notification(session, 'need_update_dialogs',
                             render_template('_dialogs_card.html', data=data, sender=user_to))
    user_to.add_notification(session, 'need_add_message',
                             f'{message.id}+++{message.send_date}+++{rec_msg}+++{id_from}')

    return {'message_block': own_msg, 'id': message.id, 'time': str(message.send_date)}


@app.route('/messages_read', methods=['POST'])
@login_required
def messages_read():
    session = db_session.create_session()

    user = get_user(session, request.form['user'], check_auth=False)
    message = session.query(Message).get(request.form['id'])

    message.is_read = True
    user.add_notification(session, 'messages_read', f',{message.id}')

    return {}


@app.route('/notifications')
@login_required
def notifications():
    session = db_session.create_session()
    since = request.args.get('since', 0.0, type=float)
    n = session.query(Notification).filter(Notification.timestamp > since, Notification.user ==
                                           current_user).order_by(Notification.timestamp)
    response = [{'name': ntf.name, 'data': ntf.get_data(), 'timestamp': ntf.timestamp}
                for ntf in n]
    for ntf in n:
        session.delete(ntf)
    session.commit()

    return jsonify(response)


if __name__ == '__main__':
    main()
