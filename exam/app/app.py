from flask import Flask, render_template, request, redirect, url_for, flash, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import os
from functools import wraps
from models import Book, Review, User, VisitHistory  # Ensure VisitHistory model is imported
from datetime import datetime, timedelta
import hashlib


app = Flask(__name__)

# Конфигурация приложения
app.config['SECRET_KEY'] = 'b3baa1cb519a5651c472d1afa1b3f4e04f1adf6909dae88a4cd39adc0ddd9732'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Настройка Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите, чтобы получить доступ к этой странице.'
login_manager.login_message_category = 'info'

# Модель пользователя
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    @property
    def is_active(self):
        return True  # Пользователь активен

    @property
    def is_authenticated(self):
        return True  # Пользователь прошел аутентификацию

    @property
    def is_anonymous(self):
        return False  # Пользователь не анонимный

    def get_id(self):
        return str(self.id)
    
    def __repr__(self):
        return f'<User {self.email}>'
    
def generate_md5(data):
    return hashlib.md5(data).hexdigest()  # Добавьте это в начало вашего файла

# Модель книги
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    cover_id = db.Column(db.Integer, db.ForeignKey('cover.id'), nullable=False)
    cover = db.relationship('Cover', backref='book', lazy=True)

    def __repr__(self):
        return f'<Book {self.title}>'

# Модель обложки
class Cover(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(150), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False)

    def __repr__(self):
        return f'<Cover {self.filename}>'

# Модель рецензии
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    book = db.relationship('Book', backref='reviews', lazy=True)
    user = db.relationship('User', backref='reviews', lazy=True)

    def __repr__(self):
        return f'<Review {self.id} for Book {self.book_id}>'

# Модель истории посещений
class VisitHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)

    user = db.relationship('User', backref='visit_history', lazy=True)
    book = db.relationship('Book', backref='visit_history', lazy=True)

# Flask-Login user loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Декоратор для проверки роли администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
            return redirect(url_for('index'))  # Перенаправляем на главную страницу
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки роли администратора
def moder_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'moder':
            flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
            return redirect(url_for('index'))  # Перенаправляем на главную страницу
        return f(*args, **kwargs)
    return decorated_function

# Декоратор для проверки роли модератора
def moder_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role not in ['admin', 'moder']:
            flash('У вас недостаточно прав для выполнения данного действия.', 'danger')
            return redirect(url_for('index'))  # Перенаправляем на главную страницу
        return f(*args, **kwargs)
    return decorated_function

# Главная страница
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Количество книг на странице
    books_query = Book.query.order_by(Book.year.desc())
    books = books_query.paginate(page=page, per_page=per_page)

    # Популярные книги
    three_months_ago = datetime.utcnow() - timedelta(days=90)
    popular_books = db.session.query(
        Book,
        db.func.count(VisitHistory.id).label('visit_count')
    ).join(VisitHistory).filter(
        VisitHistory.timestamp >= three_months_ago
    ).group_by(Book.id).order_by(db.desc('visit_count')).limit(5).all()

    # Недавно просмотренные книги
    if current_user.is_authenticated:
        recently_viewed_books = VisitHistory.query.filter_by(user_id=current_user.id).order_by(VisitHistory.timestamp.desc()).limit(5).all()
    else:
        recently_viewed_books = []

    return render_template('index.html', books=books, popular_books=popular_books, recently_viewed_books=recently_viewed_books)

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')
            return render_template('login.html')

        login_user(user, remember=remember)
        flash('Вы успешно вошли в систему!', 'success')
        return redirect(url_for('index'))

    return render_template('login.html')

# Страница выхода
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

