# Считает метрики Г0 и Г1 по заполненному протоколу.
# Пустой протокол — это нормально: эталон команда заполняет после заморозки карточек.

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = os.path.join(ROOT, "data", "protocol.csv")

COLUMNS = [
    "номер",
    "вариант",
    "секунды",
    "карточка",
    "ответ",
    "пункт",
    "верно",
    "причина",
]


def variant_of(value):
    text = value.strip().replace("G", "Г").replace("g", "Г").replace("г", "Г")
    if text in ("Г0", "Г1"):
        return text
    return ""


def is_yes(value):
    return value.strip().lower() in ("да", "yes", "true", "1")


def load_protocol(path):
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        missing = []
        for name in COLUMNS:
            if name not in fieldnames:
                missing.append(name)
        rows = list(reader)
    return missing, rows


def build_report(rows):
    groups = {
        "Г0": [],
        "Г1": [],
    }
    skipped = []
    problems = []
    # 2 — первая строка файла после заголовка.
    index = 2

    for row in rows:
        variant = variant_of(row["вариант"])
        if variant == "":
            skipped.append(index)
            index = index + 1
            continue

        item = {
            "yes": is_yes(row["верно"]),
            "bad_clause": row["причина"].strip().lower() == "неверный пункт",
            "seconds": None,
        }
        text = row["секунды"].strip()
        if text != "":
            try:
                item["seconds"] = float(text)
            except ValueError:
                problems.append(index)

        groups[variant].append(item)
        index = index + 1

    summary = {}
    for name in ("Г0", "Г1"):
        correct = 0
        bad_clause = 0
        success_seconds = []
        for item in groups[name]:
            if item["yes"]:
                correct = correct + 1
            if item["bad_clause"]:
                bad_clause = bad_clause + 1
            if item["yes"] and item["seconds"] is not None:
                success_seconds.append(item["seconds"])

        average = None
        if len(success_seconds) > 0:
            average = sum(success_seconds) / len(success_seconds)

        summary[name] = {
            "count": len(groups[name]),
            "correct": correct,
            "bad_clause": bad_clause,
            "average": average,
        }

    share = None
    g0_average = summary["Г0"]["average"]
    g1_average = summary["Г1"]["average"]
    if g0_average not in (None, 0) and g1_average is not None:
        share = (g0_average - g1_average) / g0_average

    return {
        "groups": summary,
        "faster_share": share,
        "skipped": skipped,
        "problems": problems,
    }


def report_lines(report):
    lines = []
    for name in ("Г0", "Г1"):
        group = report["groups"][name]
        if group["count"] == 0:
            lines.append(name + ": строк нет.")
            continue
        line = (
            name
            + ": верных "
            + str(group["correct"])
            + " из "
            + str(group["count"])
            + ". Неверных пунктов: "
            + str(group["bad_clause"])
            + "."
        )
        if group["average"] is None:
            line = line + " Среднее время успешного ответа посчитать нельзя."
        else:
            line = line + f" Среднее время успешного ответа: {group['average']:.1f} с."
        lines.append(line)

    share = report["faster_share"]
    if share is None:
        lines.append("Сравнить время Г0 и Г1 нельзя: нет успешных замеров у обоих.")
    elif share >= 0:
        lines.append(
            f"Г1 быстрее Г0 на {share * 100:.1f}%. В записке порог — не меньше 20%."
        )
    else:
        lines.append(f"Г1 медленнее Г0 на {abs(share) * 100:.1f}%.")

    if len(report["skipped"]) > 0:
        numbers = []
        for number in report["skipped"]:
            numbers.append(str(number))
        lines.append("Пропущены строки с непонятным вариантом: " + ", ".join(numbers))

    if len(report["problems"]) > 0:
        numbers = []
        for number in report["problems"]:
            numbers.append(str(number))
        lines.append("В этих строках секунды не число, время по ним не считал: " + ", ".join(numbers))

    return lines


def check_file(path):
    if not os.path.exists(path):
        return 1, ["Файла протокола нет: " + path]

    missing, rows = load_protocol(path)
    if len(missing) > 0:
        return 1, ["В протоколе нет столбцов: " + ", ".join(missing)]

    if len(rows) == 0:
        return 0, [
            "Протокол пустой. После испытания допишите строки в " + path,
            "Столбцы уже есть: " + ", ".join(COLUMNS),
        ]

    report = build_report(rows)
    return 0, report_lines(report)


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = DEFAULT_PATH
    code, lines = check_file(path)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
