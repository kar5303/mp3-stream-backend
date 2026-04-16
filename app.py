import os
import re
import subprocess
import tempfile
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)

# 允許你的 GitHub Pages 網域跨域請求
# 把下面換成你的 GitHub Pages 網址，例如 https://yourname.github.io
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*")
CORS(app, origins=ALLOWED_ORIGINS)


def is_valid_youtube_url(url: str) -> bool:
    """只允許合法的 YouTube 網址，防止任意命令注入"""
    pattern = r'^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}'
    return bool(re.match(pattern, url))


@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "MP3 Stream API is running."})


@app.route("/stream", methods=["GET"])
def stream_mp3():
    """
    GET /stream?url=https://www.youtube.com/watch?v=VIDEO_ID
    以串流方式回傳 MP3 音訊，前端可直接用 <audio src="..."> 播放。
    """
    url = request.args.get("url", "").strip()

    if not url:
        return jsonify({"error": "缺少 url 參數"}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "無效的 YouTube 網址"}), 400

    def generate():
        """用 yt-dlp pipe 模式串流輸出音訊，不落地存檔"""
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",      # 0=最佳, 9=最差；5 是平衡點
            "--output", "-",             # 輸出到 stdout
            "--quiet",
            url,
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        try:
            while True:
                chunk = process.stdout.read(8192)  # 每次讀 8KB
                if not chunk:
                    break
                yield chunk
        finally:
            process.stdout.close()
            process.wait()

    return Response(
        generate(),
        mimetype="audio/mpeg",
        headers={
            "Content-Disposition": "inline",   # 讓瀏覽器直接播放而非下載
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.route("/info", methods=["GET"])
def get_info():
    """
    GET /info?url=...
    回傳影片標題（供前端顯示用，可選）
    """
    url = request.args.get("url", "").strip()
    if not url or not is_valid_youtube_url(url):
        return jsonify({"error": "無效網址"}), 400

    result = subprocess.run(
        ["yt-dlp", "--no-playlist", "--print", "title", "--quiet", url],
        capture_output=True, text=True, timeout=15
    )
    title = result.stdout.strip() or "未知標題"
    return jsonify({"title": title})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
