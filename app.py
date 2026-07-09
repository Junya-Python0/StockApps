import sqlite3
from pathlib import Path

from flask import Flask, redirect, render_template, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "stock.db"


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

@app.route("/")
def index():
    conn = get_db()

    items = conn.execute("""
    SELECT * FROM items
    ORDER BY
    CASE
        WHEN stock <= minimum THEN 0
        ELSE 1
    END,
    name
    """).fetchall()

    shortage_count = conn.execute("""
    SELECT COUNT(*) FROM items
    WHERE stock <= minimum
    """).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        items=items,
        shortage_count=shortage_count
    )

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    stock = request.form["stock"]
    minimum = request.form["minimum"]

    conn = get_db()
    conn.execute(
        "INSERT INTO items (name, stock, minimum) VALUES (?, ?, ?)",
        (name, stock, minimum)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/use/<int:id>")
def use(id):
    conn = get_db()
    conn.execute(
        "UPDATE items SET stock = stock - 1 WHERE id=? AND stock > 0",
        (id,)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/buy/<int:id>")
def buy(id):
    conn = get_db()
    conn.execute(
        "UPDATE items SET stock = stock + 1 WHERE id=?",
        (id,)
    )
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    conn = get_db()
    conn.execute("DELETE FROM items WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/edit/<int:id>")
def edit(id):
    conn = get_db()
    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (id,)
    ).fetchone()
    conn.close()

    return render_template("edit.html", item=item)


@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    minimum = request.form["minimum"]

    conn = get_db()
    conn.execute(
        "UPDATE items SET minimum=? WHERE id=?",
        (minimum, id)
    )
    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)