# Считает точку отсчёта по журналу обращений.
# В справочник эти строки не попадают: здесь только суммы по вопросам.

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_PATH = os.path.join(ROOT, "src", "Данные_нормативка", "requests_log.csv")
QUESTIONS_PATH = os.path.join(ROOT, "src", "Данные_нормативка", "questions.csv")


def read_rows(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def whole_number(value):
    number = float(value)
    if number == int(number):
        return int(number)
    return number


def summarize(log_path, questions_path):
    questions = {}
    for row in read_rows(questions_path):
        questions[row["question_id"]] = row["question"]

    totals = {}
    total_minutes = 0
    request_count = 0

    for row in read_rows(log_path):
        question_id = row["question_id"]
        minutes = whole_number(row["minutes_spent"])
        total_minutes = total_minutes + minutes
        request_count = request_count + 1

        if question_id not in totals:
            totals[question_id] = {
                "question_id": question_id,
                "question": questions.get(question_id, ""),
                "minutes": 0,
                "count": 0,
                "lawyer": 0,
            }

        totals[question_id]["minutes"] = totals[question_id]["minutes"] + minutes
        totals[question_id]["count"] = totals[question_id]["count"] + 1
        if row["escalated_to_lawyer"].strip().lower() == "true":
            totals[question_id]["lawyer"] = totals[question_id]["lawyer"] + 1

    def minutes_of(item):
        return item["minutes"]

    ranked = list(totals.values())
    ranked.sort(key=minutes_of, reverse=True)
    top = ranked[:10]

    top_minutes = 0
    top_requests = 0
    top_lawyer = 0
    for item in top:
        top_minutes = top_minutes + item["minutes"]
        top_requests = top_requests + item["count"]
        top_lawyer = top_lawyer + item["lawyer"]

    return {
        "requests": request_count,
        "minutes": total_minutes,
        "top": top,
        "top_requests": top_requests,
        "top_minutes": top_minutes,
        "top_lawyer": top_lawyer,
    }


def print_summary(summary):
    total_hours = summary["minutes"] / 60
    top_hours = summary["top_minutes"] / 60
    share = summary["top_minutes"] / summary["minutes"] * 100
    without_lawyer = summary["top_requests"] - summary["top_lawyer"]

    print("Точка отсчёта по журналу за 2025 год")
    print(f"Обращений: {summary['requests']}")
    print(f"Минут поиска: {summary['minutes']}")
    print(f"Часов поиска: {total_hours:.2f}")
    print("")
    print("Десять вопросов с наибольшим временем:")

    place = 1
    for item in summary["top"]:
        print(
            f"{place}. {item['question_id']} — "
            f"{item['count']} обращений, {item['minutes']} мин, "
            f"к юристу {item['lawyer']}. {item['question']}"
        )
        place = place + 1

    print("")
    print(
        f"Вместе топ-10: {summary['top_requests']} обращений, "
        f"{summary['top_minutes']} мин ({top_hours:.2f} ч, {share:.2f}% всего времени)."
    )
    print(f"С юристом: {summary['top_lawyer']}. Без юриста: {without_lawyer}.")


def main():
    summary = summarize(LOG_PATH, QUESTIONS_PATH)
    print_summary(summary)


if __name__ == "__main__":
    main()
