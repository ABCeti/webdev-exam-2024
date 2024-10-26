import os

SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'b3baa1cb519a5651c472d1afa1b3f4e04f1adf6909dae88a4cd39adc0ddd9732'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
