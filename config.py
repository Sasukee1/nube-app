import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '3ce9b59971msh811c8c77ac997d9p1523b8jsne352837f2575'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'nubenet.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # RapidAPI TikTok
    RAPIDAPI_HOST = "tiktok-downloader27.p.rapidapi.com"
    RAPIDAPI_KEY = "3ce9b59971msh811c8c77ac997d9p1523b8jsne352837f2575"
    

