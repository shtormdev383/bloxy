#!/usr/bin/env python3
"""BLOXLY — сервер мультиплеера (asyncio, без сторонних библиотек).
Запуск: python bloxly_server.py [порт]   (по умолчанию 8765)
Аккаунты, друзья и счёт хранятся в bloxly_server_db.json рядом со скриптом.
Внимание: соединение не шифруется — используй в локальной сети или с VPN.
by shtorm and claude sonnet 5.5"""
import asyncio, hashlib, json, os, random, re, time
from pathlib import Path
from aiohttp import web, WSMsgType

PORT = int(os.environ.get("PORT", "8765"))
BASE = Path(__file__).resolve().parent
DBF = os.environ.get("DB_PATH", str(BASE / "bloxly_db.json"))
try:
    with open(DBF, encoding="utf-8") as f:
        db = json.load(f)
except Exception:
    db = {"users": {}}
dirty = False
db.setdefault("forum", [])
subs, last = set(), {}
FCATS = ["Общее", "Игры", "Студия", "Трейды", "Баги", "Идеи", "Оффтоп"]
conn, world, coins = {}, {}, []   # имя -> writer; имя -> {x,y,c,s}; [[x,y],...]


def hp(p, salt):
    return hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 60000).hex()


async def _send(w, o):
    try:
        await w.send_str(json.dumps(o, ensure_ascii=False))
    except Exception:
        pass


def tx(w, o):
    asyncio.ensure_future(_send(w, o))


def bc(o, names=None):
    for n, w in list(conn.items()):
        if names is None or n in names:
            tx(w, o)


def save():
    global dirty
    tmp = DBF + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)
    os.replace(tmp, DBF)
    dirty = False


def push(n):
    if n in conn:
        u = db["users"][n]
        tx(conn[n], {"t": "fr", "fr": u["fr"], "inc": u["inc"]})


def login(m, w):
    global dirty
    n, p, U = str(m.get("n", "")).strip(), str(m.get("p", "")), db["users"]
    err = lambda x: tx(w, {"t": "err", "x": x})
    if m.get("reg"):
        if not re.fullmatch(r"\w{3,16}", n) or len(p) < 4:
            return err("Имя 3–16 символов, пароль от 4") or None
        if n in U:
            return err("Это имя уже занято") or None
        salt = os.urandom(8).hex()
        U[n] = {"s": salt, "p": hp(p, salt), "rb": 100, "fr": [], "inc": [],
                "c": "#%06x" % random.randint(0x555555, 0xffffff)}
        dirty = True
    else:
        u = U.get(n)
        if not u or u["p"] != hp(p, u["s"]):
            return err("Неверное имя или пароль") or None
    if n in conn:
        return err("Этот аккаунт уже в сети") or None
    conn[n] = w
    u = U[n]
    tx(w, {"t": "ok", "n": n, "rb": u["rb"], "fr": u["fr"], "inc": u["inc"]})
    bc({"t": "on", "list": list(conn)})
    bc({"t": "chat", "n": "★", "x": f"{n} в сети"})
    subs.add(w)
    tx(w, {"t": "forum", "list": db["forum"][-100:]})
    return n


