import os
import re
import subprocess
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

# ── CORS：手動在每個回應加上標頭，確保瀏覽器不擋跨域請求 ──
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

@app.route("/", methods=["GET", "OPTIONS"])
def index():
    return jsonify({"status": "ok", "message": "MP3 Stream API is running."})


def is_valid_youtube_url(url: str) -> bool:
    pattern = r'^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[\w\-]{11}'
    return bool(re.match(pattern, url))


@app.route("/stream", methods=["GET", "OPTIONS"])
def stream_mp3():
    # OPTIONS preflight 直接回 200
    if request.method == "OPTIONS":
        return Response(status=200)

    url = request.args.get("url", "").strip()

    if not url:
        return jsonify({"error": "缺少 url 參數"}), 400
    if not is_valid_youtube_url(url):
        return jsonify({"error": "無效的 YouTube 網址"}), 400

    def generate():
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--format", "bestaudio",          # 先抓最佳音訊格式
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "5",
            "--no-warnings",
            "--output", "-",                  # 輸出到 stdout
            url,
        ]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,           # 收集 stderr 方便除錯
        )
        try:
            while True:
                chunk = process.stdout.read(8192)
                if not chunk:
                    break
                yield chunk
        finally:
            process.stdout.close()
            process.wait()

    resp = Response(
        generate(),
        mimetype="audio/mpeg",
    )
    resp.headers["Content-Disposition"] = "inline"
    resp.headers["Cache-Control"]       = "no-cache"
    resp.headers["X-Accel-Buffering"]   = "no"   # 關閉 nginx 緩衝，讓串流即時送出
    return resp


@app.route("/info", methods=["GET"])
def get_info():
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
