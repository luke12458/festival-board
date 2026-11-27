import os
import re
import time
from io import BytesIO
from uuid import uuid4

from flask import Flask, abort, redirect, render_template, request, send_file, session, url_for
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from markupsafe import escape
from storage import open_store, root

app = Flask(__name__)
secret = os.getenv("SECRET_KEY")
if not secret:
    if os.getenv("WEBSITE_SITE_NAME") or os.getenv("STORAGE_ACCOUNT"):
        raise RuntimeError("Set SECRET_KEY before starting Azure mode")
    root.mkdir(exist_ok=True)
    keyfile = root / "session.key"
    if not keyfile.exists():
        keyfile.write_bytes(os.urandom(32))
    secret = keyfile.read_bytes()
app.config.update(SECRET_KEY=secret, MAX_CONTENT_LENGTH=4*1024*1024,
                  SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_SECURE=bool(os.getenv("WEBSITE_SITE_NAME")))
store = open_store()


@app.before_request
def identify():
    if "voter" not in session:
        session["voter"] = uuid4().hex
    if request.method == "POST" and request.headers.get("Sec-Fetch-Site") == "cross-site":
        abort(403)


@app.get("/")
def home():
    polls = sorted(store.rows("polls"), key=lambda p: p["created"], reverse=True)
    for poll in polls:
        votes = store.rows("v" + poll["RowKey"])
        poll["counts"] = [sum(v["choice"] == i for v in votes) for i in range(2)]
        poll["mine"] = next((v["choice"] for v in votes if v["RowKey"] == session["voter"]), None)
    return render_template("index.html", polls=polls)


def normalized_image(upload):
    raw = upload.read(3 * 1024 * 1024 + 1)
    if len(raw) > 3 * 1024 * 1024:
        abort(413, "画像は3 MB以内にしてください。")
    try:
        with Image.open(BytesIO(raw), formats=["JPEG", "PNG"]) as img:
            if img.width * img.height > 16_000_000:
                abort(400, "画像を1600万画素以内に縮小してください。")
            img.thumbnail((1400, 1400))
            out = BytesIO()
            clean = ImageOps.exif_transpose(img).convert("RGB")
            clean.info.clear()
            clean.save(out, "JPEG", quality=82)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        abort(400, "読み込めるJPEGまたはPNGを選んでください。")


@app.post("/polls")
def create():
    title, a, b = [request.form.get(k, "").strip() for k in ("topic","a","b")]
    if not (0 < len(title) <= 60 and 0 < len(a) <= 32 and 0 < len(b) <= 32 and a != b):
        abort(400, "議題と異なる二案を文字数制限内で入力してください。")
    pid = uuid4().hex
    upload = request.files.get("photo")
    name = ""
    if upload and upload.filename:
        name = pid + ".jpg"
        store.picture(name, normalized_image(upload))
    store.put("polls", pid, dict(title=title,a=a,b=b,image=name,created=time.time_ns()))
    return redirect(url_for("home"), code=303)


@app.post("/polls/<pid>/vote")
def vote(pid):
    if not re.fullmatch(r"[0-9a-f]{32}", pid) or not store.exists(pid):
        abort(404)
    choice = request.form.get("choice")
    if choice not in ("0","1"):
        abort(400)
    store.put("v" + pid, session["voter"], {"choice":int(choice)})
    return redirect(url_for("home"), code=303)


@app.get("/images/<name>")
def image(name):
    if not re.fullmatch(r"[0-9a-f]{32}\.jpg", name):
        abort(404)
    data = store.picture(name)
    if data is None:
        abort(404)
    return send_file(BytesIO(data), mimetype="image/jpeg", max_age=86400)


@app.errorhandler(HTTPException)
def problem(error):
    return f'<meta charset="utf-8"><p>{escape(error.description)}</p><a href="/">掲示板へ戻る</a>', error.code
