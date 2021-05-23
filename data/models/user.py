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

    nickname = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    email = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
    img = sqlalchemy.Column(sqlalchemy.String, default='default')
    status = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    sex = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    education = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    marital_status = sqlalchemy.Column(sqlalchemy.String, default='Не указано')
    birthday = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime(1800, 1, 1))
    about_me = sqlalchemy.Column(sqlalchemy.String, default='Не указано')

    password = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    create_date = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime.utcnow)
    last_seen = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime.utcnow)

    posts = orm.relation("Post", back_populates="user", order_by='desc(Post.create_date)',
                         lazy='subquery')
    rates = orm.relation("PostRate", back_populates="user", lazy='subquery')

    _subscribers = orm.relationship("FriendshipOffer", back_populates='user_to', lazy='dynamic',
                                    primaryjoin='User.id == FriendshipOffer.id_to')
    _offers = orm.relationship('FriendshipOffer', back_populates='user_from', lazy='dynamic',
                               primaryjoin='User.id == FriendshipOffer.id_from')
    _friends = orm.relationship('Friend', lazy='dynamic',
                                primaryjoin='or_(User.id == Friend.id1, User.id == Friend.id2)')
    dialogs = orm.relationship('Dialog', lazy='subquery',
                               primaryjoin='or_(User.id == Dialog.id1, User.id == Dialog.id2)')
    messages = orm.relationship('Message', back_populates='user_to', lazy='subquery',
                                primaryjoin='User.id == Message.id_to')
    notifications = orm.relationship('Notification', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password) -> bool:
        return check_password_hash(self.password, password)

    def get_token(self, expires_in=300):
        return jwt.encode({'user': self.nickname, 'exp': time.time() + expires_in},
                          Config.SECRET_KEY, algorithm='HS256')

    @staticmethod
    def verify_token(token):
        try:
            user_id = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])['user']
        except Exception:
            return
        return user_id

    def add_notification(self, session, name, data):
        self.notifications.filter_by(name=name).delete()
        notification = Notification(name=name, data=json.dumps(data), user=self)

        session.add(notification)
        session.commit()
        return notification

    def age(self) -> str:
        born = self.birthday
        today = dt.date.today()

        if born != dt.datetime(1800, 1, 1):
            return str(today.year - born.year - ((today.month, today.day) < (born.month, born.day)))
        else:
            return 'Не указано'

    def subscribers(self):
        return [offer.user_from for offer in self._subscribers]

    def offers(self):
        return [offer.user_to for offer in self._offers]

    def friends(self):
        return [friend.user1 if friend.user1 != self else friend.user2 for friend in self._friends]

    def unread_dialogs(self):
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

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, index=True)

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user = orm.relationship('User', lazy='subquery')

    timestamp = sqlalchemy.Column(sqlalchemy.Float, index=True, default=time.time)
    data = sqlalchemy.Column(sqlalchemy.String)

    def get_data(self):
        return json.loads(str(self.data))
