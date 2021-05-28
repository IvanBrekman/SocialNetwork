import jwt
import time
import json

import sqlalchemy
import datetime as dt

from app.config import Config
from sqlalchemy import orm
from flask_login import UserMixin
from ..db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    """ Класс-модель. Таблица пользователей для базы данных """

    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    sid = sqlalchemy.Column(sqlalchemy.String)

    # Информация о пользователе
    nickname = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    img = sqlalchemy.Column(sqlalchemy.String, default='default')
    status = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    sex = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    education = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    marital_status = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    birthday = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime(1800, 1, 1))
    about_me = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    #

    # Важные данные пользователя
    password = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    create_date = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime.utcnow)
    last_seen = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime.utcnow)
    #

    # Связи пользователя с различными моделями
    posts = orm.relation("Post", back_populates="user", order_by='desc(Post.create_date)',
                         lazy='subquery')
    rates = orm.relation("PostRate", back_populates="user", lazy='subquery')

    _subscribers = orm.relationship("FriendshipOffer", back_populates='user_to', lazy='dynamic',
                                    primaryjoin='User.id == FriendshipOffer.id_to')
    _offers = orm.relationship('FriendshipOffer', back_populates='user_from', lazy='dynamic',
                               primaryjoin='User.id == FriendshipOffer.id_from')
    _friends = orm.relationship('Friend', lazy='dynamic',
                                primaryjoin='or_(User.id == Friend.id1, User.id == Friend.id2)')
    _unanswered_ss = orm.relationship("FriendshipOffer", back_populates='user_to', lazy='subquery',
                                      primaryjoin='User.id == FriendshipOffer.id_to and not '
                                                  'FriendshipOffer.is_answered')
    dialogs = orm.relationship('Dialog', lazy='subquery',
                               primaryjoin='or_(User.id == Dialog.id1, User.id == Dialog.id2)')
    messages = orm.relationship('Message', back_populates='user_to', lazy='subquery',
                                primaryjoin='User.id == Message.id_to')
    notifications = orm.relationship('Notification', back_populates='user', lazy='dynamic')
    #

    def set_password(self, password):
        """ Метод устанавливает хэшированный пароль для пользователя """
        self.password = generate_password_hash(password)

    def check_password(self, password) -> bool:
        """ Метод проверяет пароль """
        return check_password_hash(self.password, password)

    def set_sid(self, sid):
        """ Метод устанавливает значение sid для подключение к WebSocket серверу """
        self.sid = sid

    def get_token(self, expires_in=300):
        """ Метод генерирует токен для пользователя """
        return jwt.encode({'user': self.nickname, 'exp': time.time() + expires_in},
                          Config.SECRET_KEY, algorithm='HS256')

    @staticmethod
    def verify_token(token):
        """ Метод проверяет токен на действительность """
        try:
            user_id = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])['user']
        except Exception:
            return
        return user_id

    def add_notification(self, session, name, data):
        """ Метод создает уведомление с указанным названием и информацией """
        notification = Notification(name=name, data=json.dumps(data), user=self)

        session.add(notification)
        session.commit()
        return notification

    def age(self) -> str:
        """ Метод возвращает возраст пользователя, основываясь на его дне рождения """
        born = self.birthday
        today = dt.date.today()

        if born != dt.datetime(1800, 1, 1):
            return str(today.year - born.year - ((today.month, today.day) < (born.month, born.day)))
        else:
            return 'Не указано'

    def subscribers(self):
        """ Метод возвращает список подписчиков пользователя """
        return [offer.user_from for offer in sorted(self._subscribers, key=lambda o: o.is_answered)]

    def unanswered_subscribers(self):
        """ Метод возвращает список подписчиков пользователя, которые ожидают ответ на запрос """
        return [offer for offer in self._unanswered_ss if not offer.is_answered]

    def need_answer(self, user):
        """ Метод проверяет нужно ли пользователю отвечать на запрос User-а """
        for offer in self._unanswered_ss:
            if offer.user_from == user and not offer.is_answered:
                return True
        return False

    def offers(self):
        """ Метод возвращает список пользователей, которым отправлен запрос дружбы """
        return [offer.user_to for offer in self._offers]

    def friends(self):
        """ Метод возвращает список друзей пользователя """
        return [friend.user1 if friend.user1 != self else friend.user2 for friend in self._friends]

    def unread_dialogs(self):
        """ Метод возвращает словарь диалогов с непрочитанными сообщениями для каждого диалога """

        dialogs = {}
        for mes in [message for message in self.messages if not message.is_read]:
            if dialogs.get(mes.id_from):
                dialogs.get(mes.id_from).append(mes)
            else:
                dialogs[mes.id_from] = [mes]

        return dialogs


class Notification(SqlAlchemyBase, SerializerMixin):
    """ Класс-модель для хранения уведомлений для обновления на стороне клиента """

    __tablename__ = 'notifications'

    # Название уведомления
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, index=True)
    #

    # Пользователь, которому отправлено уведомление
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user = orm.relationship('User', lazy='subquery')
    #

    # Data уведомления
    timestamp = sqlalchemy.Column(sqlalchemy.Float, index=True, default=time.time)
    data = sqlalchemy.Column(sqlalchemy.String)
    #

    def get_data(self):
        """ Получает информацию в виде json """
        return json.loads(str(self.data))