def act(n, t, m, w):
    global dirty
    U = db["users"]
    u = U[n]
    if t == "chat":
        x = str(m.get("x", ""))[:300].strip()
        if x:
            bc({"t": "chat", "n": n, "x": x})
    elif t == "dm":
        to, x = m.get("to"), str(m.get("x", ""))[:300].strip()
        if to in conn and x:
            tx(conn[to], {"t": "dm", "n": n, "x": x})
            tx(w, {"t": "dm", "n": "→ " + str(to), "x": x})
        else:
            tx(w, {"t": "err", "x": "Игрок не в сети"})
    elif t == "fr":
        to = m.get("n")
        if to in U and to != n and to not in u["fr"] and n not in U[to]["inc"]:
            U[to]["inc"].append(n)
            dirty = True
            push(to)
            tx(w, {"t": "sys", "x": f"Запрос отправлен: {to}"})
        else:
            tx(w, {"t": "err", "x": "Нельзя добавить этого игрока"})
    elif t == "fra":
        f = m.get("n")
        if f in u["inc"]:
            u["inc"].remove(f)
            for a, b in ((n, f), (f, n)):
                if b not in U[a]["fr"]:
                    U[a]["fr"].append(b)
            dirty = True
            push(n), push(f)
    elif t == "frd":
        f = m.get("n")
        for a, b in ((n, f), (f, n)):
            if a in U and b in U[a]["fr"]:
                U[a]["fr"].remove(b)
        dirty = True
        push(n), push(f)
    elif t in ("fnew", "frep", "flike"):
        now = time.time()
        if t != "flike" and now - last.get(n, 0) < 4:
            return tx(w, {"t": "err", "x": "Не так быстро — подожди пару секунд"})
        F = db["forum"]
        if t == "fnew":
            c = m.get("c") if m.get("c") in FCATS else "Общее"
            ti, x = str(m.get("title", "")).strip()[:80], str(m.get("x", "")).strip()[:1000]
            if len(ti) < 3:
                return tx(w, {"t": "err", "x": "Заголовок от 3 символов"})
            th = {"id": int(now * 1000), "c": c, "t": ti, "x": x, "by": n, "ts": int(now * 1000), "r": [], "l": []}
            F.append(th)
            del F[:-300]
        else:
            th = next((q for q in F if q["id"] == m.get("id")), None)
            if not th:
                return
            if t == "frep":
                x = str(m.get("x", "")).strip()[:500]
                if not x or len(th["r"]) >= 300:
                    return
                th["r"].append([n, x, int(now * 1000)])
            else:
                th["l"].remove(n) if n in th["l"] else th["l"].append(n)
        if t != "flike":
            last[n] = now
        dirty = True
        for sw in list(subs):
            tx(sw, {"t": "fth", "th": th})
    elif t == "join":
        world[n] = {"x": 400, "y": 250, "c": u["c"], "s": 0}
    elif t == "leave":
        world.pop(n, None)
    elif t == "mv" and n in world:
        p = world[n]
        p["x"] = max(20, min(780, float(m.get("x", p["x"]))))
        p["y"] = max(20, min(480, float(m.get("y", p["y"]))))


async def ticker():
    k = 0
    while True:
        await asyncio.sleep(.05)
        k += 1
        while len(coins) < 12:
            coins.append([random.randint(30, 770), random.randint(30, 470)])
        for n, p in list(world.items()):
            for c in coins[:]:
                if (p["x"] - c[0]) ** 2 + (p["y"] - c[1]) ** 2 < 24 ** 2:
                    coins.remove(c)
                    p["s"] += 1
                    db["users"][n]["rb"] += 1
                    global dirty
                    dirty = True
                    bc({"t": "ev", "k": "coin", "n": n, "x": c[0], "y": c[1]})
                    if n in conn:
                        tx(conn[n], {"t": "rb", "v": db["users"][n]["rb"]})
        if world:
            bc({"t": "world", "p": world, "c": coins}, list(world))
        if dirty and k % 200 == 0:
            save()

async def ws_handler(req):
    ws = web.WebSocketResponse(heartbeat=25, max_msg_size=8192)
    await ws.prepare(req)
    me = None
    try:
        async for msg in ws:
            if msg.type != WSMsgType.TEXT:
                continue
            try:
                m = json.loads(msg.data)
                t = m["t"]
                if t == "sub":
                    subs.add(ws)
                    tx(ws, {"t": "forum", "list": db["forum"][-100:]})
                    continue
                if me is None:
                    if t == "login":
                        me = login(m, ws)
                else:
                    act(me, t, m, ws)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
    finally:
        subs.discard(ws)
        if me and conn.get(me) is ws:
            conn.pop(me)
            world.pop(me, None)
            bc({"t": "on", "list": list(conn)})
    return ws


async def index(_):
    return web.FileResponse(BASE / "index.html")


async def health(_):
    return web.Response(text="ok")


async def on_start(app):
    app["tick"] = asyncio.create_task(ticker())


async def on_stop(app):
    app["tick"].cancel()
    save()


def make_app():
    app = web.Application()
    app.add_routes([web.get("/", index), web.get("/ws", ws_handler), web.get("/health", health)])
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_stop)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), host="0.0.0.0", port=PORT)
