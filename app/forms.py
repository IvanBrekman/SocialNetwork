from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, PasswordField, TextAreaField, \
    SubmitField, BooleanField, FileField, SelectMultipleField, RadioField
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, EqualTo, Email, ValidationError

marital_statuses = ['Не указано', 'Не женат/Не замужем', 'Помолвлен(а)', 'Женат/Замужем',
                    'В гражданском браке', 'Влюблен(а)', 'Все сложно', 'В активном поиске',
                    'Встречаюсь']
sort_types = [('create_date', 'Дате создания'), ('likes', 'Лайкам'), ('dislikes', 'Дизлайкам')]


class RegistrationForm(FlaskForm):
    nickname = StringField("Никнейм", validators=[DataRequired()])
    email = EmailField("Email", validators=[DataRequired(), Email()])

    mes = "Указанные пароли не сходятся"
    password = PasswordField("Пароль", validators=[DataRequired()])
    password_again = PasswordField("Повторите пароль", validators=[DataRequired(),
                                                                   EqualTo("password", message=mes)])
    submit = SubmitField('Зарегистрироваться')


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])

    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class EditUserForm(FlaskForm):
    avatar = FileField('Выберите изображение')
    nickname = StringField("Никнейм", validators=[DataRequired()])
    status = StringField('Статус')
    sex = SelectField('Пол', choices=['Не указано', 'Мужской', 'Женский'])
    education = StringField('Образование')
    marital_status = SelectField('Семейный статус', choices=marital_statuses)
    birthday = StringField('День Рождения')
    remove_birthday = BooleanField('Убрать')
    about_me = TextAreaField('Обо мне')

    submit = SubmitField('Изменить')


class ConfirmEmailForm(FlaskForm):
    email = EmailField('Укажите новую почту', validators=[DataRequired(), Email()])
    submit = SubmitField('Подтвердить изменение')

    def __init__(self, emails, user_email=None, is_email_edit=True, *args, **kwargs):
        super(ConfirmEmailForm, self).__init__(*args, **kwargs)
        self.emails = emails
        self.user_email = user_email
        self.is_email_edit = is_email_edit

        if not is_email_edit:
            self.email.label = 'Укажите вашу почту'

    def validate_email(self, email):
        return self.email_change(email) if self.is_email_edit else self.password_recover(email)

    def email_change(self, email):
        if email.data == self.user_email:
            raise ValidationError('Это текущая ваша почта')
        if email.data in self.emails:
            raise ValidationError('Пользователь с такой почтой уже зарегистрирован')
        return True

    def password_recover(self, email):
        if email.data not in self.emails:
            raise ValidationError('Пользователь с указанной почтой не найден')
        return True


class EditPasswordForm(FlaskForm):
    mes = "Указанные пароли не сходятся"
    password = PasswordField("Новый Пароль", validators=[DataRequired()])
    password_again = PasswordField("Повторите пароль", validators=[DataRequired(),
                                                                   EqualTo("password", message=mes)])
    submit = SubmitField('Изменить')


class AddEditPostForm(FlaskForm):
    title = StringField('Заголовок поста')
    content = TextAreaField('Контент поста')
    tags = SelectMultipleField('Тэги к посту')

    img = FileField('Картинка к посту')

    submit = SubmitField('Изменить')


class DisplayPostForm(FlaskForm):
    tags = SelectMultipleField('Выберите тэги')
    sort_by = SelectField('Сортировать по', choices=sort_types)
    sort_type = RadioField(choices=[('asc', 'По возрастанию'), ('desc', 'По убыванию')])

    apply_btn = SubmitField('Применить')
    default_btn = SubmitField('По умолчанию')


class FindUserForm(FlaskForm):
    nickname = StringField('')
    submit = SubmitField('Найти')


class SendMessageForm(FlaskForm):
    message = StringField('Ваше сообщение', validators=[DataRequired()])
    submit = SubmitField('▲')
