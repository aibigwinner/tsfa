import json
import random
import threading
from datetime import datetime
from pathlib import Path
from config import ADMIN_IDS

DATA_DIR = Path(__file__).parent / "data"


class JSONStorage:
    def __init__(self, filename):
        self.path = DATA_DIR / filename
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write({})

    def _read(self):
        with self._lock:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _write(self, data):
        with self._lock:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, key, default=None):
        return self._read().get(key, default)

    def set(self, key, value):
        data = self._read()
        data[key] = value
        self._write(data)

    def delete(self, key):
        data = self._read()
        data.pop(key, None)
        self._write(data)

    def all(self):
        return self._read()

    def filter(self, predicate):
        return {k: v for k, v in self._read().items() if predicate(k, v)}


players = JSONStorage("players.json")
battles = JSONStorage("battles.json")
tournaments = JSONStorage("tournaments.json")
challenges = JSONStorage("challenges.json")
polls = JSONStorage("polls.json")


# ---- Players ----

def get_or_create_player(user_id, username=None, first_name=None):
    user_id = str(user_id)
    data = players._read()
    if user_id not in data:
        data[user_id] = {
            "username": username,
            "first_name": first_name or "Игрок",
            "rating": 1000,
            "wins": 0,
            "losses": 0,
            "total_battles": 0,
            "is_admin": int(user_id) in ADMIN_IDS,
            "is_banned": False,
            "registered_at": datetime.now().isoformat(),
            "achievements": [],
            "characters": {},
            "current_streak": 0,
            "max_streak": 0,
            "tournament_wins": 0,
        }
        players._write(data)
    return data[user_id]


def get_player(user_id):
    return players.get(str(user_id))


def update_player(user_id, **kwargs):
    user_id = str(user_id)
    data = players._read()
    if user_id in data:
        data[user_id].update(kwargs)
        players._write(data)


# ---- Characters ----

def add_character_usage(user_id, character, won: bool):
    user_id = str(user_id)
    data = players._read()
    if user_id not in data:
        return
    chars = data[user_id].setdefault("characters", {})
    name = character.strip().lower()
    if name not in chars:
        chars[name] = {"name": character.strip(), "wins": 0, "losses": 0, "total": 0}
    chars[name]["total"] += 1
    if won:
        chars[name]["wins"] += 1
    else:
        chars[name]["losses"] += 1
    players._write(data)


# ---- Streaks ----

def update_streak(user_id, won: bool):
    user_id = str(user_id)
    data = players._read()
    if user_id not in data:
        return
    if won:
        data[user_id]["current_streak"] = data[user_id].get("current_streak", 0) + 1
        cs = data[user_id]["current_streak"]
        if cs > data[user_id].get("max_streak", 0):
            data[user_id]["max_streak"] = cs
    else:
        data[user_id]["current_streak"] = 0
    players._write(data)


# ---- Achievements ----

def award_achievement(user_id, achievement_id):
    user_id = str(user_id)
    data = players._read()
    if user_id not in data:
        return False
    earned = data[user_id].setdefault("achievements", [])
    if achievement_id not in earned:
        earned.append(achievement_id)
        data[user_id]["achievements"] = earned
        players._write(data)
        return True
    return False


# ---- Battles ----

def create_battle(game_id, creator_id, battle_type="friendly", character=None):
    battle_id = f"battle_{int(datetime.now().timestamp())}"
    creator_id = str(creator_id)
    battle = {
        "id": battle_id,
        "game_id": game_id,
        "creator_id": creator_id,
        "opponent_id": None,
        "status": "waiting",
        "type": battle_type,
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
        "winner_id": None,
        "tournament_id": None,
        "screenshots": [],
        "character_creator": character,
        "character_opponent": None,
    }
    battles.set(battle_id, battle)
    return battle


def join_battle(battle_id, player_id):
    battle = battles.get(battle_id)
    if not battle or battle["status"] != "waiting":
        return None
    battle["opponent_id"] = str(player_id)
    battle["status"] = "active"
    battles.set(battle_id, battle)
    return battle


