def top_scorers(conn, date_from, date_to, tournament_id, limit):
    where = []
    params: list = []
    if date_from:
        where.append("e.created_at >= %s")
        params.append(date_from)
    if date_to:
        where.append("e.created_at <= %s")
        params.append(date_to)
    if tournament_id:
        where.append("m.tournament_id = %s")
        params.append(tournament_id)
    where_sql = ("where " + " and ".join(where)) if where else ""

    with conn.cursor() as cur:
        cur.execute(
            f"""
            select p.id        as player_id,
                   p.full_name,
                   t.name      as team_name,
                   count(*) filter (where e.event_type = 'GOAL')   as goals,
                   count(*) filter (where e.event_type = 'ASSIST') as assists,
                   count(*) filter (
                       where e.event_type in ('YELLOW_CARD', 'RED_CARD')
                   )                                               as cards
            from match_events e
            join matches m on m.id = e.match_id
            join players p on p.id = e.player_id
            join teams t   on t.id = p.team_id
            {where_sql}
            group by p.id, p.full_name, t.name
            order by goals desc, assists desc, p.full_name asc
            limit %s
            """,
            [*params, limit],
        )
        return cur.fetchall()


def tournament_stats(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            select tr.id   as tournament_id,
                   tr.name as tournament,
                   tr.season,
                   (
                       select count(*)
                       from team_tournaments tt
                       where tt.tournament_id = tr.id
                   )                                   as teams_count,
                   count(distinct m.id)                as matches_count,
                   count(e.id) filter (where e.event_type = 'GOAL') as goals_count,
                   count(e.id) filter (where e.event_type = 'GOAL')::numeric
                       / nullif(count(distinct m.id), 0)            as avg_goals_per_match
            from tournaments tr
            left join matches m      on m.tournament_id = tr.id
            left join match_events e on e.match_id = m.id
            group by tr.id, tr.name, tr.season
            order by matches_count desc, tr.name asc
            """
        )
        return cur.fetchall()


def team_stats(conn, limit):
    with conn.cursor() as cur:
        cur.execute(
            """
            select t.id   as team_id,
                   t.name,
                   t.city,
                   count(distinct p.id)                             as players_count,
                   count(e.id) filter (where e.event_type = 'GOAL') as goals_count,
                   count(e.id) filter (
                       where e.event_type in ('YELLOW_CARD', 'RED_CARD')
                   )                                                as cards_count,
                   max(e.created_at)                                as last_event_at
            from teams t
            left join players p      on p.team_id = t.id
            left join match_events e on e.player_id = p.id
            group by t.id, t.name, t.city
            order by goals_count desc, t.name asc
            limit %s
            """,
            (limit,),
        )
        return cur.fetchall()
