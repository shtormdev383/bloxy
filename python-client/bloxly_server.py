#!/usr/bin/env python3
"""BLOXLY — сервер мультиплеера (asyncio, без сторонних библиотек).
Запуск: python bloxly_server.py [порт]   (по умолчанию 8765)
Аккаунты, друзья и счёт хранятся в bloxly_server_db.json рядом со скриптом.
Внимание: соединение не шифруется — используй в локальной сети или с VPN.
by shtorm and claude sonnet 5.5"""
import asyncio, hashlib, json, os, random, re, sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
DBF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bloxly_server_db.json")
try:
    with open(DBF, encoding="utf-8") as f:
        db = json.load(f)
except Exception:
    db = {"users": {}}
dirty = False
conn, world, coins = {}, {}, []   # имя -> writer; имя -> {x,y,c,s}; [[x,y],...]


def hp(p, salt):
    return hashlib.pbkdf2_hmac("sha256", p.encode(), bytes.fromhex(salt), 60000).hex()


def tx(w, o):
    try:
        w.write((json.dumps(o, ensure_ascii=False) + "\n").encode())
    except Exception:
        pass


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
    elif t == "join":
        world[n] = {"x": 400, "y": 250, "c": u["c"], "s": 0}
    elif t == "leave":
        world.pop(n, None)
    elif t == "mv" and n in world:
        p = world[n]
        p["x"] = max(20, min(780, float(m.get("x", p["x"]))))
        p["y"] = max(20, min(480, float(m.get("y", p["y"]))))


async def handle(r, w):
    me = None
    try:
        while True:
            line = await r.readline()
            if not line:
                break
            try:
                m = json.loads(line)
                t = m["t"]
                if me is None:
                    if t == "login":
                        me = login(m, w)
                else:
                    act(me, t, m, w)
            except (ValueError, TypeError, KeyError, AttributeError):
                continue
    except Exception:
        pass
    finally:
        if me and conn.get(me) is w:
            conn.pop(me)
            world.pop(me, None)
            bc({"t": "on", "list": list(conn)})
        w.close()


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


async def main():
    srv = await asyncio.start_server(handle, "0.0.0.0", PORT, limit=8192)
    asyncio.create_task(ticker())
    print(f"BLOXLY сервер запущен на порту {PORT}. Ctrl+C — остановить.")
    try:
        await srv.serve_forever()
    finally:
        save()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