def set_battle_character(battle_id, player_id, character):
    battle = battles.get(battle_id)
    if not battle:
        return False
    player_id = str(player_id)
    if player_id == battle["creator_id"]:
        battle["character_creator"] = character
    elif player_id == battle.get("opponent_id"):
        battle["character_opponent"] = character
    else:
        return False
    battles.set(battle_id, battle)
    return True


def add_screenshot(battle_id, file_id):
    battle = battles.get(battle_id)
    if not battle:
        return False
    battle.setdefault("screenshots", []).append(file_id)
    battles.set(battle_id, battle)
    return True


def complete_battle(battle_id, winner_id):
    battle = battles.get(battle_id)
    if not battle:
        return None
    battle["status"] = "completed"
    battle["winner_id"] = str(winner_id)
    battle["completed_at"] = datetime.now().isoformat()
    battles.set(battle_id, battle)

    winner_id = str(winner_id)
    loser_id = (
        battle["opponent_id"]
        if battle["creator_id"] == winner_id
        else battle["creator_id"]
    )

    update_player(winner_id, wins=players.get(winner_id, {}).get("wins", 0) + 1)
    update_player(loser_id, losses=players.get(loser_id, {}).get("losses", 0) + 1)
    for uid in [winner_id, loser_id]:
        update_player(uid, total_battles=players.get(uid, {}).get("total_battles", 0) + 1)

    update_streak(winner_id, True)
    update_streak(loser_id, False)

    if battle.get("character_creator"):
        add_character_usage(
            battle["creator_id"], battle["character_creator"],
            winner_id == battle["creator_id"],
        )
    if battle.get("character_opponent"):
        add_character_usage(
            battle["opponent_id"], battle["character_opponent"],
            winner_id == battle["opponent_id"],
        )

    return battle


def cancel_battle(battle_id):
    battle = battles.get(battle_id)
    if not battle:
        return None
    battle["status"] = "cancelled"
    battles.set(battle_id, battle)
    return battle


# ---- Tournaments ----

def create_tournament(name, creator_id, max_players=8):
    tid = f"tournament_{int(datetime.now().timestamp())}"
    tournament = {
        "id": tid,
        "name": name,
        "description": "",
        "status": "registration",
        "created_by": str(creator_id),
        "max_players": max_players,
        "players": [],
        "bracket": [],
        "current_round": 0,
        "created_at": datetime.now().isoformat(),
    }
    tournaments.set(tid, tournament)
    return tournament


def register_for_tournament(tournament_id, player_id):
    player_id = str(player_id)
    tournament = tournaments.get(tournament_id)
    if not tournament:
        return None, "Турнир не найден"
    if tournament["status"] != "registration":
        return None, "Регистрация уже закрыта"
    if len(tournament["players"]) >= tournament["max_players"]:
        return None, "Турнир уже заполнен"
    if any(p["id"] == player_id for p in tournament["players"]):
        return None, "Вы уже зарегистрированы"
    player_data = get_player(player_id)
    tournament["players"].append({
        "id": player_id,
        "username": player_data.get("username"),
        "first_name": player_data.get("first_name", "Игрок"),
    })
    tournaments.set(tournament_id, tournament)
    return tournament, None


def generate_bracket(tournament_id):
    t = tournaments.get(tournament_id)
    if not t or t["status"] != "registration":
        return None, "Турнир не в статусе регистрации"
    if len(t["players"]) < 2:
        return None, "Недостаточно игроков (минимум 2)"

    players_list = list(t["players"])
    random.shuffle(players_list)
    n = len(players_list)

    next_pow2 = 1
    while next_pow2 < n:
        next_pow2 *= 2
    byes = next_pow2 - n

    round1 = []
    i = 0
    while i < n:
        if byes > 0:
            round1.append({
                "p1": players_list[i],
                "p2": None,
                "winner": players_list[i],
                "bye": True,
            })
            byes -= 1
            i += 1
        else:
            if i + 1 < n:
                round1.append({
                    "p1": players_list[i],
                    "p2": players_list[i + 1],
                    "winner": None,
                    "bye": False,
                })
                i += 2
            else:
                round1.append({
                    "p1": players_list[i],
                    "p2": None,
                    "winner": players_list[i],
                    "bye": True,
                })
                i += 1

    t["bracket"] = [round1]
    t["current_round"] = 1
    t["status"] = "ongoing"
    tournaments.set(tournament_id, t)
    return t, None


