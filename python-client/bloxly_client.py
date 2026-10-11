#!/usr/bin/env python3
"""BLOXLY — клиент на Python (Tkinter, без сторонних библиотек), офлайн и онлайн-мультиплеер.
Запуск: python bloxly_client.py     by shtorm and claude sonnet 5.5
Данные хранятся в файле ~/.bloxly.json (только на этом компьютере)."""
import hashlib, json, math, os, queue, random, socket, threading, time
import tkinter as tk
from tkinter import colorchooser, messagebox

BG, PANEL, PANEL2, TX, MUT = "#1b1230", "#140c25", "#33224f", "#f6f3ff", "#b9aedb"
ACC = "#8b5cf6"
FILE = os.path.join(os.path.expanduser("~"), ".bloxly.json")
H = ("Arial", 20, "bold")
GAMES = [("Двор 3D", "Играбельно в веб-версии"), ("Выживание в зомби", "Тапай по зомби 20 секунд"),
         ("Пиццерия тайкун", "Кликер: пеки пиццу, покупай печи"), ("Лава! Беги!", "Скоро в клиенте"),
         ("Башня-паркур 3D", "Играбельно в веб-версии")]
BOTS = [("Мишка_Про", 1), ("Neo_Builder", 2), ("Sasha2012", 0), ("KotikGamer", 1), ("Dasha_Star", 0)]
STAT = {0: "не в сети", 1: "в сети", 2: "играет"}
REPLY = ["Привет! 👋", "Го в игру?", "Ахах, классно", "Давай!", "Окей 👍", "Я сейчас занят"]


class Net:
    """Сетевой слой: поток читает строки JSON с сервера и кладёт их в очередь."""

    def __init__(s):
        s.sock, s.ok, s.q = None, False, queue.Queue()
        s.name, s.rb, s.fr, s.inc, s.online = None, 0, [], [], []
        s.log, s.world, s.coins, s.ev = [], {}, [], []

    def connect(s, host, port):
        s.sock = socket.create_connection((host, port), timeout=5)
        s.sock.settimeout(None)
        threading.Thread(target=s.reader, daemon=True).start()

    def reader(s):
        buf = b""
        try:
            while True:
                d = s.sock.recv(4096)
                if not d:
                    break
                buf += d
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    try:
                        s.q.put(json.loads(line))
                    except ValueError:
                        pass
        except OSError:
            pass
        s.q.put({"t": "closed"})

    def send(s, o):
        try:
            s.sock.sendall((json.dumps(o, ensure_ascii=False) + "\n").encode())
        except Exception:
            pass


