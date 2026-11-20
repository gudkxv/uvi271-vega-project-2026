# Проверки справочника. Запуск из корня проекта: python3 tests/check.py

import csv
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))

import app as site
import db
import search

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import baseline
import metrics


def check(condition, message):
    if not condition:
        raise SystemExit("Не прошла проверка: " + message)


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_card(card_id, question_id, answer, status, keywords, clause):
    return {
        "card_id": card_id,
        "question_id": question_id,
        "document_title": "Тестовый документ",
        "act_number": "тест",
        "edition": "не сверена",
        "source_url": "https://example.com/doc",
        "clause_ref": clause,
        "answer_text": answer,
        "applicability": "СЕКРЕТ_УСЛОВИЕ",
        "keywords": keywords,
        "status": status,
        "checked_at": "",
        "checked_by": "",
    }


def make_question(question_id, category, question):
    return {
        "question_id": question_id,
        "category": category,
        "question": question,
    }


def build_client(folder, cards, questions):
    cards_path = os.path.join(folder, "cards.csv")
    questions_path = os.path.join(folder, "questions.csv")
    db_path = os.path.join(folder, "helper.sqlite")
    write_csv(cards_path, db.CARD_FIELDS, cards)
    write_csv(questions_path, ["question_id", "category", "question"], questions)
    application = site.create_app(cards_path, questions_path, db_path)
    return application.test_client(), cards_path


def check_baseline():
    log_path = os.path.join(ROOT, "src", "Данные_нормативка", "requests_log.csv")
    questions_path = os.path.join(ROOT, "src", "Данные_нормативка", "questions.csv")
    summary = baseline.summarize(log_path, questions_path)
    check(summary["requests"] == 14000, "всего обращений")
    check(summary["minutes"] == 994054, "всего минут")
    check(summary["top_requests"] == 7032, "обращения топ-10")
    check(summary["top_minutes"] == 505516, "минуты топ-10")
    check(summary["top_lawyer"] == 1634, "обращения топ-10 с юристом")

    ids = []
    for item in summary["top"]:
        ids.append(item["question_id"])
    check(
        ids == ["Q057", "Q011", "Q039", "Q041", "Q036", "Q012", "Q025", "Q028", "Q003", "Q017"],
        "порядок десяти вопросов",
    )

    cards = db.read_csv(os.path.join(ROOT, "data", "cards.csv"))
    card_ids = []
    for card in cards:
        card_ids.append(card["question_id"])
        check(card["status"] == "черновик", "статус " + card["card_id"] + " должен быть черновик")
    check(card_ids == ids, "карточки идут в том же порядке, что и топ-10")
    print("Точка отсчёта совпала с запиской, карточки — черновики.")


def check_search():
    cards = [
        {
            "rank": 1,
            "question": "С какого момента приём груза",
            "category": "Сроки",
            "keywords": "штемпель",
            "answer_text": "этот текст не ищем",
        },
        {
            "rank": 2,
            "question": "С какого момента прием вагона",
            "category": "Сроки",
            "keywords": "",
            "answer_text": "аварийная карточка только в ответе",
        },
        {
            "rank": 3,
            "question": "Штраф за накладную",
            "category": "Штрафы",
            "keywords": "общийтермин",
            "answer_text": "",
        },
    ]
    cards[0]["keywords"] = "штемпель общийтермин"

    both = search.find_cards(cards, "общийтермин")
    check(len(both) == 2, "одинаковый счёт показывает обе карточки")
    check(both[0]["rank"] == 1 and both[1]["rank"] == 3, "ничья сортируется по порядку тем")

    one = search.find_cards(cards, "штемпель")
    check(len(one) == 1, "лучший счёт оставляет одну карточку")
    check(one[0]["score"] == 1, "счёт равен числу найденных слов")

    yo = search.find_cards(cards, "прием груза")
    check(len(yo) == 1 and yo[0]["rank"] == 1, "буква ё не мешает поиску")

    check(len(search.find_cards(cards, "и в на")) == 0, "короткие слова не ищутся")
    check(len(search.find_cards(cards, "аварийная")) == 0, "текст ответа в поиск не входит")
    print("Поиск работает.")


