from flask import Flask, request, redirect, url_for, render_template, session, flash, jsonify
import requests
from pytube import YouTube
import os
import threading
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # کلید مخفی برای مدیریت نشست‌ها

# اطلاعات ورود
USERNAME = 'your_username'  # نام کاربری
PASSWORD = 'your_password'  # رمز عبور

# لینک‌های آپارات و ایفویلو
APARAT_UPLOAD_URL = 'https://www.aparat.com/upload'
IFILO_UPLOAD_URL = 'https://ifilo.net/upload'

# دایرکتوری برای ذخیره ویدیوها
DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def download_youtube_video(url):
    """دانلود ویدیو از یوتیوب و بازگشت مسیر فایل دانلود شده."""
    try:
        yt = YouTube(url)
        video_stream = yt.streams.get_highest_resolution()
        video_file = video_stream.download(output_path=DOWNLOAD_DIR)
        return video_file
    except Exception as e:
        print(f"Error downloading YouTube video: {e}")
        return None

def download_telegram_file(file_url):
    """دانلود فایل از تلگرام."""
    try:
        response = requests.get(file_url)
        file_name = file_url.split('/')[-1]
        with open(os.path.join(DOWNLOAD_DIR, file_name), 'wb') as f:
            f.write(response.content)
        return os.path.join(DOWNLOAD_DIR, file_name)
    except Exception as e:
        print(f"Error downloading Telegram file: {e}")
        return None

def upload_video_to_aparat(video_path, title, description):
    """آپلود ویدیو به آپارات."""
    try:
        with open(video_path, 'rb') as video_file:
            files = {'file': video_file}
            data = {'title': title, 'description': description}
            response = requests.post(APARAT_UPLOAD_URL, files=files, data=data)
            return response.ok
    except Exception as e:
        print(f"Error uploading video to Aparat: {e}")
        return False

def upload_video_to_ifilo(video_path, title, description):
    """آپلود ویدیو به ایفویلو."""
    try:
        with open(video_path, 'rb') as video_file:
            files = {'file': video_file}
            data = {'title': title, 'description': description}
            response = requests.post(IFILO_UPLOAD_URL, files=files, data=data)
            return response.ok
    except Exception as e:
        print(f"Error uploading video to Ifilo: {e}")
        return False

def delete_file_after_delay(file_path, delay):
    """حذف فایل بعد از یک تاخیر مشخص."""
    time.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == USERNAME and password == PASSWORD:
            session['logged_in'] = True
            flash('ورود با موفقیت انجام شد!')
            return redirect(url_for('upload'))
        else:
            flash('نام کاربری یا رمز عبور نادرست است.')
    return render_template('login.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        video_source = request.form['video_source']
        video_url = request.form['video_url']
        title = request.form['video_title']
 description = request.form['video_description']
        
        if video_source == 'youtube':
            video_path = download_youtube_video(video_url)
        elif video_source == 'telegram':
            video_path = download_telegram_file(video_url)
        else:
            flash('منبع ویدیو نامعتبر است.')
            return redirect(url_for('upload'))

        if video_path:
            if upload_video_to_aparat(video_path, title, description):
                flash('ویدیو با موفقیت آپلود شد به آپارات!')
            if upload_video_to_ifilo(video_path, title, description):
                flash('ویدیو با موفقیت آپلود شد به ایفویلو!')
            
            # حذف فایل بعد از 5 ساعت
            threading.Thread(target=delete_file_after_delay, args=(video_path, 18000)).start()
            
            return redirect(url_for('upload'))
        else:
            flash('دانلود ویدیو ناموفق بود.')

    return render_template('upload.html')

@app.route('/files')
def files():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    files = os.listdir(DOWNLOAD_DIR)
    return render_template('files.html', files=files)

@app.route('/delete_file/<file_name>')
def delete_file(file_name):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('فایل حذف شد.')
    else:
        flash('فایل یافت نشد.')
    return redirect(url_for('files'))

@app.route('/api/upload', methods=['POST'])
def api_upload():
    video_source = request.form['video_source']
    video_url = request.form['video_url']
    title = request.form['video_title']
    description = request.form['video_description']
    
    if video_source == 'youtube':
        video_path = download_youtube_video(video_url)
    elif video_source == 'telegram':
        video_path = download_telegram_file(video_url)
    else:
        return jsonify({'error': 'Invalid video source'}), 400

    if video_path:
        if upload_video_to_aparat(video_path, title, description):
            return jsonify({'message': 'Video uploaded to Aparat successfully'}), 201
        if upload_video_to_ifilo(video_path, title, description):
            return jsonify({'message': 'Video uploaded to Ifilo successfully'}), 201
        else:
            return jsonify({'error': 'Failed to upload video'}), 500
    else:
        return jsonify({'error': 'Failed to download video'}), 500

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('خروج با موفقیت انجام شد.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