# Обработчик для страницы регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        name = request.form['name']

        # Проверка на уникальность пользователя
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует.')
            return redirect(url_for('register'))

        # Создание нового пользователя
        new_user = User(
            email=email,
            password=generate_password_hash(password),
            name=name,
            role='user'  # Назначаем роль "user" по умолчанию
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Регистрация успешна! Вы можете войти.')
        return redirect(url_for('login'))

    return render_template('register.html')

# Страница добавления книги
@app.route('/add-book', methods=['GET', 'POST'])
@login_required
@admin_required  # Защита маршрута для администратора
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        year = request.form.get('year')
        publisher = request.form.get('publisher')
        author = request.form.get('author')
        pages = request.form.get('pages')

        # Обработка файла обложки
        cover_file = request.files.get('cover')  # Используйте .get() для обработки ошибок
        cover = None  # Инициализация переменной cover
        if cover_file:
            cover_filename = cover_file.filename
            cover_mime_type = cover_file.content_type
            cover_md5_hash = generate_md5(cover_file.read())
            cover = Cover(filename=cover_filename, mime_type=cover_mime_type, md5_hash=cover_md5_hash)
            db.session.add(cover)
            db.session.commit()  # Добавьте скобки для выполнения commit()

        # Добавление книги
        book = Book(title=title, description=description, year=year, publisher=publisher, author=author, pages=pages, cover=cover)
        db.session.add(book)
        db.session.commit()  # Добавьте скобки для выполнения commit()

        flash('Книга успешно добавлена!', 'success')
        return redirect(url_for('index'))  # Перенаправление после добавления книги

    return render_template('add_book.html')  # Возвращаем страницу добавления книги

# Страница редактирования книги
@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
@moder_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    if request.method == 'POST':
        # Обновление данных книги
        book.title = request.form.get('title')
        book.description = request.form.get('description')
        book.year = request.form.get('year')
        book.publisher = request.form.get('publisher')
        book.author = request.form.get('author')
        book.pages = request.form.get('pages')

        # Если загружается новая обложка
        if 'cover' in request.files:
            cover_file = request.files['cover']
            if cover_file:
                cover_filename = cover_file.filename
                cover_mime_type = cover_file.content_type
                cover_md5_hash = generate_md5(cover_file.read())
                cover = Cover(filename=cover_filename, mime_type=cover_mime_type, md5_hash=cover_md5_hash)
                db.session.add(cover)
                db.session.commit()
                book.cover = cover  # Обновляем обложку книги

        db.session.commit()
        flash('Книга успешно обновлена!', 'success')
        return redirect(url_for('view_book', book_id=book.id))

    return render_template('edit_book.html', book=book)

# Страница удаления книги
@app.route('/delete_book/<int:book_id>', methods=['POST'])
@login_required
@admin_required  # Защита маршрута для администратора
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    db.session.delete(book)
    db.session.commit()

    flash('Книга успешно удалена!', 'success')
    return redirect(url_for('index'))

# Страница просмотра книги
@app.route('/book/<int:book_id>')
def view_book(book_id):
    book = Book.query.get_or_404(book_id)

    # Логирование посещения
    if current_user.is_authenticated:
        today = datetime.utcnow().date()
        visit_count = VisitHistory.query.filter(
            VisitHistory.user_id == current_user.id,
            VisitHistory.book_id == book.id,
            VisitHistory.timestamp >= today
        ).count()

        if visit_count < 10:  # Ограничение до 10 посещений книги в день
            visit = VisitHistory(user_id=current_user.id, book_id=book.id)
            db.session.add(visit)
            db.session.commit()

    reviews = Review.query.filter_by(book_id=book.id).all() 
    return render_template('view_book.html', book=book, reviews=reviews, current_user=current_user)


# Страница добавления рецензии
@app.route('/book/<int:book_id>/review', methods=['GET', 'POST'])
@login_required
def add_review(book_id):
    book = Book.query.get_or_404(book_id)
    
    existing_review = Review.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing_review:
        flash('Вы уже оставляли рецензию на эту книгу.', 'danger')
        return redirect(url_for('view_book', book_id=book_id))

    if request.method == 'POST':
        rating = request.form.get('rating')
        text = request.form.get('text')
        review = Review(book_id=book_id, user_id=current_user.id, rating=rating, text=text)
        db.session.add(review)
        db.session.commit()

        flash('Рецензия успешно добавлена!', 'success')
        return redirect(url_for('view_book', book_id=book_id))

    return render_template('add_review.html', book=book)

@app.route('/admin/statistics')
@login_required
@admin_required
def admin_statistics():
    return render_template('admin_statistics.html')

@app.route('/admin/statistics/user-log')
@login_required
@admin_required
def user_log():
    page = request.args.get('page', 1, type=int)
    logs = VisitHistory.query.order_by(VisitHistory.timestamp.desc()).paginate(page=page, per_page=10)
    return render_template('user_log.html', logs=logs)

@app.route('/admin/statistics/book-stats')
@login_required
@admin_required
def book_stats():
    page = request.args.get('page', 1, type=int)
    stats = db.session.query(
        Book,
        db.func.count(VisitHistory.id).label('view_count')
    ).join(VisitHistory).group_by(Book.id).order_by(db.desc('view_count')).paginate(page=page, per_page=10)
    return render_template('book_stats.html', stats=stats)

@app.route('/admin/statistics/user-log/export')
@login_required
@admin_required
def export_user_log():
    logs = VisitHistory.query.order_by(VisitHistory.timestamp.desc()).all()
    return export_to_csv(logs, 'user_log.csv')

@app.route('/admin/statistics/book-stats/export')
@login_required
@admin_required
def export_book_stats():
    stats = db.session.query(
        Book,
        db.func.count(VisitHistory.id).label('view_count')
    ).join(VisitHistory).group_by(Book.id).all()
    return export_to_csv(stats, 'book_stats.csv')

def export_to_csv(data, filename):
    def generate():
        yield 'Пользователь, Книга, Дата и время\n'  # Заголовок
        for item in data:
            user_name = item.user.name if item.user else 'Неаутентифицированный пользователь'
            yield f"{user_name}, {item.book.title}, {item.timestamp}\n"
    
    return Response(generate(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={filename}'})




with app.app_context():
    db.create_all()
