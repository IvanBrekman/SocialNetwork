import sqlalchemy
from sqlalchemy import orm
from ..db_session import SqlAlchemyBase


class FriendshipOffer(SqlAlchemyBase):
    """ Класс-модель для описания предложений дружбы """

    __tablename__ = 'friendship_offers'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    # Пользователь, отправивший запрос дружбы
    id_from = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user_from = orm.relationship('User', foreign_keys=[id_from], lazy='subquery')
    #

    # Пользователь, получивший запрос дружбы
    id_to = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user_to = orm.relationship('User', foreign_keys=[id_to], lazy='subquery')
    #

    # Состояние ответа на запрос
    is_answered = sqlalchemy.Column(sqlalchemy.Boolean, default=False)


class Friend(SqlAlchemyBase):
    """ Класс-модель для описания друзей """

    __tablename__ = 'friends'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    # Первый участник дружбы
    id1 = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user1 = orm.relationship('User', foreign_keys=[id1], lazy='subquery')
    #

    # Второй участник дружбы
    id2 = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user2 = orm.relationship('User', foreign_keys=[id2], lazy='subquery')
    #