def check_pages():
    folder = tempfile.mkdtemp()
    cards = [
        make_card("c-ok", "Q1", "ГОТОВЫЙ_ОТВЕТ", "проверено", "доставка штемпель", "статья 33"),
        make_card("c-draft", "Q2", "СКРЫТЫЙ_ОТВЕТ", "черновик", "черновикслово", "пункт 9"),
        make_card("c-old", "Q3", "СТАРЫЙ_ОТВЕТ", "устарело", "устарелослово", "пункт 8"),
    ]
    questions = [
        make_question("Q1", "Сроки", "Когда начинается доставка груза"),
        make_question("Q2", "Акты", "Что такое скрытый черновик темы"),
        make_question("Q3", "Акты", "Старая норма про вагон"),
    ]
    client, cards_path = build_client(folder, cards, questions)

    home = client.get("/").get_data(as_text=True)
    check("Когда начинается доставка груза" in home, "проверенная тема видна на главной")
    check("СКРЫТЫЙ_ОТВЕТ" not in home, "черновик не виден на главной")
    check("Что такое скрытый черновик темы" not in home, "вопрос черновика не виден на главной")

    found = client.get("/?q=доставка").get_data(as_text=True)
    check("ГОТОВЫЙ_ОТВЕТ" not in found, "в списке поиска нет текста ответа")
    check("Когда начинается доставка груза" in found, "поиск находит проверенную карточку")
    check("Совпало слов" in found, "поиск показывает счёт")

    missed = client.get("/?q=подводная+лодка").get_data(as_text=True)
    check("Подходящей проверенной карточки нет" in missed, "пустой поиск говорит, что карточки нет")
    check("ГОТОВЫЙ_ОТВЕТ" not in missed, "пустой поиск не подставляет ответ")

    hidden = client.get("/card/c-draft").get_data(as_text=True)
    check("СКРЫТЫЙ_ОТВЕТ" not in hidden, "страница черновика не показывает ответ")
    check("Карточка не подтверждена" in hidden, "черновик объясняет, что ответа нет")

    old = client.get("/card/c-old").get_data(as_text=True)
    check("СТАРЫЙ_ОТВЕТ" not in old, "устаревшая карточка не показывает ответ")
    check("Карточка устарела" in old, "устаревшая карточка это говорит")

    ready = client.get("/card/c-ok").get_data(as_text=True)
    check("ГОТОВЫЙ_ОТВЕТ" in ready, "проверенная карточка показывает ответ")
    check("статья 33" in ready, "проверенная карточка показывает пункт")

    edit = client.get("/edit/c-draft").get_data(as_text=True)
    check("СКРЫТЫЙ_ОТВЕТ" in edit, "правка показывает черновик")
    check("только для этого компьютера" in edit, "правка предупреждает, что пароля нет")

    g0 = client.get("/g0").get_data(as_text=True)
    check("ГОТОВЫЙ_ОТВЕТ" not in g0, "Г0 не показывает ответ")
    check("СЕКРЕТ_УСЛОВИЕ" not in g0, "Г0 не показывает условия")
    check("статья 33" in g0, "Г0 показывает пункт")
    check("Тестовый документ" in g0, "Г0 показывает документ")

    missing = client.get("/card/нет-такой")
    check(missing.status_code == 404, "неизвестная карточка — это 404")

    bad = client.post(
        "/edit/c-draft",
        data={
            "answer_text": "СКРЫТЫЙ_ОТВЕТ",
            "applicability": "СЕКРЕТ_УСЛОВИЕ",
            "keywords": "черновикслово",
            "status": "готово",
            "checked_by": "",
        },
    )
    check(bad.status_code == 400, "чужой статус не сохраняется")

    saved = client.post(
        "/edit/c-draft",
        data={
            "answer_text": "СКРЫТЫЙ_ОТВЕТ стал ответом",
            "applicability": "СЕКРЕТ_УСЛОВИЕ",
            "keywords": "черновикслово",
            "status": "проверено",
            "checked_by": "Иванов",
        },
        follow_redirects=True,
    )
    saved_text = saved.get_data(as_text=True)
    check("Сохранено" in saved_text, "сохранение подтверждается")
    home_after = client.get("/").get_data(as_text=True)
    check("Что такое скрытый черновик темы" in home_after, "после проверки тема видна сотруднику")
    card_after = client.get("/card/c-draft").get_data(as_text=True)
    check("СКРЫТЫЙ_ОТВЕТ стал ответом" in card_after, "после проверки ответ открыт")
    check("Иванов" in card_after, "на карточке есть, кто проверил")

    rows = db.read_csv(cards_path)
    for row in rows:
        if row["card_id"] == "c-draft":
            row["clause_ref"] = "ПУНКТ-ПРОВЕРКА-99"
    write_csv(cards_path, db.CARD_FIELDS, rows)
    client.post("/edit/reload")
    g0_after = client.get("/g0").get_data(as_text=True)
    check("ПУНКТ-ПРОВЕРКА-99" in g0_after, "перечитать CSV подхватывает пункт")

    shutil.rmtree(folder)
    print("Страницы скрывают черновик, Г0 без ответа, правка меняет статус.")


