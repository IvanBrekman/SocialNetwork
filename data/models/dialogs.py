import sqlalchemy
import datetime as dt

from sqlalchemy import orm
from ..db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Dialog(SqlAlchemyBase, SerializerMixin):
    """ Класс-модель для описания диалогов пользователей в базе данных """

    __tablename__ = 'dialogs'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    # Первый участник диалога
    id1 = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user1 = orm.relationship('User', foreign_keys=[id1], lazy='subquery')
    #

    # Второй участник диалога
    id2 = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user2 = orm.relationship('User', foreign_keys=[id2], lazy='subquery')
    #

    # Все сообщения диалога
    messages = orm.relationship('Message', back_populates='dialog', order_by='Message.send_date',
                                lazy='dynamic')

    def unread_messages_amount(self, id_from):
        """ Метод возвращает количество непрочитанных сообщений в диалоге """

        unw = filter(lambda message: message.id_from != id_from and not message.is_read,
                     self.messages)
        return sum(1 for _ in unw)

    def unread_messages(self, id_from):
        """ Метод возвращает список непрочитанных сообщений """
        return self.messages.filter(Message.id_from != id_from, Message.is_read == 0).all()


class Message(SqlAlchemyBase, SerializerMixin):
    """ Класс-модель для описания сообщений в диалогах пользователей в базе данных """

    __tablename__ = 'messages'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    # Диалог, к которому привязано сообщение
    dialog_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('dialogs.id'))
    dialog = orm.relationship('Dialog')
    #

    # Пользователь, отправивший сообщение
    id_from = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user_from = orm.relationship('User', foreign_keys=[id_from], lazy='subquery')
    #

    # Пользователь, получивший сообщение
    id_to = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user_to = orm.relationship('User', foreign_keys=[id_to], lazy='subquery')
    #

    # Данные сообщения
    content = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    send_date = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime.utcnow)
    is_read = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    #

    def get_abbreviated_message(self, length):
        """ Метод возвращает строку текста сообщения, обрезанную до длины length """

        if len(self.content) > length:
            return self.content[:length - 3] + '...'
        return self.content