def advance_round(tournament_id, match_index, winner_id):
    t = tournaments.get(tournament_id)
    if not t or t["status"] != "ongoing":
        return None, "Турнир не идёт"

    current_round_idx = t["current_round"] - 1
    if current_round_idx >= len(t["bracket"]):
        return None, "Турнир уже завершён"

    current_round = t["bracket"][current_round_idx]
    if match_index < 0 or match_index >= len(current_round):
        return None, "Некорректный индекс матча"

    match = current_round[match_index]
    if match.get("bye"):
        return None, "В этом матче был авто-проход"

    winner_id = str(winner_id)
    p1_id = match["p1"]["id"] if isinstance(match["p1"], dict) else match["p1"]
    p2_id = match["p2"]["id"] if isinstance(match["p2"], dict) else match["p2"]
    if winner_id not in (p1_id, p2_id):
        return None, "Победитель не из этого матча"

    match["winner"] = match["p1"] if p1_id == winner_id else match["p2"]
    tournaments.set(tournament_id, t)

    all_done = all(m.get("winner") for m in current_round)
    if not all_done:
        return t, "Победитель записан. Ждём остальные матчи раунда."

    if len(current_round) == 1:
        t["status"] = "completed"
        winner_data = get_player(winner_id)
        if winner_data:
            tw = winner_data.get("tournament_wins", 0) + 1
            update_player(winner_id, tournament_wins=tw)
        tournaments.set(tournament_id, t)
        return t, f"🏆 Турнир завершён! Победитель: {match['winner'].get('first_name', '???')}"

    next_round = []
    for i in range(0, len(current_round), 2):
        m1 = current_round[i]
        m2 = current_round[i + 1] if i + 1 < len(current_round) else None
        if m1 and m2 and m1.get("winner") and m2.get("winner"):
            next_round.append({
                "p1": m1["winner"],
                "p2": m2["winner"],
                "winner": None,
                "bye": False,
            })
        elif m1 and m1.get("winner") and not m2:
            next_round.append({
                "p1": m1["winner"],
                "p2": None,
                "winner": m1["winner"],
                "bye": True,
            })

    t["bracket"].append(next_round)
    t["current_round"] += 1
    tournaments.set(tournament_id, t)
    return t, f"Раунд {t['current_round'] - 1} завершён! Начинается раунд {t['current_round']}."


# ---- Challenges ----

def create_challenge(title, description, creator_id, target_count=10):
    cid = f"challenge_{int(datetime.now().timestamp())}"
    challenge = {
        "id": cid,
        "title": title,
        "description": description,
        "created_by": str(creator_id),
        "target_count": target_count,
        "participants": {},
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    challenges.set(cid, challenge)
    return challenge


# ---- Polls ----

def create_poll(question, options, creator_id):
    pid = f"poll_{int(datetime.now().timestamp())}"
    poll = {
        "id": pid,
        "question": question,
        "options": {str(k): v for k, v in enumerate(options, 1)},
        "votes": {},
        "created_by": str(creator_id),
        "status": "active",
        "created_at": datetime.now().isoformat(),
    }
    polls.set(pid, poll)
    return poll


def vote_in_poll(poll_id, user_id, option_key):
    poll = polls.get(poll_id)
    if not poll or poll["status"] != "active":
        return False, "Голосование не активно"
    if option_key not in poll["options"]:
        return False, "Неверный вариант"
    user_id = str(user_id)
    poll["votes"][user_id] = option_key
    polls.set(poll_id, poll)
    return True, None


def close_poll(poll_id):
    poll = polls.get(poll_id)
    if not poll:
        return None
    poll["status"] = "closed"
    polls.set(poll_id, poll)
    return poll


def get_poll_results(poll_id):
    poll = polls.get(poll_id)
    if not poll:
        return None
    results = {}
    for opt_key, opt_label in poll["options"].items():
        count = sum(1 for v in poll["votes"].values() if v == opt_key)
        results[opt_label] = count
    return results
