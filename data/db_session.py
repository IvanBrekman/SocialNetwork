import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import sqlalchemy.ext.declarative as dec


SqlAlchemyBase = dec.declarative_base()  # Создаем объект базы данных

__factory = None


def global_init(db_file: str, echo=False) -> None:
    """
    Функция инициализирует базу данных, выбирает движок, и создает метаданные таблиц
    :param db_file: Путь к файлу базы данных
    :param echo: Необходимость отображать запросы sqlalchemy
    :return: None
    """

    global __factory

    if __factory:  # Проверка на созданную сессию
        return

    if not db_file or not db_file.strip():
        raise ValueError("Excepted path to db file, got nothing instead")

    conn_str = f"sqlite:///{db_file.strip()}?check_same_thread=False"
    print(f"Подключение к базе данных по адресу: {conn_str}")

    engine = sa.create_engine(conn_str, echo=echo)
    __factory = orm.sessionmaker(bind=engine)

    from . import __all_models  # Загрузка всех моделей

    SqlAlchemyBase.metadata.create_all(engine)


def create_session() -> Session:
    """
    Функция создают сессию общения с базой данных
    :return: Объект типа Session для общения с базой данных
    """

    global __factory
    assert isinstance(__factory, orm.sessionmaker), f"Wrong type of __factory. Excepted " \
                                                    f"orm.sessionmaker, got {type(__factory)}"
    return __factory()
