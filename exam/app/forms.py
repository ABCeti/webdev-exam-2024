from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, TextAreaField, FileField, IntegerField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    login = StringField('Логин', validators=[DataRequired(), Length(max=80)])
    password = PasswordField('Пароль', validators=[DataRequired()])

class BookForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired()])
    description = TextAreaField('Описание', validators=[DataRequired()])
    year = IntegerField('Год', validators=[DataRequired()])
    publisher = StringField('Издательство', validators=[DataRequired()])
    author = StringField('Автор', validators=[DataRequired()])
    pages = IntegerField('Страниц', validators=[DataRequired()])
    cover = FileField('Обложка')

class ReviewForm(FlaskForm):
    rating = SelectField('Оценка', choices=[(5, 'Отлично'), (4, 'Хорошо'), (3, 'Удовлетворительно'),
                                              (2, 'Неудовлетворительно'), (1, 'Плохо'), (0, 'Ужасно')],
                         default=5)
    text = TextAreaField('Текст рецензии', validators=[DataRequired()])
