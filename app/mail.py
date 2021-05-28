from flask import Flask
from flask_mail import Message, Mail
from threading import Thread


def send_async_email(app: Flask, mail: Mail, msg: Message):
    """ Асинхронная функция отправки сообщение на почту """

    with app.app_context():
        mail.send(msg)


def send_email(app: Flask, mail: Mail, subject: str, sender: str, recipients: list, html_body: str):
    """ Генерация сообщения для отправки на почту """

    msg = Message(subject, sender=sender, recipients=recipients)
    msg.html = html_body
    Thread(target=send_async_email, args=(app, mail, msg)).start()


if __name__ == '__main__':
    pass
