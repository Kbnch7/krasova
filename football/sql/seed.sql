insert into teams (id, name, city, founded_year) values
    (1, 'Спартак',    'Москва',           1922),
    (2, 'Зенит',      'Санкт-Петербург',  1925),
    (3, 'ЦСКА',       'Москва',           1911),
    (4, 'Локомотив',  'Москва',           1922),
    (5, 'Краснодар',  'Краснодар',        2008),
    (6, 'Динамо',     'Москва',           1923);
select setval('teams_id_seq', (select max(id) from teams));

insert into tournaments (id, name, season) values
    (1, 'РПЛ',                '2025/2026'),
    (2, 'Кубок России',       '2025/2026'),
    (3, 'Суперкубок России',  '2025'),
    (4, 'Лига чемпионов',     '2025/2026');
select setval('tournaments_id_seq', (select max(id) from tournaments));

insert into team_tournaments (team_id, tournament_id) values
    (1, 1), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1),
    (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
    (2, 3), (5, 3),
    (2, 4);

insert into players (id, full_name, team_id, position, birth_year, shirt_number) values
    (1,  'Артем Соколов',    1, 'GK',  1998,  1),
    (2,  'Никита Волков',    1, 'DEF', 2001,  3),
    (3,  'Роман Гусев',      1, 'MID', 2000,  8),
    (4,  'Егор Панов',       1, 'FWD', 1997,  9),
    (5,  'Илья Крылов',      2, 'GK',  1999,  1),
    (6,  'Тимур Асланов',    2, 'DEF', 2002,  4),
    (7,  'Марк Дементьев',   2, 'MID', 1996, 10),
    (8,  'Данила Орлов',     2, 'FWD', 2000, 11),
    (9,  'Кирилл Зайцев',    3, 'GK',  2003,  1),
    (10, 'Глеб Морозов',     3, 'DEF', 1999,  5),
    (11, 'Матвей Лебедев',   3, 'MID', 2004,  6),
    (12, 'Иван Беляев',      3, 'FWD', 1998,  7),
    (13, 'Антон Ершов',      4, 'GK',  1997,  1),
    (14, 'Павел Гаврилов',   4, 'DEF', 2000,  2),
    (15, 'Денис Королев',    4, 'MID', 2001, 17),
    (16, 'Сергей Титов',     4, 'FWD', 1995,  9),
    (17, 'Максим Фомин',     5, 'GK',  2000,  1),
    (18, 'Виктор Носов',     5, 'DEF', 1998, 15),
    (19, 'Лев Тарасов',      5, 'MID', 2002, 21),
    (20, 'Арсений Жуков',    5, 'FWD', 1999, 19),
    (21, 'Юрий Савельев',    6, 'GK',  1996,  1),
    (22, 'Олег Кузьмин',     6, 'DEF', 1999, 13),
    (23, 'Артур Мельник',    6, 'MID', 2003, 14),
    (24, 'Богдан Резник',    6, 'FWD', 2001, 20);
select setval('players_id_seq', (select max(id) from players));

insert into matches (id, tournament_id, home_team_id, away_team_id, status, started_at, home_score, away_score) values
    (1, 1, 1, 2, 'FINISHED',  now() - interval '50 days', 2, 1),
    (2, 1, 3, 4, 'FINISHED',  now() - interval '45 days', 0, 0),
    (3, 1, 5, 6, 'FINISHED',  now() - interval '40 days', 3, 2),
    (4, 1, 2, 3, 'FINISHED',  now() - interval '30 days', 1, 1),
    (5, 2, 4, 1, 'FINISHED',  now() - interval '20 days', 2, 3),
    (6, 1, 6, 2, 'FINISHED',  now() - interval '10 days', 0, 2),
    (7, 1, 1, 3, 'SCHEDULED', now() + interval '5 days',  0, 0),
    (8, 2, 5, 4, 'SCHEDULED', now() + interval '12 days', 0, 0);
select setval('matches_id_seq', (select max(id) from matches));

insert into match_events (match_id, player_id, event_type, minute, created_at, updated_at)
select v.match_id, v.player_id, v.event_type, v.minute,
       m.started_at + make_interval(mins => v.minute),
       m.started_at + make_interval(mins => v.minute)
from (values
    (1,  4, 'GOAL',         23),
    (1,  2, 'ASSIST',       23),
    (1,  2, 'YELLOW_CARD',  55),
    (1,  3, 'GOAL',         67),
    (1,  8, 'GOAL',         80),
    (1,  7, 'ASSIST',       80),
    (2, 10, 'YELLOW_CARD',  30),
    (2, 12, 'SUBSTITUTION', 60),
    (2, 14, 'YELLOW_CARD',  70),
    (3, 20, 'GOAL',         20),
    (3, 18, 'ASSIST',       20),
    (3, 19, 'GOAL',         44),
    (3, 24, 'GOAL',         51),
    (3, 20, 'GOAL',         75),
    (3, 22, 'RED_CARD',     82),
    (3, 23, 'GOAL',         88),
    (4,  8, 'GOAL',         12),
    (4,  6, 'YELLOW_CARD',  40),
    (4, 12, 'GOAL',         65),
    (5, 16, 'GOAL',         15),
    (5,  4, 'GOAL',         30),
    (5,  2, 'ASSIST',       30),
    (5, 13, 'YELLOW_CARD',  55),
    (5,  4, 'GOAL',         60),
    (5, 15, 'GOAL',         70),
    (5,  3, 'GOAL',         85),
    (6,  8, 'GOAL',         25),
    (6, 22, 'SUBSTITUTION', 46),
    (6,  7, 'GOAL',         71)
) as v(match_id, player_id, event_type, minute)
join matches m on m.id = v.match_id;
