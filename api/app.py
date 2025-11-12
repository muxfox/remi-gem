import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

CREDIT_TEXT = "Credit - Shubham Gote · Code assistance - ChatGPT"
IMGBB_API_KEY = '389a5d8e41bbfb2224b702bf63d46d33'

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

@app.get('/')
def serve_index():
    return send_from_directory(ROOT_DIR, 'index.html')

@app.get('/index.html')
def serve_index_html():
    return send_from_directory(ROOT_DIR, 'index.html')

def upload_to_imgbb(file_storage):
    if not IMGBB_API_KEY:
        raise RuntimeError("IMGBB_API_KEY not set.")
    files = {'image': (file_storage.filename, file_storage.stream, file_storage.mimetype)}
    url = f"https://api.imgbb.com/1/upload?key={IMGBB_API_KEY}"
    r = requests.post(url, files=files, timeout=60)
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        raise RuntimeError(f"imgbb upload failed: {data}")
    return data["data"]["url"]

def call_remini_api(image_url):
    api_base = "https://myrestapi-xi.vercel.app/imagecreator/remini"
    resp = requests.get(api_base, params={"url": image_url}, timeout=120)
    resp.raise_for_status()
    return resp.json()

@app.post("/process")
def process_image():
    try:
        if 'image' not in request.files:
            return jsonify({"ok": False, "error": "No image uploaded"}), 400

        image = request.files['image']
        if image.filename == '':
            return jsonify({"ok": False, "error": "Empty filename"}), 400

        hosted_url = upload_to_imgbb(image)
        api_result = call_remini_api(hosted_url)

        if api_result.get("status") and "result" in api_result:
            return jsonify({
                "ok": True,
                "credit": CREDIT_TEXT,
                "source_url": hosted_url,
                "result_url": api_result["result"]
            })
        else:
            return jsonify({
                "ok": False,
                "error": "API did not return result URL",
                "raw": api_result,
                "debug": {"source_url": hosted_url}
            }), 502
    except Exception as e:
        import traceback
        return jsonify({
            "ok": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }), 500

handler = app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
