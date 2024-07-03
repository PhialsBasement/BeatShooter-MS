from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import json
from datetime import datetime

app = Flask(__name__)

# Configure rate limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Configuration
UPLOAD_FOLDER = 'uploads'
LEVELS_FILE = 'levels.json'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_levels():
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_levels(levels):
    with open(LEVELS_FILE, 'w') as f:
        json.dump(levels, f)

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour")  # Limit uploads to 10 per hour
def upload_level():
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file part"}), 400
    
    file = request.files['audio_file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        level_data = {
            "level_name": request.form['level_name'],
            "youtube_link": request.form['youtube_link'],
            "beat_interval": float(request.form['beat_interval']),
            "beat_threshold": float(request.form['beat_threshold']),
            "audio_filename": filename,
            "upload_date": datetime.now().isoformat()
        }
        
        levels = load_levels()
        levels.append(level_data)
        save_levels(levels)
        
        return jsonify({"message": "Level uploaded successfully"}), 200

@app.route('/levels', methods=['GET'])
@limiter.limit("100 per hour")  # Limit level list requests to 100 per hour
def get_levels():
    levels = load_levels()
    return jsonify(levels)

@app.route('/audio/<filename>', methods=['GET'])
@limiter.limit("50 per hour")  # Limit audio downloads to 50 per hour
def get_audio(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))

@app.route('/delete_level/<level_name>', methods=['DELETE'])
@limiter.limit("20 per hour")  # Limit level deletions to 20 per hour
def delete_level(level_name):
    levels = load_levels()
    level_to_delete = next((level for level in levels if level['level_name'] == level_name), None)
    
    if level_to_delete:
        levels.remove(level_to_delete)
        save_levels(levels)
        
        # Delete associated audio file
        audio_path = os.path.join(app.config['UPLOAD_FOLDER'], level_to_delete['audio_filename'])
        if os.path.exists(audio_path):
            os.remove(audio_path)
        
        return jsonify({"message": f"Level '{level_name}' deleted successfully"}), 200
    else:
        return jsonify({"error": f"Level '{level_name}' not found"}), 404

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({"error": "Rate limit exceeded", "message": str(e.description)}), 429

if __name__ == '__main__':
    app.run()