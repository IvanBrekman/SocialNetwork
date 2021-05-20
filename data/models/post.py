import sqlalchemy
import datetime as dt

from sqlalchemy import orm
from ..db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin

association_table = sqlalchemy.Table(
    'posts_to_tags',
    SqlAlchemyBase.metadata,
    sqlalchemy.Column('post_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('posts.id')),
    sqlalchemy.Column('tag_id', sqlalchemy.Integer, sqlalchemy.ForeignKey('tags.id'))
)


class Post(SqlAlchemyBase, SerializerMixin):
    """ Класс-модель. Таблица постов для базы данных """

    __tablename__ = 'posts'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    title = sqlalchemy.Column(sqlalchemy.String)
    content = sqlalchemy.Column(sqlalchemy.String)
    img = sqlalchemy.Column(sqlalchemy.String)

    likes = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)
    dislikes = sqlalchemy.Column(sqlalchemy.Integer, default=0, nullable=False)

    author = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user = orm.relation('User')

    rates = orm.relation('PostRate', back_populates='post', lazy='subquery')
    tags = orm.relation('Tag', secondary='posts_to_tags', backref='post_id', lazy='subquery')

    create_date = sqlalchemy.Column(sqlalchemy.DateTime, default=dt.datetime.utcnow)


class PostRate(SqlAlchemyBase, SerializerMixin):
    """ Класс-модель. Таблица связи постов с пользователями и их оценкой поста для базы данных """

    __tablename__ = 'post_rate'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)

    post_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('posts.id'))
    post = orm.relation('Post', lazy='subquery')

    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    user = orm.relation('User', lazy='subquery')

    value = sqlalchemy.Column(sqlalchemy.Integer)


class Tag(SqlAlchemyBase):
    """ Класс-модель. Таблица тэгов нвостей для базы данных """

    __tablename__ = 'tags'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False, unique=True)
