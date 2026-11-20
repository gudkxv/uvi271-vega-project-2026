# Поиск без модели: считаем, сколько слов запроса нашлось
# в тексте вопроса, категории и ключевых словах.
# «срок» находится и внутри «сроки». Слова короче трёх букв пропускаем.


def normalize(text):
    return text.lower().replace("ё", "е")


def words_of(text):
    found = []
    current = ""
    for char in normalize(text):
        if char.isalpha() or char.isdigit():
            current = current + char
        else:
            if len(current) > 2:
                found.append(current)
            current = ""
    if len(current) > 2:
        found.append(current)
    return found


def score(query, card):
    query_words = words_of(query)
    if len(query_words) == 0:
        return 0

    haystack = normalize(card["question"] + " " + card["category"] + " " + card["keywords"])
    points = 0
    for word in query_words:
        if word in haystack:
            points = points + 1
    return points


def find_cards(cards, query):
    best = 0
    found = []
    for card in cards:
        points = score(query, card)
        if points > best:
            best = points
            copy = dict(card)
            copy["score"] = points
            found = [copy]
        elif points == best and points > 0:
            copy = dict(card)
            copy["score"] = points
            found.append(copy)

    def by_rank(item):
        return item["rank"]

    found.sort(key=by_rank)
    return found