def check_real_site():
    folder = tempfile.mkdtemp()
    cards_path = os.path.join(folder, "cards.csv")
    shutil.copy(os.path.join(ROOT, "data", "cards.csv"), cards_path)
    questions_path = os.path.join(ROOT, "src", "Данные_нормативка", "questions.csv")
    db_path = os.path.join(folder, "helper.sqlite")
    application = site.create_app(cards_path, questions_path, db_path)
    client = application.test_client()

    home = client.get("/").get_data(as_text=True)
    check("Проверенных карточек пока нет" in home, "на старте сотруднику нечего открыть")

    missed = client.get("/?q=переадресовка").get_data(as_text=True)
    check("Подходящей проверенной карточки нет" in missed, "черновик не находится поиском")
    check("не сверен с официальной публикацией" not in missed, "поиск не показывает текст черновика")

    g0 = client.get("/g0").get_data(as_text=True)
    check("пункт 26" in g0, "Г0 показывает пункт по переадресовке")
    check("не сверен с официальной публикацией" not in g0, "Г0 не показывает готовый ответ")
    check("Каталог Г0" in g0, "страница Г0 подписана")

    edit = client.get("/edit/C057").get_data(as_text=True)
    check("не сверен с официальной публикацией" in edit, "правка открывает черновик Q057")

    shutil.rmtree(folder)
    print("Настоящие карточки: черновики скрыты, Г0 показывает только ссылку.")


def check_metrics():
    code, lines = metrics.check_file(os.path.join(ROOT, "data", "protocol.csv"))
    text = "\n".join(lines)
    check(code == 0, "пустой протокол не считается ошибкой")
    check("Протокол пустой" in text, "пустой протокол об этом пишет")

    folder = tempfile.mkdtemp()
    path = os.path.join(folder, "protocol.csv")
    rows = [
        {
            "номер": "1",
            "вариант": "G0",
            "секунды": "100",
            "карточка": "",
            "ответ": "а",
            "пункт": "а",
            "верно": "да",
            "причина": "",
        },
        {
            "номер": "2",
            "вариант": "Г0",
            "секунды": "200",
            "карточка": "",
            "ответ": "б",
            "пункт": "б",
            "верно": "нет",
            "причина": "",
        },
        {
            "номер": "1",
            "вариант": "Г1",
            "секунды": "40",
            "карточка": "C003",
            "ответ": "в",
            "пункт": "в",
            "верно": "да",
            "причина": "",
        },
        {
            "номер": "2",
            "вариант": "Г1",
            "секунды": "80",
            "карточка": "C003",
            "ответ": "г",
            "пункт": "г",
            "верно": "нет",
            "причина": "неверный пункт",
        },
    ]
    write_csv(path, metrics.COLUMNS, rows)
    code, lines = metrics.check_file(path)
    text = "\n".join(lines)
    check(code == 0, "заполненный протокол читается")
    check("Г0: верных 1 из 2. Неверных пунктов: 0." in text, "счёт Г0")
    check("Г1: верных 1 из 2. Неверных пунктов: 1." in text, "счёт Г1 и плохого пункта")
    check("Среднее время успешного ответа: 100.0 с." in text, "среднее Г0")
    check("Среднее время успешного ответа: 40.0 с." in text, "среднее Г1")
    check("Г1 быстрее Г0 на 60.0%" in text, "сравнение времени")
    shutil.rmtree(folder)
    print("Метрики считаются, пустой протокол не ломает запуск.")


def main():
    check_baseline()
    check_search()
    check_pages()
    check_real_site()
    check_metrics()
    print("Все проверки прошли.")


if __name__ == "__main__":
    main()
