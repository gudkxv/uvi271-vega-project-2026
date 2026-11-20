# Локальный справочник. Запуск: python3 app/app.py

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import db
import search
from flask import Flask, redirect, render_template, request, url_for


def create_app(cards_path, questions_path, db_path):
    application = Flask(__name__)
    application.config["CARDS_PATH"] = cards_path
    application.config["QUESTIONS_PATH"] = questions_path
    application.config["DB_PATH"] = db_path
    db.init_db(db_path, cards_path, questions_path)

    @application.get("/")
    def home():
        query = request.args.get("q", "").strip()
        verified = db.get_cards(application.config["DB_PATH"], verified_only=True)
        if query == "":
            found = verified
            mode = "list"
            if len(found) == 0:
                mode = "empty"
        else:
            found = search.find_cards(verified, query)
            if len(found) == 0:
                mode = "miss"
            else:
                mode = "found"
        return render_template("index.html", title="Поиск", query=query, cards=found, mode=mode)

    @application.get("/card/<card_id>")
    def card_page(card_id):
        card = db.get_card(application.config["DB_PATH"], card_id)
        if card is None:
            return render_template("missing.html", title="Нет карточки"), 404
        if card["status"] != "проверено":
            return render_template("hidden.html", title="Карточка не подтверждена", card=card)
        return render_template("card.html", title="Карточка", card=card)

    @application.get("/g0")
    def g0_page():
        cards = db.get_cards(application.config["DB_PATH"], verified_only=False)
        return render_template("g0.html", title="Каталог Г0", cards=cards)

    @application.get("/edit")
    def edit_list():
        cards = db.get_cards(application.config["DB_PATH"], verified_only=False)
        return render_template("edit_list.html", title="Правка карточек", cards=cards)

    @application.post("/edit/reload")
    def reload_cards():
        db.init_db(
            application.config["DB_PATH"],
            application.config["CARDS_PATH"],
            application.config["QUESTIONS_PATH"],
        )
        return redirect(url_for("edit_list"))

    @application.route("/edit/<card_id>", methods=["GET", "POST"])
    def edit_card(card_id):
        card = db.get_card(application.config["DB_PATH"], card_id)
        if card is None:
            return render_template("missing.html", title="Нет карточки"), 404

        error = ""
        status_code = 200
        if request.method == "POST":
            answer_text = request.form.get("answer_text", "")
            applicability = request.form.get("applicability", "")
            keywords = request.form.get("keywords", "")
            status = request.form.get("status", "").strip()
            checked_by = request.form.get("checked_by", "").strip()
            saved = db.update_card(
                application.config["DB_PATH"],
                application.config["CARDS_PATH"],
                card_id,
                answer_text,
                applicability,
                keywords,
                status,
                checked_by,
            )
            if not saved:
                error = "Такого статуса нет. Оставьте черновик, проверено или устарело."
                status_code = 400
                card["answer_text"] = answer_text
                card["applicability"] = applicability
                card["keywords"] = keywords
                card["status"] = status
                card["checked_by"] = checked_by
            else:
                return redirect(url_for("edit_card", card_id=card_id, saved=1))

        saved_flag = request.args.get("saved") == "1"
        return render_template(
            "edit_form.html",
            title="Правка карточки",
            card=card,
            statuses=db.STATUSES,
            error=error,
            saved=saved_flag,
        ), status_code

    return application


def default_paths():
    cards_path = os.path.join(ROOT, "data", "cards.csv")
    questions_path = os.path.join(ROOT, "src", "Данные_нормативка", "questions.csv")
    db_path = os.path.join(ROOT, "data", "helper.sqlite")
    return cards_path, questions_path, db_path


if __name__ == "__main__":
    cards_path, questions_path, db_path = default_paths()
    application = create_app(cards_path, questions_path, db_path)
    application.run(host="127.0.0.1", port=5000)
