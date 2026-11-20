# CSV — файл, который правит команда.
# При запуске он копируется в локальную базу.
# Кнопка «Сохранить» записывает правку и в базу, и обратно в CSV.

import csv
import os
import sqlite3
from datetime import date

CARD_FIELDS = [
    "card_id",
    "question_id",
    "document_title",
    "act_number",
    "edition",
    "source_url",
    "clause_ref",
    "answer_text",
    "applicability",
    "keywords",
    "status",
    "checked_at",
    "checked_by",
]

STATUSES = ["черновик", "проверено", "устарело"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def cell(row, name):
    value = row.get(name, "")
    if value is None:
        return ""
    return value.strip()


def connect(db_path):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db(db_path, cards_path, questions_path):
    folder = os.path.dirname(db_path)
    if folder != "":
        os.makedirs(folder, exist_ok=True)

    questions = {}
    for row in read_csv(questions_path):
        questions[row["question_id"]] = row

    connection = connect(db_path)
    connection.execute("DROP TABLE IF EXISTS cards")
    connection.execute(
        """
        CREATE TABLE cards (
            card_id TEXT PRIMARY KEY,
            question_id TEXT,
            rank INTEGER,
            category TEXT,
            question TEXT,
            document_title TEXT,
            act_number TEXT,
            edition TEXT,
            source_url TEXT,
            clause_ref TEXT,
            answer_text TEXT,
            applicability TEXT,
            keywords TEXT,
            status TEXT,
            checked_at TEXT,
            checked_by TEXT
        )
        """
    )

    rank = 1
    for row in read_csv(cards_path):
        question = questions.get(row["question_id"], {})
        connection.execute(
            """
            INSERT INTO cards (
                card_id, question_id, rank, category, question,
                document_title, act_number, edition, source_url, clause_ref,
                answer_text, applicability, keywords, status, checked_at, checked_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cell(row, "card_id"),
                cell(row, "question_id"),
                rank,
                cell(question, "category"),
                cell(question, "question"),
                cell(row, "document_title"),
                cell(row, "act_number"),
                cell(row, "edition"),
                cell(row, "source_url"),
                cell(row, "clause_ref"),
                cell(row, "answer_text"),
                cell(row, "applicability"),
                cell(row, "keywords"),
                cell(row, "status"),
                cell(row, "checked_at"),
                cell(row, "checked_by"),
            ),
        )
        rank = rank + 1

    connection.commit()
    connection.close()


def rows_to_dicts(rows):
    cards = []
    for row in rows:
        cards.append(dict(row))
    return cards


def get_cards(db_path, verified_only=False):
    connection = connect(db_path)
    if verified_only:
        rows = connection.execute(
            "SELECT * FROM cards WHERE status = ? ORDER BY rank",
            ("проверено",),
        ).fetchall()
    else:
        rows = connection.execute("SELECT * FROM cards ORDER BY rank").fetchall()
    connection.close()
    return rows_to_dicts(rows)


def get_card(db_path, card_id):
    connection = connect(db_path)
    row = connection.execute(
        "SELECT * FROM cards WHERE card_id = ?",
        (card_id,),
    ).fetchone()
    connection.close()
    if row is None:
        return None
    return dict(row)


def write_cards_csv(cards_path, cards):
    with open(cards_path, "w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CARD_FIELDS)
        writer.writeheader()
        for card in cards:
            writer.writerow(
                {
                    "card_id": card["card_id"],
                    "question_id": card["question_id"],
                    "document_title": card["document_title"],
                    "act_number": card["act_number"],
                    "edition": card["edition"],
                    "source_url": card["source_url"],
                    "clause_ref": card["clause_ref"],
                    "answer_text": card["answer_text"],
                    "applicability": card["applicability"],
                    "keywords": card["keywords"],
                    "status": card["status"],
                    "checked_at": card["checked_at"],
                    "checked_by": card["checked_by"],
                }
            )


def update_card(db_path, cards_path, card_id, answer_text, applicability, keywords, status, checked_by):
    if status not in STATUSES:
        return False

    connection = connect(db_path)
    row = connection.execute(
        "SELECT * FROM cards WHERE card_id = ?",
        (card_id,),
    ).fetchone()
    if row is None:
        connection.close()
        return False

    if status == "проверено":
        if row["status"] != "проверено" or row["checked_at"] == "":
            checked_at = date.today().strftime("%d.%m.%Y")
        else:
            checked_at = row["checked_at"]
    else:
        checked_at = ""

    connection.execute(
        """
        UPDATE cards
        SET answer_text = ?, applicability = ?, keywords = ?, status = ?,
            checked_at = ?, checked_by = ?
        WHERE card_id = ?
        """,
        (answer_text, applicability, keywords, status, checked_at, checked_by, card_id),
    )
    connection.commit()
    saved = connection.execute("SELECT * FROM cards ORDER BY rank").fetchall()
    connection.close()
    write_cards_csv(cards_path, saved)
    return True
