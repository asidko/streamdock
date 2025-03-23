from flask import Flask
from .routes import main_bp
import os
import logging
import json

def create_app():
    app = Flask(
        __name__, 
        template_folder=os.path.join(os.path.dirname(__file__), '../templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '../static')
    )

    logging.basicConfig(level=logging.ERROR)

    # Priority: Environment variable > config.json
    m3u_url_env = os.environ.get('M3U_URL')
    if m3u_url_env:
        app.config['M3U_URL'] = m3u_url_env
        logging.info(f"M3U URL loaded from environment: {app.config['M3U_URL']}")
    else:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as config_file:
                try:
                    config_data = json.load(config_file)
                    app.config['M3U_URL'] = config_data.get('m3u_url', '')
                    app.config['LANGUAGE'] = config_data.get('language', 'en')
                    logging.info(f"M3U URL loaded from config.json: {app.config['M3U_URL']}")
                    logging.info(f"Language loaded from config.json: {app.config['LANGUAGE']}")
                except json.JSONDecodeError:
                    app.config['M3U_URL'] = ''
                    app.config['LANGUAGE'] = 'en'
                    logging.error("Error parsing config.json. Default settings applied.")
        else:
            app.config['M3U_URL'] = ''
            app.config['LANGUAGE'] = 'en'
            logging.warning("config.json not found. Default settings applied.")

    # Environmental override for language
    lang_env = os.environ.get('LANGUAGE')
    if lang_env:
        app.config['LANGUAGE'] = lang_env
        logging.info(f"Language loaded from environment: {app.config['LANGUAGE']}")

    with app.app_context():
        app.register_blueprint(main_bp)

    stream_cache_path = os.path.join(app.static_folder, 'stream_cache')
    if not os.path.exists(stream_cache_path):
        os.makedirs(stream_cache_path)
        logging.info(f"Created stream cache folder: {stream_cache_path}")

    return app
