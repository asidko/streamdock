from flask import render_template, Blueprint, jsonify, request, current_app, send_file, g, redirect, url_for, session
from .m3u_parser import parse_m3u_channels_and_categories
import os
import logging
import json
import requests
from io import BytesIO


main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    lang = current_app.config.get('LANGUAGE', 'en')
    return render_template('index.html', lang=lang)

@main_bp.route('/api/categories')
def get_categories():
    m3u_url = current_app.config.get('M3U_URL', '')
    if not m3u_url:
        logging.error("No M3U URL configured.")
        return jsonify({"categories": []})
    
    categories = parse_m3u_channels_and_categories(m3u_url)
    return jsonify({"categories": categories})

@main_bp.route('/category/<category_name>')
def get_category_channels(category_name):
    m3u_url = current_app.config.get('M3U_URL', '')
    if not m3u_url:
        logging.error("No M3U URL configured.")
        channels = []
    else:
        categories = parse_m3u_channels_and_categories(m3u_url)
        
        category = next((cat for cat in categories if cat['name'] == category_name), None)
        channels = category['channels'] if category else []
    return jsonify(channels)

@main_bp.route('/proxy_image')
def proxy_image():
    image_url = request.args.get('url')
    
    if not image_url:
        return jsonify({"error": "No image URL provided"}), 400

    try:
        response = requests.get(image_url, stream=True, timeout=5)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', 'image/png')

        return send_file(BytesIO(response.content), mimetype=content_type)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error proxying image: {e}")
        # Fallback to a default image if proxying fails
        default_icon_path = os.path.join(current_app.static_folder, 'default-logo_light.png')
        if os.path.exists(default_icon_path):
            return send_file(default_icon_path, mimetype='image/png')
        else:
            return jsonify({"error": "Default image not found"}), 500

@main_bp.route('/api/language')
def get_language():
    lang = current_app.config.get('LANGUAGE', 'en')
    lang_file_path = os.path.join(current_app.static_folder, f'lang/{lang}.json')
    
    try:
        with open(lang_file_path, 'r', encoding='utf-8') as lang_file:
            translations = json.load(lang_file)
            return jsonify(translations)
    except Exception as e:
        logging.error(f"Error loading language file: {e}")
        # If error, return empty translations
        return jsonify({})

@main_bp.route('/language/<lang_code>')
def change_language(lang_code):
    # Validate language code
    if lang_code not in ['en', 'uk']:
        return jsonify({"error": "Invalid language code"}), 400
    
    # Update config file
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as config_file:
                config_data = json.load(config_file)
        else:
            config_data = {}
        
        config_data['language'] = lang_code
        
        with open(config_path, 'w', encoding='utf-8') as config_file:
            json.dump(config_data, config_file, indent=4)
        
        # Update app config
        current_app.config['LANGUAGE'] = lang_code
        logging.info(f"Language changed to: {lang_code}")
        
        # Redirect to referring page or home
        referrer = request.referrer
        if referrer:
            return redirect(referrer)
        return redirect(url_for('main.index'))
    
    except Exception as e:
        logging.error(f"Error changing language: {e}")
        return jsonify({"error": "Failed to change language"}), 500

@main_bp.route('/get_stream', methods=['POST'])
def get_stream():
    """
    Endpoint to get the stream URL for a given stream URL.
    Expects JSON data with 'stream_url'.
    """
    data = request.get_json()
    stream_url = data.get('stream_url')

    if not stream_url:
        return jsonify({'error': 'No stream URL provided'}), 400

    
    return jsonify({'stream_url': stream_url}), 200


@main_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')
    lang = current_app.config.get('LANGUAGE', 'en')

    if request.method == 'POST':
        m3u_url = request.form.get('m3u_url', '').strip()
        if m3u_url:
            
            # Delete the cached playlist.json file to force re-parsing
            playlist_json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'playlist.json')
            if os.path.exists(playlist_json_path):
                try:
                    os.remove(playlist_json_path)
                    logging.info(f"Removed cached playlist file: {playlist_json_path}")
                except Exception as e:
                    logging.error(f"Failed to remove cached playlist file: {e}")
            
            # Save the new config
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as config_file:
                        config_data = json.load(config_file)
                else:
                    config_data = {}

                config_data['m3u_url'] = m3u_url
                # Preserve language setting if it exists
                if 'language' not in config_data:
                    config_data['language'] = current_app.config.get('LANGUAGE', 'en')
                
                with open(config_path, 'w', encoding='utf-8') as config_file:
                    json.dump(config_data, config_file, indent=4)
                
                current_app.config['M3U_URL'] = m3u_url
                logging.info(f"M3U URL updated: {m3u_url}")
                
                # Clear any existing channels and categories from memory
                if hasattr(g, 'categories'):
                    delattr(g, 'categories')
                
                success_message = "M3U URL successfully updated."
                return render_template('settings.html', success=success_message, m3u_url=m3u_url, lang=lang)
            except Exception as e:
                logging.error(f"Error updating M3U URL: {e}")
                return render_template('settings.html', error="Error updating the M3U URL.", m3u_url=m3u_url, lang=lang)
        else:
            return render_template('settings.html', error="Please provide a valid M3U URL.", m3u_url=m3u_url, lang=lang)
    else:
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as config_file:
                    config_data = json.load(config_file)
                    m3u_url = config_data.get('m3u_url', '')
            except json.JSONDecodeError:
                m3u_url = ''
                logging.error("Error parsing config.json.")
        else:
            m3u_url = ''
            logging.warning("config.json not found.")
        return render_template('settings.html', m3u_url=m3u_url, lang=lang)
