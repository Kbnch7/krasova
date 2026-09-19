import argparse
import os
import random
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import psycopg

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://football:football@localhost:5436/football"
)

FIRST_NAMES = [
    "Артем", "Никита", "Роман", "Егор", "Илья", "Тимур", "Марк", "Данила",
    "Кирилл", "Глеб", "Матвей", "Иван", "Антон", "Павел", "Денис", "Сергей",
]
LAST_NAMES = [
    "Соколов", "Волков", "Гусев", "Панов", "Крылов", "Асланов", "Дементьев",
    "Орлов", "Зайцев", "Морозов", "Лебедев", "Беляев", "Ершов", "Гаврилов",
]
CITIES = [
    "Москва", "Санкт-Петербург", "Казань", "Краснодар", "Екатеринбург",
    "Ростов-на-Дону", "Самара", "Новосибирск", "Сочи", "Воронеж",
]
CLUB_A = [
    "Спартак", "Динамо", "Локомотив", "Торпедо", "Заря", "Восход", "Метеор",
    "Звезда", "Арсенал", "Факел", "Урал", "Балтика",
]
POSITIONS = ["GK", "DEF", "MID", "FWD"]
BASE_TOURNAMENTS = [
    ("РПЛ", "2025/2026"),
    ("Кубок России", "2025/2026"),
    ("Суперкубок России", "2025"),
    ("Лига чемпионов", "2025/2026"),
    ("Лига Европы", "2025/2026"),
    ("Первая лига", "2025/2026"),
]
EVENT_TYPES = ["GOAL", "ASSIST", "YELLOW_CARD", "RED_CARD", "SUBSTITUTION"]
EVENT_WEIGHTS = [25, 15, 20, 5, 35]


def log(message: str) -> None:
    print(f"[generate] {message}", flush=True)


def fetch_ids(conn, table: str) -> list[int]:
    with conn.cursor() as cur:
        cur.execute(f"select id from {table}")
        return [row[0] for row in cur.fetchall()]


def ensure_tournaments(conn) -> list[int]:
    with conn.cursor() as cur:
        for name, season in BASE_TOURNAMENTS:
            cur.execute(
                "insert into tournaments (name, season) values (%s, %s) "
                "on conflict (name) do nothing",
                (name, season),
            )
    conn.commit()
    return fetch_ids(conn, "tournaments")


def gen_teams(conn, count: int, tournament_ids: list[int]) -> None:
    log(f"команды: {count}")
    with conn.cursor().copy(
        "copy teams (name, city, founded_year) from stdin"
    ) as copy:
        for i in range(count):
            copy.write_row(
                (
                    f"{random.choice(CLUB_A)}-{i}",
                    random.choice(CITIES),
                    random.randint(1900, 2020),
                )
            )
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("select id from teams order by id desc limit %s", (count,))
        new_teams = [row[0] for row in cur.fetchall()]

    log("связи команда-турнир")
    with conn.cursor().copy(
        "copy team_tournaments (team_id, tournament_id) from stdin"
    ) as copy:
        for team_id in new_teams:
            picked = random.sample(
                tournament_ids, k=min(len(tournament_ids), random.randint(1, 3))
            )
            for tournament_id in picked:
                copy.write_row((team_id, tournament_id))
    conn.commit()


def gen_players(conn, count: int, team_ids: list[int]) -> None:
    if not team_ids:
        sys.exit("нет команд: сначала сгенерируйте команды (--teams)")
    log(f"игроки: {count}")
    with conn.cursor().copy(
        "copy players (full_name, team_id, position, birth_year, shirt_number) from stdin"
    ) as copy:
        for _ in range(count):
            copy.write_row(
                (
                    f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    random.choice(team_ids),
                    random.choice(POSITIONS),
                    random.randint(1985, 2008),
                    random.randint(1, 99),
                )
            )
    conn.commit()


def gen_matches(conn, count: int, team_ids: list[int], tournament_ids: list[int], days: int) -> None:
    if len(team_ids) < 2:
        sys.exit("нужно минимум две команды")
    log(f"матчи: {count} (за последние {days} дней)")
    now = datetime.now(timezone.utc)
    with conn.cursor().copy(
        "copy matches (tournament_id, home_team_id, away_team_id, status, "
        "started_at, home_score, away_score, created_at) from stdin"
    ) as copy:
        for _ in range(count):
            home, away = random.sample(team_ids, 2)
            started_at = now - timedelta(
                days=random.randint(0, days), seconds=random.randint(0, 86399)
            )
            copy.write_row(
                (
                    random.choice(tournament_ids),
                    home,
                    away,
                    "FINISHED",
                    started_at,
                    random.randint(0, 5),
                    random.randint(0, 5),
                    started_at,
                )
            )
    conn.commit()


def gen_events(conn, count: int) -> None:
    log("читаю матчи и составы")
    with conn.cursor() as cur:
        cur.execute("select id, home_team_id, away_team_id, started_at from matches")
        matches = cur.fetchall()
        cur.execute("select id, team_id from players")
        players_by_team = defaultdict(list)
        for player_id, team_id in cur.fetchall():
            players_by_team[team_id].append(player_id)

    matches = [m for m in matches if players_by_team[m[1]] or players_by_team[m[2]]]
    if not matches:
        sys.exit("нет матчей с игроками: сначала сгенерируйте команды, игроков и матчи")

    log(f"события матчей: {count}")
    started = time.time()
    with conn.cursor().copy(
        "copy match_events (match_id, player_id, event_type, minute, created_at, updated_at) "
        "from stdin"
    ) as copy:
        for i in range(count):
            match_id, home_id, away_id, started_at = random.choice(matches)
            squad = players_by_team[random.choice((home_id, away_id))]
            if not squad:
                squad = players_by_team[home_id] or players_by_team[away_id]
            minute = random.randint(1, 95)
            created_at = started_at + timedelta(minutes=minute)
            copy.write_row(
                (
                    match_id,
                    random.choice(squad),
                    random.choices(EVENT_TYPES, weights=EVENT_WEIGHTS)[0],
                    minute,
                    created_at,
                    created_at,
                )
            )
            if i and i % 200_000 == 0:
                log(f"  ...{i} строк за {time.time() - started:.1f} c")
    conn.commit()
    log(f"события готовы за {time.time() - started:.1f} c")


def main() -> None:
    parser = argparse.ArgumentParser(description="Генератор тестовых данных футбольного сервиса")
    parser.add_argument("--teams", type=int, default=0)
    parser.add_argument("--players", type=int, default=0)
    parser.add_argument("--matches", type=int, default=0)
    parser.add_argument("--events", type=int, default=0)
    parser.add_argument(
        "--days", type=int, default=730, help="разброс дат матчей в днях"
    )
    parser.add_argument("--seed", type=int, default=None, help="seed для random")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    started = time.time()
    with psycopg.connect(DATABASE_URL) as conn:
        tournament_ids = ensure_tournaments(conn)

        if args.teams:
            gen_teams(conn, args.teams, tournament_ids)
        if args.players:
            gen_players(conn, args.players, fetch_ids(conn, "teams"))
        if args.matches:
            gen_matches(conn, args.matches, fetch_ids(conn, "teams"), tournament_ids, args.days)
        if args.events:
            gen_events(conn, args.events)

        log("analyze")
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("analyze")

        with conn.cursor() as cur:
            for table in ("teams", "tournaments", "team_tournaments",
                          "players", "matches", "match_events"):
                cur.execute(f"select count(*) from {table}")
                log(f"{table}: {cur.fetchone()[0]}")

    log(f"всего заняло {time.time() - started:.1f} c")


if __name__ == "__main__":
    main()
