import logging
import os
import secrets
import sqlite3
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stock.db"

# ==========================
# ログ設定
# ==========================
logging.basicConfig(
    filename=BASE_DIR / "operation.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def write_log(action, item_name="", item_id="", ip="", user_agent=""):
    logging.info(
        f"{action} id={item_id} name={item_name} ip={ip} ua={user_agent}"
    )

def get_client_ip():
    return request.headers.get(
        "CF-Connecting-IP",
        request.remote_addr
    )


def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def verify_csrf_token():
    submitted = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    if submitted != expected:
        abort(400)

# ==========================
# DB接続
# ==========================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stock INTEGER NOT NULL,
            minimum INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


# ==========================
# 一覧表示
# ==========================
@app.route("/")
def index():
    csrf_token = generate_csrf_token()
    conn = get_db()

    items = conn.execute(
        """
        SELECT * FROM items
        ORDER BY
        CASE
            WHEN stock <= minimum THEN 0
            ELSE 1
        END,
        name
        """
    ).fetchall()

    shortage_count = conn.execute(
        """
        SELECT COUNT(*) FROM items
        WHERE stock <= minimum
        """
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        items=items,
        shortage_count=shortage_count,
        csrf_token=csrf_token,
    )


# ==========================
# 追加
# ==========================
@app.route("/add", methods=["POST"])
def add():
    verify_csrf_token()
    name = request.form["name"]
    stock = request.form["stock"]
    minimum = request.form["minimum"]

    conn = get_db()

    cur = conn.execute(
        "INSERT INTO items (name, stock, minimum) VALUES (?, ?, ?)",
        (name, stock, minimum),
    )

    conn.commit()

    write_log(
        action="ADD",
        item_name=name,
        item_id=cur.lastrowid,
        ip=get_client_ip(),
        user_agent=request.headers.get("User-Agent"),
    )

    conn.close()

    return redirect("/")


# ==========================
# 使用
# ==========================
@app.route("/use/<int:id>", methods=["POST"])
def use(id):
    verify_csrf_token()
    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (id,),
    ).fetchone()

    conn.execute(
        "UPDATE items SET stock = stock - 1 WHERE id=? AND stock > 0",
        (id,),
    )

    conn.commit()

    if item:
        write_log(
            action="USE",
            item_name=item["name"],
            item_id=id,
            ip=get_client_ip(),
            user_agent=request.headers.get("User-Agent"),
        )

    conn.close()

    return redirect("/")


# ==========================
# 購入
# ==========================
@app.route("/buy/<int:id>", methods=["POST"])
def buy(id):
    verify_csrf_token()
    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (id,),
    ).fetchone()

    conn.execute(
        "UPDATE items SET stock = stock + 1 WHERE id=?",
        (id,),
    )

    conn.commit()

    if item:
        write_log(
            action="BUY",
            item_name=item["name"],
            item_id=id,
            ip=get_client_ip(),
            user_agent=request.headers.get("User-Agent"),
        )

    conn.close()

    return redirect("/")


# ==========================
# 削除
# ==========================
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    verify_csrf_token()
    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (id,),
    ).fetchone()

    conn.execute(
        "DELETE FROM items WHERE id=?",
        (id,),
    )

    conn.commit()

    if item:
        write_log(
            action="DELETE",
            item_name=item["name"],
            item_id=id,
            ip=get_client_ip(),
            user_agent=request.headers.get("User-Agent"),
        )

    conn.close()

    return redirect("/")


# ==========================
# 編集画面
# ==========================
@app.route("/edit/<int:id>")
def edit(id):
    csrf_token = generate_csrf_token()
    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (id,),
    ).fetchone()

    conn.close()

    return render_template("edit.html", item=item, csrf_token=csrf_token)


# ==========================
# 最低在庫更新
# ==========================
@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    verify_csrf_token()
    minimum = request.form["minimum"]

    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (id,),
    ).fetchone()

    conn.execute(
        "UPDATE items SET minimum=? WHERE id=?",
        (minimum, id),
    )

    conn.commit()

    if item:
        write_log(
            action=f"UPDATE minimum={minimum}",
            item_name=item["name"],
            item_id=id,
            ip=get_client_ip(),
            user_agent=request.headers.get("User-Agent"),
        )

    conn.close()

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)