class App(tk.Tk):
    def __init__(s):
        super().__init__()
        s.title("BLOXLY — клиент")
        s.geometry("920x620")
        s.configure(bg=BG)
        s.u = None
        s.net = None
        s.after(30, s.poll)
        try:
            with open(FILE, encoding="utf-8") as f:
                s.db = json.load(f)
        except Exception:
            s.db = {"users": {}}
        s.login()

    # ---------- утилиты
    @property
    def me(s):
        return s.db["users"][s.u]

    def save(s):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(s.db, f, ensure_ascii=False)

    def clear(s, w=None):
        for x in (w or s).winfo_children():
            x.destroy()

    def b(s, p, t, cmd, bg=None):
        return tk.Button(p, text=t, command=cmd, bg=bg or PANEL2, fg=TX, relief="flat", padx=12, pady=6,
                         activebackground=ACC, activeforeground=TX, cursor="hand2")

    def lab(s, p, t, f=("Arial", 11), fg=TX, bg=BG):
        return tk.Label(p, text=t, font=f, bg=bg, fg=fg, justify="left")

    def go(s, page):
        s.clear(s.c)
        page()

    # ---------- вход
    def login(s):
        s.u = None
        s.clear()
        f = tk.Frame(s, bg=PANEL, padx=36, pady=28)
        f.place(relx=.5, rely=.5, anchor="c")
        s.lab(f, "BLOXLY", ("Arial", 32, "bold"), ACC, PANEL).pack()
        s.lab(f, "клиент на Python", fg=MUT, bg=PANEL).pack(pady=(0, 12))
        e1, e2 = tk.Entry(f, width=26), tk.Entry(f, width=26, show="•")
        e1.pack(pady=4)
        e2.pack(pady=4)

        def enter(reg):
            n, raw = e1.get().strip(), e2.get()
            p, U = hashlib.sha256(raw.encode()).hexdigest(), s.db["users"]
            if reg:
                if len(n) < 3 or len(raw) < 4:
                    return messagebox.showwarning("BLOXLY", "Имя от 3 символов, пароль от 4")
                if n in U or n in dict(BOTS):
                    return messagebox.showwarning("BLOXLY", "Это имя уже занято")
                U[n] = {"p": p, "rb": 100, "fr": [], "chats": {}, "dly": "", "ck": {"n": 0, "pw": 1, "au": 0},
                        "look": {"skin": "#f2c9a0", "shirt": "#e5484d", "bg": "#335fff", "hat": "none"}}
            elif n not in U or U[n]["p"] != p:
                return messagebox.showwarning("BLOXLY", "Неверное имя или пароль")
            s.u = n
            s.save()
            s.main()

        s.b(f, "Войти", lambda: enter(False), ACC).pack(fill="x", pady=(10, 4))
        s.b(f, "Создать аккаунт", lambda: enter(True)).pack(fill="x")

    # ---------- каркас
    def main(s):
        s.clear()
        sb = tk.Frame(s, bg=PANEL, width=190)
        sb.pack(side="left", fill="y")
        s.lab(sb, "BLOXLY", ("Arial", 20, "bold"), ACC, PANEL).pack(pady=16)
        for t, pg in [("🏠 Главная", s.p_home), ("🎮 Игры", s.p_games), ("👥 Друзья", s.p_friends), ("🌐 Онлайн", s.p_online),
                      ("🧍 Аватар", s.p_avatar), ("⚙️ Настройки", s.p_set)]:
            tk.Button(sb, text=t, command=lambda p=pg: s.go(p), bg=PANEL, fg=TX, relief="flat", anchor="w",
                      padx=16, pady=8, activebackground=PANEL2, activeforeground=TX).pack(fill="x")
        s.b(sb, "Выйти", s.login).pack(side="bottom", fill="x", padx=10, pady=10)
        s.c = tk.Frame(s, bg=BG, padx=24, pady=18)
        s.c.pack(side="left", fill="both", expand=True)
        s.p_home()

    # ---------- страницы
    def p_home(s):
        m = s.me
        s.lab(s.c, f"Привет, {s.u}!", H).pack(anchor="w")
        s.lab(s.c, f"R$ {m['rb']}  ·  друзей: {len(m['fr'])}", ("Arial", 13), MUT).pack(anchor="w", pady=4)
        s.b(s.c, "🎁 Ежедневный бонус +20 R$", s.daily, ACC).pack(anchor="w", pady=8)
        s.lab(s.c, "Друзья", ("Arial", 15, "bold")).pack(anchor="w", pady=(14, 4))
        if not m["fr"]:
            s.lab(s.c, "Пока никого. Добавь друзей во вкладке «Друзья».", fg=MUT).pack(anchor="w")
        for n, st in BOTS:
            if n in m["fr"]:
                s.lab(s.c, f"•  {n} — {STAT[st]}").pack(anchor="w")

    def daily(s):
        d = time.strftime("%Y-%m-%d")
        if s.me["dly"] == d:
            return messagebox.showinfo("BLOXLY", "Бонус уже получен. Приходи завтра!")
        s.me["dly"] = d
        s.me["rb"] += 20
        s.save()
        s.go(s.p_home)

    def p_games(s):
        s.lab(s.c, "Игры", H).pack(anchor="w", pady=(0, 8))
        for i, (n, d) in enumerate(GAMES):
            r = tk.Frame(s.c, bg=PANEL, padx=12, pady=10)
            r.pack(fill="x", pady=3)
            s.lab(r, f"{n}\n{d}", bg=PANEL).pack(side="left")
            s.b(r, "▶ Играть", lambda i=i: s.play(i), ACC).pack(side="right")

    def play(s, i):
        {1: s.zomb, 2: s.clicker}.get(i, lambda: messagebox.showinfo(
            "BLOXLY", "Эта игра играбельна в веб-версии. Здесь доступны «Зомби» и «Пиццерия»."))()

    def p_friends(s):
        s.lab(s.c, "Друзья", H).pack(anchor="w", pady=(0, 8))
        for n, st in BOTS:
            r = tk.Frame(s.c, bg=PANEL, padx=12, pady=8)
            r.pack(fill="x", pady=3)
            s.lab(r, f"{n}  —  {STAT[st]}", bg=PANEL).pack(side="left")
            if n in s.me["fr"]:
                s.b(r, "Чат", lambda n=n: s.chat(n), ACC).pack(side="right", padx=3)
                s.b(r, "Удалить", lambda n=n: s.toggle(n)).pack(side="right")
            else:
                s.b(r, "Добавить", lambda n=n: s.toggle(n), ACC).pack(side="right")

    def toggle(s, n):
        L = s.me["fr"]
        L.remove(n) if n in L else L.append(n)
        s.save()
        s.go(s.p_friends)

    def chat(s, n):
        w = tk.Toplevel(s, bg=PANEL)
        w.title(n)
        t = tk.Text(w, width=44, height=16, bg=BG, fg=TX, state="disabled", wrap="word")
        t.pack(padx=8, pady=8)
        h = s.me["chats"].setdefault(n, [])
        e = tk.Entry(w, width=40)
        e.pack(side="left", padx=8, pady=(0, 8))

        def draw():
            t.config(state="normal")
            t.delete("1.0", "end")
            for mine, x in h:
                t.insert("end", ("Я: " if mine else n + ": ") + x + "\n")
            t.config(state="disabled")
            t.see("end")

        def reply():
            if w.winfo_exists():
                h.append([0, random.choice(REPLY)])
                s.save()
                draw()

        def send(_=None):
            x = e.get().strip()
            if x:
                h.append([1, x])
                e.delete(0, "end")
                s.save()
                draw()
                w.after(800, reply)

        e.bind("<Return>", send)
        s.b(w, "Отправить", send, ACC).pack(side="left", pady=(0, 8))
        draw()

    def p_avatar(s):
        L = s.me["look"]
        s.lab(s.c, "Аватар", H).pack(anchor="w")
        cv = tk.Canvas(s.c, width=220, height=270, bg=L["bg"], highlightthickness=0)
        cv.pack(side="left", padx=(0, 20))

        def draw():
            cv.delete("all")
            cv.config(bg=L["bg"])
            cv.create_polygon(30, 270, 60, 190, 160, 190, 190, 270, fill=L["shirt"], outline="")
            cv.create_oval(65, 60, 155, 150, fill=L["skin"], outline="")
            cv.create_oval(90, 95, 100, 107, fill="#222")
            cv.create_oval(120, 95, 130, 107, fill="#222")
            cv.create_arc(90, 105, 130, 135, start=200, extent=140, style="arc", width=3)
            if L["hat"] == "cap":
                cv.create_arc(62, 40, 158, 130, start=0, extent=180, fill="#e5484d", outline="")
            if L["hat"] == "crown":
                cv.create_polygon(75, 70, 80, 35, 100, 55, 110, 25, 120, 55, 140, 35, 145, 70, fill="#f5c518", outline="")

        def pick(k):
            c = colorchooser.askcolor(color=L[k])[1]
            if c:
                L[k] = c
                s.save()
                draw()

        def hat(x):
            L["hat"] = x
            s.save()
            draw()

        r = tk.Frame(s.c, bg=BG)
        r.pack(side="left", anchor="n", pady=30)
        for t, k in [("Цвет кожи", "skin"), ("Цвет футболки", "shirt"), ("Цвет фона", "bg")]:
            s.b(r, t, lambda k=k: pick(k)).pack(fill="x", pady=3)
        for t, x in [("Без шапки", "none"), ("Кепка", "cap"), ("Корона", "crown")]:
            s.b(r, t, lambda x=x: hat(x)).pack(fill="x", pady=3)
        draw()

    def p_set(s):
        def ch():
            global ACC
            c = colorchooser.askcolor(color=ACC)[1]
            if c:
                ACC = c
                s.main()

        s.lab(s.c, "Настройки", H).pack(anchor="w")
        s.b(s.c, "Цвет акцента", ch, ACC).pack(anchor="w", pady=10)
        s.lab(s.c, "BLOXLY — клиент на Python\nby shtorm and claude sonnet 5.5", fg=MUT).pack(anchor="w", pady=20)

    # ---------- онлайн / мультиплеер
    def poll(s):
        while s.net and not s.net.q.empty():
            s.on_msg(s.net.q.get_nowait())
        s.after(30, s.poll)

    def on_msg(s, m):
        n, t = s.net, m.get("t")
        if not n:
            return
        if t == "ok":
            n.ok, n.name, n.rb, n.fr, n.inc = True, m["n"], m["rb"], m["fr"], m["inc"]
            s.go(s.p_online)
        elif t == "err":
            messagebox.showwarning("BLOXLY", m["x"])
            if not n.ok:
                s.net = None
        elif t in ("chat", "dm", "sys"):
            n.log.append(f"[ЛС] {m['n']}: {m['x']}" if t == "dm" else
                         (f"* {m['x']}" if t == "sys" else f"{m['n']}: {m['x']}"))
            n.log[:] = n.log[-200:]
            s.refresh_chat()
        elif t == "on":
            n.online = m["list"]
            s.render_online()
        elif t == "fr":
            n.fr, n.inc = m["fr"], m["inc"]
            s.render_online()
        elif t == "rb":
            n.rb = m["v"]
        elif t == "world":
            n.world, n.coins = m["p"], m["c"]
        elif t == "ev":
            n.ev.append(m)
            n.ev[:] = n.ev[-50:]
        elif t == "closed":
            if n.ok:
                messagebox.showinfo("BLOXLY", "Соединение с сервером потеряно")
            s.net = None
            s.go(s.p_online)

    def p_online(s):
        s.lab(s.c, "Онлайн", H).pack(anchor="w", pady=(0, 8))
        n = s.net
        if not (n and n.ok):
            return s.online_login()
        top = tk.Frame(s.c, bg=BG)
        top.pack(fill="x")
        s.lab(top, f"Ты: {n.name}   ·   /w имя текст — личное сообщение", fg=MUT).pack(side="left")
        s.b(top, "⚔️ Арена", s.arena, ACC).pack(side="right")
        body = tk.Frame(s.c, bg=BG)
        body.pack(fill="both", expand=True, pady=8)
        left = tk.Frame(body, bg=PANEL)
        left.pack(side="left", fill="both", expand=True)
        s.chat_box = tk.Text(left, bg=BG, fg=TX, state="disabled", wrap="word", height=18)
        s.chat_box.pack(fill="both", expand=True, padx=6, pady=6)
        e = tk.Entry(left)
        e.pack(fill="x", padx=6, pady=(0, 6))

        def say(_=None):
            x = e.get().strip()
            e.delete(0, "end")
            p = x.split(" ", 2)
            if p[0] == "/w" and len(p) == 3:
                n.send({"t": "dm", "to": p[1], "x": p[2]})
            elif x:
                n.send({"t": "chat", "x": x})

        e.bind("<Return>", say)
        s.side_online = tk.Frame(body, bg=PANEL, width=240)
        s.side_online.pack(side="right", fill="y", padx=(8, 0))
        s.side_online.pack_propagate(False)
        s.render_online()
        s.refresh_chat()

    def online_login(s):
        f = tk.Frame(s.c, bg=PANEL, padx=20, pady=16)
        f.pack(anchor="w")
        s.lab(f, "Запусти bloxly_server.py и подключись:", bg=PANEL).pack(anchor="w", pady=(0, 8))
        es = [tk.Entry(f, width=28) for _ in range(3)]
        es[0].insert(0, s.db.get("host", "127.0.0.1:8765"))
        es[2].config(show="•")
        for x, t in zip(es, ("Сервер host:порт", "Имя", "Пароль")):
            s.lab(f, t, fg=MUT, bg=PANEL).pack(anchor="w")
            x.pack(pady=(0, 6))

        def enter(reg):
            try:
                host, _, port = es[0].get().partition(":")
                net = Net()
                net.connect(host or "127.0.0.1", int(port or 8765))
            except Exception as ex:
                return messagebox.showerror("BLOXLY", f"Не удалось подключиться: {ex}")
            s.db["host"] = es[0].get()
            s.save()
            s.net = net
            net.send({"t": "login", "n": es[1].get().strip(), "p": es[2].get(), "reg": reg})

        r = tk.Frame(f, bg=PANEL)
        r.pack(fill="x", pady=(6, 0))
        s.b(r, "Войти", lambda: enter(False), ACC).pack(side="left")
        s.b(r, "Регистрация", lambda: enter(True)).pack(side="left", padx=6)

    def refresh_chat(s):
        try:
            b = s.chat_box
            b.config(state="normal")
            b.delete("1.0", "end")
            b.insert("end", "\n".join(s.net.log))
            b.config(state="disabled")
            b.see("end")
        except (AttributeError, tk.TclError):
            pass

    def render_online(s):
        try:
            p = s.side_online
            s.clear(p)
        except (AttributeError, tk.TclError):
            return
        n = s.net

        def head(t):
            s.lab(p, t, ("Arial", 12, "bold"), bg=PANEL).pack(anchor="w", padx=8, pady=(10, 2))

        head(f"В сети ({len(n.online)})")
        s.lab(p, ", ".join(n.online) or "—", fg=MUT, bg=PANEL).pack(anchor="w", padx=8)
        head("Друзья")
        for f in n.fr:
            r = tk.Frame(p, bg=PANEL)
            r.pack(fill="x", padx=8)
            s.lab(r, ("🟢 " if f in n.online else "⚪ ") + f, bg=PANEL).pack(side="left")
            s.b(r, "✕", lambda f=f: n.send({"t": "frd", "n": f})).pack(side="right")
        if n.inc:
            head("Запросы")
            for f in n.inc:
                r = tk.Frame(p, bg=PANEL)
                r.pack(fill="x", padx=8)
                s.lab(r, f, bg=PANEL).pack(side="left")
                s.b(r, "Принять", lambda f=f: n.send({"t": "fra", "n": f}), ACC).pack(side="right")
        e = tk.Entry(p)
        e.pack(fill="x", padx=8, pady=(12, 2))
        s.b(p, "Добавить в друзья", lambda: (n.send({"t": "fr", "n": e.get().strip()}), e.delete(0, "end"))).pack(padx=8)

    def arena(s):
        n = s.net
        w = tk.Toplevel(s, bg="#000")
        w.title("Арена — собирай монеты (WASD / стрелки)")
        cv = tk.Canvas(w, width=800, height=500, bg="#120a22", highlightthickness=0)
        cv.pack()
        for g in range(0, 801, 50):
            cv.create_line(g, 0, g, 500, fill="#1e1236")
        for g in range(0, 501, 50):
            cv.create_line(0, g, 800, g, fill="#1e1236")
        KEYS = {"w": "w cyrillic_tse up", "a": "a cyrillic_ef left", "s": "s cyrillic_yeru down", "d": "d cyrillic_ve right"}
        st = {"x": 400., "y": 250., "k": set(), "sh": 0., "pa": [], "fl": [], "tr": [], "t": 0, "vis": {}}
        w.bind("<KeyPress>", lambda e: st["k"].add(e.keysym.lower()))
        w.bind("<KeyRelease>", lambda e: st["k"].discard(e.keysym.lower()))
        w.focus_force()
        n.ev.clear()
        n.send({"t": "join"})

        def held(d):
            return any(x in st["k"] for x in KEYS[d].split())

        def burst(x, y, col, cnt):
            for _ in range(cnt):
                a, v = random.uniform(0, 6.28), random.uniform(1, 5)
                st["pa"].append([x, y, math.cos(a) * v, math.sin(a) * v, 22, col])

        def frame():
            if not w.winfo_exists():
                n.send({"t": "leave"})
                return
            st["t"] += 1
            t = st["t"]
            dx, dy = held("d") - held("a"), held("s") - held("w")
            if dx or dy:
                l = math.hypot(dx, dy)
                st["x"] = min(780, max(20, st["x"] + dx / l * 4.2))
                st["y"] = min(480, max(20, st["y"] + dy / l * 4.2))
                st["tr"].append((st["x"], st["y"]))
            st["tr"] = st["tr"][-12:]
            if t % 3 == 0:
                n.send({"t": "mv", "x": round(st["x"]), "y": round(st["y"])})
            while n.ev:
                e = n.ev.pop(0)
                mine = e["n"] == n.name
                burst(e["x"], e["y"], "#ffd43b" if mine else "#a78bfa", 16 if mine else 8)
                if mine:
                    st["sh"] = 7
                    st["fl"].append([e["x"], e["y"], 30, "+1 R$"])
            cv.delete("d")
            sh = st["sh"]
            st["sh"] *= .85
            ox, oy = random.uniform(-sh, sh), random.uniform(-sh, sh)

            def dot(x, y, r, **k):
                cv.create_oval(x - r + ox, y - r + oy, x + r + ox, y + r + oy, tags="d", **k)

            for x, y in n.coins:
                r = 9 + 2 * math.sin(t / 6 + x)
                dot(x, y, r + 5, fill="#4a3a00", outline="")
                dot(x, y, r, fill="#ffd43b", outline="#fff2a8", width=2)
            for i, (x, y) in enumerate(st["tr"]):
                dot(x, y, 3 + i, fill="#6d28d9", outline="", stipple="gray50")
            for nm, p in n.world.items():
                if nm == n.name:
                    continue
                vx, vy = st["vis"].get(nm, (p["x"], p["y"]))
                vx += (p["x"] - vx) * .25
                vy += (p["y"] - vy) * .25
                st["vis"][nm] = (vx, vy)
                dot(vx, vy, 16, fill=p["c"], outline="#fff")
                cv.create_text(vx + ox, vy - 26 + oy, text=f"{nm} · {p['s']}", fill="#ddd", font=("Arial", 9), tags="d")
            me = n.world.get(n.name, {})
            dot(st["x"], st["y"], 18, fill=me.get("c", ACC), outline="#fff", width=3)
            cv.create_text(st["x"] + ox, st["y"] - 28 + oy, text=f"{n.name} · {me.get('s', 0)}", fill="#fff",
                           font=("Arial", 10, "bold"), tags="d")
            for pa in st["pa"]:
                pa[0] += pa[2]; pa[1] += pa[3]; pa[3] += .15; pa[4] -= 1
                dot(pa[0], pa[1], 3, fill=pa[5], outline="")
            st["pa"] = [p for p in st["pa"] if p[4] > 0]
            for f in st["fl"]:
                f[1] -= 1.2; f[2] -= 1
                cv.create_text(f[0] + ox, f[1] + oy, text=f[3], fill="#ffd43b", font=("Arial", 14, "bold"), tags="d")
            st["fl"] = [f for f in st["fl"] if f[2] > 0]
            top = sorted(n.world.items(), key=lambda kv: -kv[1]["s"])[:5]
            cv.create_text(790, 10, anchor="ne", justify="right", fill="#fff", font=("Arial", 11, "bold"), tags="d",
                           text="🏆 Топ\n" + "\n".join(f"{i + 1}. {k} — {v['s']}" for i, (k, v) in enumerate(top)))
            cv.create_text(10, 10, anchor="nw", text=f"R$ {n.rb}", fill="#ffd43b", font=("Arial", 14, "bold"), tags="d")
            w.after(16, frame)

        frame()

    # ---------- игры
    def zomb(s):
        w = tk.Toplevel(s, bg=PANEL)
        w.title("Выживание в зомби")
        cv = tk.Canvas(w, width=420, height=300, bg="#1f2a1f", highlightthickness=0)
        cv.pack(padx=8, pady=8)
        st = {"n": 0, "t": 20}
        lab = s.lab(w, "Время: 20 · Убито: 0", bg=PANEL)
        lab.pack(pady=(0, 8))

        def spawn():
            if st["t"] <= 0 or not w.winfo_exists():
                return
            z = cv.create_text(random.randint(20, 400), random.randint(20, 280), text="🧟", font=("Arial", 32))

            def hit(_):
                st["n"] += 1
                x, y = cv.coords(z)
                cv.delete(z)
                pop = cv.create_text(x, y, text="💥 +1", font=("Arial", 22, "bold"), fill="#ffd43b")
                cv.after(180, lambda: cv.delete(pop))

            cv.tag_bind(z, "<Button-1>", hit)
            cv.after(1100, lambda: cv.delete(z))
            w.after(450, spawn)

        def tick():
            if not w.winfo_exists():
                return
            st["t"] -= 1
            lab.config(text=f"Время: {st['t']} · Убито: {st['n']}")
            if st["t"] <= 0:
                s.me["rb"] += st["n"]
                s.save()
                messagebox.showinfo("Игра окончена", f"Убито: {st['n']}\n+{st['n']} R$")
                w.destroy()
            else:
                w.after(1000, tick)

        spawn()
        w.after(1000, tick)

    def clicker(s):
        k = s.me["ck"]
        w = tk.Toplevel(s, bg=PANEL)
        w.title("Пиццерия тайкун")
        info = s.lab(w, "", ("Arial", 12), bg=PANEL)
        info.pack(pady=8, padx=10)

        def up():
            info.config(text=f"🍕 {int(k['n'])} · клик +{k['pw']} · печей {k['au']}\n"
                             f"Сильный клик: {20 * k['pw']} · Печь: {50 * (k['au'] + 1)}")
            s.save()

        def click():
            k["n"] += k["pw"]
            up()

        def buy(cost, key):
            if k["n"] >= cost:
                k["n"] -= cost
                k[key] += 1
            up()

        def sell():
            if k["n"] >= 200:
                k["n"] -= 200
                s.me["rb"] += 5
            up()

        def auto():
            if w.winfo_exists():
                k["n"] += k["au"]
                up()
                w.after(1000, auto)

        tk.Button(w, text="🍕", font=("Arial", 64), command=click, bg=PANEL, relief="flat").pack()
        s.b(w, "Сильный клик", lambda: buy(20 * k["pw"], "pw")).pack(fill="x", padx=10, pady=2)
        s.b(w, "Купить печь", lambda: buy(50 * (k["au"] + 1), "au")).pack(fill="x", padx=10, pady=2)
        s.b(w, "Продать 200 🍕 за 5 R$", sell, ACC).pack(fill="x", padx=10, pady=(2, 10))
        up()
        auto()


if __name__ == "__main__":
    App().mainloop()
