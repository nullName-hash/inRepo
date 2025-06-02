from flask import Flask, request, jsonify, send_from_directory
import yt_dlp
import os

app = Flask(__name__)

download_status = {}  # ذخیره وضعیت دانلود

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/formats', methods=['POST'])
def formats():
    data = request.get_json()
    url = data.get('url')
    if not url:
        return jsonify({'error': 'لینک ویدیو وارد نشده'}), 400

    ydl_opts = {'quiet': False, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])
        filtered_formats = []

        for f in formats:
            acodec = f.get('acodec')
            vcodec = f.get('vcodec')
            ext = f.get('ext', '')
            resolution = f.get('resolution') or f.get('height')
            filesize = f.get('filesize') or f.get('filesize_approx')

            if not vcodec or vcodec == 'none':
                continue  # حذف فرمت‌های بدون تصویر

            is_combined = (
                ext == 'mp4' and
                acodec != 'none' and
                vcodec != 'none' and
                not f.get('format_note', '').lower().startswith('dash')
            )

            is_audio_or_video = (
                acodec != 'none' or 
                (resolution and str(resolution).isdigit() and int(resolution) > 360)
            )

            if is_combined or is_audio_or_video:
                filtered_formats.append({
                    'format_id': f.get('format_id'),
                    'ext': ext,
                    'filesize': filesize,
                    'resolution': resolution,
                    'fps': f.get('fps'),
                    'vcodec': vcodec,
                    'acodec': acodec,
                    'note': f.get('format_note', ''),
                    'combined': is_combined
                })

        return jsonify({
            'formats': filtered_formats,
            'title': info.get('title', '')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download', methods=['POST'])
def download():
    data = request.get_json()
    url = data.get('url')
    format_id = data.get('format_id')
    if not url or not format_id:
        return jsonify({'error': 'لینک یا فرمت انتخاب نشده'}), 400

    def progress_hook(d):
        if d['status'] == 'downloading':
            download_status['progress'] = {
                'percent': d.get('_percent_str', '').strip(),
                'speed': d.get('_speed_str', '').strip(),
                'eta': d.get('_eta_str', '').strip()
            }
        elif d['status'] == 'finished':
            download_status['progress'] = {'finished': True}

    try:
        output_template = '/sdcard/Download/DownTube/downloaded_video.%(ext)s'
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_template,
            'quiet': True,
            'noplaylist': True,
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return jsonify({'message': 'دانلود کامل شد: ' + output_template.replace('%(ext)s', 'mp4')})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/progress')
def progress():
    return jsonify(download_status.get('progress', {}))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)