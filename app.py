"""
StudyOS 🌸 — Notion-style study workspace
Stack: Python, Streamlit (>=1.40), SQLite3, Groq API (llama-3.1-8b-instant)

Run:      streamlit run app.py
API key:  .streamlit/secrets.toml  ->  GROQ_API_KEY = "gsk_..."
"""

import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="StudyOS 🌸", page_icon="🌸", layout="wide",
                   initial_sidebar_state="auto")

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------
DB_PATH = "studyos.db"
TZ = ZoneInfo("Africa/Cairo")
MODEL = "llama-3.1-8b-instant"

DAYS = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
KINDS = ["🏫 School", "📚 Tutoring", "🍵 Other"]
HABITS = ["💧 Drink Water", "🤲 Pray", "🌙 Sleep Early"]
PAGES = ["🏠 Dashboard", "📅 Schedule Setup", "🤖 AI Bestie",
         "⏳ Focus Room", "☁️ Brain Dump", "🚨 SOS Exam Mode"]


def now() -> datetime:
    return datetime.now(TZ)


def today_iso() -> str:
    return now().strftime("%Y-%m-%d")


def today_name() -> str:
    return now().strftime("%A")


# ----------------------------------------------------------------------------
# CSS — Notion-style cards (st.container(key="card_*") => .st-key-card_*)
# ----------------------------------------------------------------------------
BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@400;500;600;700&display=swap');
:root { color-scheme: light; }
html, body, .stApp, [class*="css"], button, input, textarea, select {
    font-family: 'Quicksand', sans-serif !important;
}
.stApp { background: #FAF9F6 !important; }
.stApp, .stApp p, .stApp span, .stApp label, .stApp li, .stApp div { color: #4A4A4A; }
h1, h2, h3, h4, h5 { color: #6B4E71 !important; font-weight: 700 !important; }

/* Hide Streamlit chrome (header kept transparent so the sidebar toggle works on phones) */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stAppDeployButton"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 1.6rem; padding-bottom: 4rem; max-width: 1150px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #E6E6FA !important; border-right: 2px solid #FFD1DC; }
[data-testid="stSidebar"] .stRadio label p { font-weight: 600; }

/* ===== Notion cards ===== */
[class*="st-key-card"] {
    background: #FFFFFF; border-radius: 15px; padding: 20px 22px; margin-bottom: 14px;
    border: 1px solid #F1E4EA; box-shadow: 0 4px 16px rgba(160, 120, 150, 0.14);
}
.card-title { font-weight: 700; font-size: 1.05rem; color: #6B4E71; margin: 0 0 10px 0; }
.hero {
    background: linear-gradient(135deg, #FFD1DC 0%, #E6E6FA 100%);
    border-radius: 15px; padding: 22px 26px; margin-bottom: 16px;
    box-shadow: 0 6px 18px rgba(160, 120, 150, 0.22);
}
.hero h2 { margin: 0 0 4px 0; font-size: 1.6rem; }
.hero p { margin: 0; font-weight: 500; }

/* Timeline rows */
.slot {
    display: flex; gap: 12px; align-items: center; padding: 10px 12px; margin: 8px 0;
    border-radius: 12px; background: #FAF9F6; border-left: 5px solid #FFD1DC;
}
.slot.tutor { border-left-color: #C9B6F2; }
.slot.other { border-left-color: #BDE6D3; }
.slot .t { font-weight: 700; color: #6B4E71; min-width: 104px; font-size: .92rem; }
.slot .n { font-weight: 600; flex: 1; }
.pill { background: #E6E6FA; border-radius: 999px; padding: 2px 11px; font-size: .78rem;
        font-weight: 600; color: #6B4E71; white-space: nowrap; }

/* Todos */
.todo { font-weight: 600; padding-top: 7px; line-height: 1.3; }
.todo.done { text-decoration: line-through; color: #B5AEB3 !important; font-weight: 500; }

/* Inputs */
.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div, .stMultiSelect div[data-baseweb="select"] > div,
.stTimeInput input {
    border-radius: 12px !important; background: #FFFFFF !important; color: #4A4A4A !important;
    border: 1.5px solid #FFD1DC !important;
}
.stTextArea textarea { min-height: 170px; }
[data-testid="stDataFrame"] { border-radius: 15px; overflow: hidden;
    box-shadow: 0 3px 12px rgba(160, 120, 150, 0.14); }
[data-testid="stChatMessage"] { background: #FAF9F6; border-radius: 15px; padding: 10px 14px; }

/* Buttons */
.stButton > button, .stFormSubmitButton > button {
    background: #FFD1DC; color: #6B4E71 !important; border: none; border-radius: 12px;
    font-weight: 700; padding: .5rem 1rem; box-shadow: 0 2px 8px rgba(255, 160, 190, .35);
    transition: all .15s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #FFC0D0; transform: translateY(-1px);
}
.stButton > button p { color: #6B4E71 !important; }

/* Todo check buttons: small, round, lavender */
[class*="st-key-todo_tog"] button, [class*="st-key-todo_del"] button {
    background: #E6E6FA; border-radius: 50%; padding: 0; min-height: 38px; width: 38px;
    box-shadow: none;
}
[class*="st-key-todo_del"] button { background: transparent; opacity: .55; }

/* Habit pills */
[class*="st-key-habit_"] button {
    width: 100%; border-radius: 999px; background: #FFFFFF; border: 2px dashed #E6E6FA;
    padding: .7rem 1rem; font-size: 1rem; box-shadow: none;
}
[class*="st-key-habit_"] button:hover { border-color: #FFD1DC; background: #FFF5F8; }

/* Mobile */
@media (max-width: 640px) {
    .block-container { padding: 1rem .7rem 4rem .7rem; }
    [class*="st-key-card"] { padding: 14px 14px; }
    .hero { padding: 16px; } .hero h2 { font-size: 1.25rem; }
    .slot { flex-wrap: wrap; gap: 4px; } .slot .t { min-width: 0; }
    .stButton > button, .stFormSubmitButton > button { width: 100%; }
}
</style>
"""
st.markdown(BASE_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Database
# ----------------------------------------------------------------------------
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS weekly_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
            title TEXT NOT NULL, kind TEXT NOT NULL DEFAULT '🏫 School'
        );
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, name TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0,
            UNIQUE(date, name)
        );
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'todo',   -- 'todo' | 'goal'
            text TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, content TEXT NOT NULL, ai_reply TEXT
        );
        """)


# schedule
def add_slot(day, start, end, title, kind):
    with db() as c:
        c.execute("INSERT INTO weekly_schedule (day,start_time,end_time,title,kind) VALUES (?,?,?,?,?)",
                  (day, start, end, title, kind))


def update_slot(sid, day, start, end, title, kind):
    with db() as c:
        c.execute("UPDATE weekly_schedule SET day=?,start_time=?,end_time=?,title=?,kind=? WHERE id=?",
                  (day, start, end, title, kind, sid))


def delete_slot(sid):
    with db() as c:
        c.execute("DELETE FROM weekly_schedule WHERE id=?", (sid,))


def get_schedule(day=None):
    with db() as c:
        if day:
            rows = c.execute("SELECT * FROM weekly_schedule WHERE day=? ORDER BY start_time", (day,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM weekly_schedule").fetchall()
    rows = [dict(r) for r in rows]
    if not day:
        rows.sort(key=lambda r: (DAYS.index(r["day"]) if r["day"] in DAYS else 99, r["start_time"]))
    return rows


# goal + todos
def get_goal(d):
    with db() as c:
        r = c.execute("SELECT text FROM todos WHERE date=? AND kind='goal'", (d,)).fetchone()
    return r["text"] if r else ""


def set_goal(d, text):
    with db() as c:
        c.execute("DELETE FROM todos WHERE date=? AND kind='goal'", (d,))
        if text.strip():
            c.execute("INSERT INTO todos (date,kind,text,done) VALUES (?,?,?,0)", (d, "goal", text.strip()))


def get_todos(d):
    with db() as c:
        rows = c.execute("SELECT * FROM todos WHERE date=? AND kind='todo' ORDER BY id", (d,)).fetchall()
    return [dict(r) for r in rows]


def add_todo(d, text):
    with db() as c:
        c.execute("INSERT INTO todos (date,kind,text,done) VALUES (?,?,?,0)", (d, "todo", text.strip()))


def toggle_todo(tid):
    with db() as c:
        c.execute("UPDATE todos SET done = 1 - done WHERE id=?", (tid,))


def delete_todo(tid):
    with db() as c:
        c.execute("DELETE FROM todos WHERE id=?", (tid,))


# habits
def get_habits(d):
    with db() as c:
        rows = c.execute("SELECT name, done FROM habits WHERE date=?", (d,)).fetchall()
    state = {h: False for h in HABITS}
    state.update({r["name"]: bool(r["done"]) for r in rows})
    return state


def set_habit(d, name, done):
    with db() as c:
        c.execute("INSERT INTO habits (date,name,done) VALUES (?,?,?) "
                  "ON CONFLICT(date,name) DO UPDATE SET done=excluded.done", (d, name, int(done)))


# journal
def add_journal(content, reply):
    with db() as c:
        c.execute("INSERT INTO journal (created_at,content,ai_reply) VALUES (?,?,?)",
                  (now().strftime("%Y-%m-%d %H:%M"), content, reply))


def get_journal(limit=12):
    with db() as c:
        rows = c.execute("SELECT * FROM journal ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def delete_journal(jid):
    with db() as c:
        c.execute("DELETE FROM journal WHERE id=?", (jid,))


init_db()

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
for k, v in {"chat_history": [], "dump_reply": "", "sos_plan": "", "balloons": False}.items():
    st.session_state.setdefault(k, v)


# ----------------------------------------------------------------------------
# Time maths (done in Python, never by the LLM)
# ----------------------------------------------------------------------------
def to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def fmt_min(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def free_slots_today(min_len=20, day_start="07:00", day_end="22:30"):
    """Free windows from NOW until day_end, between today's fixed schedule items (Cairo time)."""
    cur = now()
    pointer = max(to_min(day_start), cur.hour * 60 + cur.minute)
    end = to_min(day_end)
    busy = sorted((to_min(r["start_time"]), to_min(r["end_time"])) for r in get_schedule(today_name()))
    slots = []
    for b_start, b_end in busy:
        if b_end <= pointer:
            continue
        if min(b_start, end) - pointer >= min_len:
            slots.append((pointer, min(b_start, end)))
        pointer = max(pointer, b_end)
    if end - pointer >= min_len:
        slots.append((pointer, end))
    return slots


# ----------------------------------------------------------------------------
# Groq
# ----------------------------------------------------------------------------
def get_api_key():
    try:
        key = st.secrets["GROQ_API_KEY"]
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GROQ_API_KEY")


def groq_ready() -> bool:
    if get_api_key():
        return True
    st.error("🌸 I can't find the Groq API key yet. Add `GROQ_API_KEY = \"your_key\"` to "
             "`.streamlit/secrets.toml` (or the Secrets box on Streamlit Cloud) and refresh 🤍")
    return False


def ask_groq(messages, temperature=0.7, max_tokens=1200) -> str:
    try:
        from groq import Groq
    except ImportError:
        return "⚠️ The `groq` package isn't installed. Run `pip install groq` 🌸"
    try:
        client = Groq(api_key=get_api_key())
        resp = client.chat.completions.create(model=MODEL, messages=messages,
                                              temperature=temperature, max_tokens=max_tokens)
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return (f"⚠️ I couldn't reach my brain just now ☁️ ({type(e).__name__}). "
                f"Check your API key / internet and try again 🤍")


# ----------------------------------------------------------------------------
# Small UI helpers
# ----------------------------------------------------------------------------
def card_title(text):
    st.markdown(f'<div class="card-title">{text}</div>', unsafe_allow_html=True)


def slot_html(r) -> str:
    cls = "tutor" if "Tutoring" in r["kind"] else ("other" if "Other" in r["kind"] else "")
    return (f'<div class="slot {cls}"><div class="t">{r["start_time"]} – {r["end_time"]}</div>'
            f'<div class="n">{r["title"]}</div><span class="pill">{r["kind"]}</span></div>')


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ----------------------------------------------------------------------------
# 1. Dashboard
# ----------------------------------------------------------------------------
def page_dashboard():
    d = today_iso()
    st.markdown(
        f'<div class="hero"><h2>Good morning! Let\'s make today productive ✨</h2>'
        f'<p>🌸 {now().strftime("%A, %d %B %Y")}</p></div>', unsafe_allow_html=True)

    left, right = st.columns([3, 2], gap="medium")

    # ---------------- LEFT: timeline + todos ----------------
    with left:
        with st.container(key="card_timeline"):
            card_title("🎀 Today's Timeline")
            rows = get_schedule(today_name())
            if rows:
                st.markdown("".join(slot_html(r) for r in rows), unsafe_allow_html=True)
            else:
                st.caption("☁️ Nothing scheduled today. Add classes in 📅 Schedule Setup.")

        with st.container(key="card_todos"):
            card_title("🌷 To-Do List")
            with st.form("todo_form", clear_on_submit=True, border=False):
                c1, c2 = st.columns([5, 1.4])
                new_task = c1.text_input("New task", label_visibility="collapsed",
                                         placeholder="Add a little task ✨")
                added = c2.form_submit_button("Add")
            if added and new_task.strip():
                add_todo(d, new_task)
                st.rerun()

            todos = get_todos(d)
            if not todos:
                st.caption("No tasks yet — add your first one 🌸")
            for t in todos:
                c1, c2, c3 = st.columns([1, 7, 1], vertical_alignment="center")
                if c1.button("☑️" if t["done"] else "⬜", key=f"todo_tog_{t['id']}"):
                    toggle_todo(t["id"])
                    st.rerun()
                c2.markdown(f'<div class="todo {"done" if t["done"] else ""}">{esc(t["text"])}</div>',
                            unsafe_allow_html=True)
                if c3.button("✕", key=f"todo_del_{t['id']}"):
                    delete_todo(t["id"])
                    st.rerun()
            if todos:
                done = sum(t["done"] for t in todos)
                st.progress(done / len(todos), text=f"{done}/{len(todos)} done 🤍")

    # ---------------- RIGHT: goal + habits ----------------
    with right:
        with st.container(key="card_goal"):
            card_title("🎯 Daily Goal")
            gk = f"goal_{d}"
            if gk not in st.session_state:
                st.session_state[gk] = get_goal(d)
            st.text_input("Goal", key=gk, label_visibility="collapsed",
                          placeholder="The ONE thing I want to finish today…",
                          on_change=lambda: set_goal(d, st.session_state[gk]))
            if st.session_state[gk].strip():
                st.caption("Saved ✨ You've got this!")

        with st.container(key="card_habits"):
            card_title("💧 Habit Tracker")
            state = get_habits(d)

            # colour done pills pink (dynamic CSS, since pills are styled buttons)
            css = "".join(
                f'.st-key-habit_{i} button{{background:#FFD1DC !important;border:2px solid #FFB6C9 !important;'
                f'box-shadow:0 3px 10px rgba(255,160,190,.4) !important;}}'
                for i, h in enumerate(HABITS) if state[h])
            if css:
                st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

            for i, h in enumerate(HABITS):
                if st.button(f"{h}  {'✓' if state[h] else ''}".strip(), key=f"habit_{i}"):
                    set_habit(d, h, not state[h])
                    if all({**state, h: not state[h]}.values()):
                        st.session_state["balloons"] = True
                    st.rerun()

            n = sum(state.values())
            st.progress(n / len(HABITS), text=f"{n}/{len(HABITS)} habits 🌸")

    if st.session_state["balloons"]:
        st.session_state["balloons"] = False
        st.balloons()


# ----------------------------------------------------------------------------
# 2. Schedule Setup
# ----------------------------------------------------------------------------
def page_schedule():
    st.markdown("## 📅 Schedule Setup")
    st.caption("Your fixed weekly school hours and tutoring sessions 🌸")
    rows = get_schedule()

    left, right = st.columns([2, 3], gap="medium")

    with left:
        with st.container(key="card_add"):
            card_title("✨ Add a session")
            with st.form("add_slot", clear_on_submit=True, border=False):
                title = st.text_input("Title", placeholder="School / Math with Ms. Nour")
                days = st.multiselect("Day(s)", DAYS,
                                      default=[today_name()] if today_name() in DAYS else [])
                kind = st.selectbox("Type", KINDS)
                c1, c2 = st.columns(2)
                start = c1.time_input("Start", value=dtime(8, 0), step=300)
                end = c2.time_input("End", value=dtime(14, 0), step=300)
                ok = st.form_submit_button("Add to schedule 🌸")
            if ok:
                if not title.strip() or not days:
                    st.warning("Add a title and at least one day 🤍")
                elif end <= start:
                    st.warning("End time must be after the start time ⏰")
                else:
                    for dname in days:
                        add_slot(dname, start.strftime("%H:%M"), end.strftime("%H:%M"), title.strip(), kind)
                    st.rerun()

    with right:
        with st.container(key="card_table"):
            card_title("🎀 My Weekly Schedule")
            if rows:
                df = pd.DataFrame(rows)[["id", "day", "start_time", "end_time", "title", "kind"]]
                st.dataframe(
                    df, hide_index=True, use_container_width=True,
                    column_config={"id": st.column_config.NumberColumn("ID", width="small"),
                                   "day": "Day", "start_time": "Start", "end_time": "End",
                                   "title": "Session", "kind": "Type"})
                n_t = sum("Tutoring" in r["kind"] for r in rows)
                st.caption(f"📚 {n_t} tutoring session(s) · 🏫 {len(rows) - n_t} other")
            else:
                st.caption("☁️ Nothing here yet — add your first session!")

    if rows:
        with st.container(key="card_edit"):
            card_title("✏️ Edit or delete")
            labels = {r["id"]: f'{r["day"][:3]} {r["start_time"]}-{r["end_time"]} · {r["title"]}' for r in rows}
            sel = st.selectbox("Choose a session", list(labels), format_func=lambda i: labels[i])
            r = next(x for x in rows if x["id"] == sel)
            with st.form(f"edit_{sel}", border=False):
                c1, c2, c3 = st.columns(3)
                e_title = c1.text_input("Title", value=r["title"])
                e_day = c2.selectbox("Day", DAYS, index=DAYS.index(r["day"]) if r["day"] in DAYS else 0)
                e_kind = c3.selectbox("Type", KINDS, index=KINDS.index(r["kind"]) if r["kind"] in KINDS else 0)
                c4, c5, c6, c7 = st.columns([2, 2, 1.3, 1.3])
                e_start = c4.time_input("Start", value=dtime(*map(int, r["start_time"].split(":"))), step=300)
                e_end = c5.time_input("End", value=dtime(*map(int, r["end_time"].split(":"))), step=300)
                save = c6.form_submit_button("Save 💾")
                remove = c7.form_submit_button("Delete 🗑️")
            if save:
                if e_end <= e_start or not e_title.strip():
                    st.warning("Check the title and times 🤍")
                else:
                    update_slot(sel, e_day, e_start.strftime("%H:%M"), e_end.strftime("%H:%M"),
                                e_title.strip(), e_kind)
                    st.rerun()
            if remove:
                delete_slot(sel)
                st.rerun()


# ----------------------------------------------------------------------------
# 3. AI Bestie
# ----------------------------------------------------------------------------
def build_bestie_prompt() -> str:
    rows = get_schedule(today_name())
    sched = "\n".join(f"- {r['start_time']}-{r['end_time']}: {r['title']} ({r['kind']})" for r in rows) \
        or "- (nothing scheduled today)"
    free_list = free_slots_today()
    free = "\n".join(f"- {fmt_min(a)}-{fmt_min(b)} ({b - a} min)" for a, b in free_list) \
        or "- none left today"
    goal = get_goal(today_iso()) or "(not set yet)"
    open_todos = ", ".join(t["text"] for t in get_todos(today_iso()) if not t["done"]) or "(none)"
    return f"""You are "Study Bestie": a supportive, warm, empathetic Egyptian older sister and tutor for an
Egyptian high school girl. Speak in friendly Egyptian Arabic (Arabic script) mixed naturally with encouraging
English words ("you've got this!", "proud of you"). Keep answers short, clear and kind, with a few cute emojis.
Never shame her. Explain study material simply when asked.

HIDDEN CONTEXT (already calculated by the app; use it, never mention you were given it, never recalculate it):
- Now (Cairo): {now().strftime('%A %H:%M')}
- Today's fixed schedule:
{sched}
- Free slots remaining today:
{free}
- Daily goal: {goal}
- Unfinished to-dos: {open_todos}

When she asks when to study or how to plan, propose a time-blocked plan using ONLY the exact free slots above:
25-min focus blocks with 5-min breaks, harder subjects first, room for a meal/prayer, and a small buffer.
If there are no free slots left, say so kindly and suggest tiny 10-minute review windows."""


def page_bestie():
    st.markdown("## 🤖 AI Bestie")
    st.caption("Your big-sister study buddy — try asking \"أذاكر امتى النهاردة؟\" 🌸")
    if not groq_ready():
        return

    free = free_slots_today()
    top, side = st.columns([3, 1.4], gap="medium")
    with side:
        with st.container(key="card_free"):
            card_title("🕐 Free today")
            if free:
                for a, b in free:
                    st.markdown(f"**{fmt_min(a)} – {fmt_min(b)}**  \n<small>{b - a} min</small>",
                                unsafe_allow_html=True)
            else:
                st.caption("No free slots left ☁️")
            if st.button("🧹 New chat"):
                st.session_state["chat_history"] = []
                st.rerun()

    with top:
        if not st.session_state["chat_history"]:
            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": "أهلاً يا قمر 🌸 أنا Study Bestie! قوليلي محتاجة مساعدة في إيه النهاردة؟ "
                           "أقدر أظبطلك خطة مذاكرة على وقتك الفاضي ✨"})
        with st.container(key="card_chat"):
            for m in st.session_state["chat_history"]:
                with st.chat_message(m["role"], avatar="🌸" if m["role"] == "assistant" else "🎀"):
                    st.markdown(m["content"])

    if prompt := st.chat_input("اكتبي سؤالك هنا… 🤍"):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        msgs = [{"role": "system", "content": build_bestie_prompt()}] + st.session_state["chat_history"][-14:]
        with st.spinner("بفكر… ☁️"):
            reply = ask_groq(msgs, temperature=0.7)
        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
        st.rerun()


# ----------------------------------------------------------------------------
# 4. Focus Room
# ----------------------------------------------------------------------------
POMODORO_HTML = """
<div id="app" style="font-family:'Quicksand',sans-serif;text-align:center;padding:16px 8px;
 background:linear-gradient(135deg,#FFE3EA,#E6E6FA);border-radius:15px;position:relative;overflow:hidden;color:#4A4A4A">
 <link href="https://fonts.googleapis.com/css2?family=Quicksand:wght@500;700&display=swap" rel="stylesheet">
 <div id="mode" style="font-weight:700;color:#6B4E71;font-size:1.05rem">🍅 Focus time</div>
 <div style="position:relative;width:230px;height:230px;margin:10px auto">
  <svg viewBox="0 0 120 120" width="230" height="230" style="transform:rotate(-90deg)">
   <circle cx="60" cy="60" r="52" fill="#fff" stroke="#FFF0F4" stroke-width="9"/>
   <circle id="ring" cx="60" cy="60" r="52" fill="none" stroke="#FFB6C9" stroke-width="9"
     stroke-linecap="round" stroke-dasharray="326.7" stroke-dashoffset="0" style="transition:stroke-dashoffset 1s linear"/>
  </svg>
  <div id="time" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
    font-size:2.6rem;font-weight:700;color:#6B4E71">25:00</div>
 </div>
 <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:8px">
  <button class="b" onclick="setMode(25,'🍅 Focus time')">Focus (25 min)</button>
  <button class="b" onclick="setMode(5,'🍵 Short break')">Break (5 min)</button>
 </div>
 <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">
  <button class="b main" id="go" onclick="toggle()">▶ Start</button>
  <button class="b" onclick="resetT()">↺ Reset</button>
 </div>
 <div id="msg" style="margin-top:12px;font-weight:700;color:#6B4E71;min-height:26px"></div>
 <div id="sess" style="font-size:.85rem;opacity:.8">Focus sessions done: 0 🌸</div>
</div>
<style>
 .b{font-family:'Quicksand',sans-serif;font-weight:700;border:none;border-radius:12px;padding:10px 16px;
    background:#fff;color:#6B4E71;box-shadow:0 3px 10px rgba(180,140,170,.3);cursor:pointer;font-size:.95rem}
 .b.main{background:#FFB6C9}
 .fall{position:absolute;top:-30px;font-size:1.6rem;animation:fall 3.2s linear forwards;pointer-events:none}
 @keyframes fall{to{transform:translateY(560px) rotate(360deg);opacity:.2}}
</style>
<script>
 let total=1500,left=total,timer=null,sessions=0,isFocus=true;
 const C=326.7,$=id=>document.getElementById(id);
 function draw(){const m=String(Math.floor(left/60)).padStart(2,'0'),s=String(left%60).padStart(2,'0');
   $('time').textContent=m+':'+s; $('ring').style.strokeDashoffset=C*(1-left/total);}
 function setMode(min,label){clearInterval(timer);timer=null;total=left=min*60;isFocus=min>=25;
   $('mode').textContent=label;$('go').textContent='▶ Start';$('msg').textContent='';draw();}
 function toggle(){
   if(timer){clearInterval(timer);timer=null;$('go').textContent='▶ Resume';return;}
   if(left<=0)left=total; $('msg').textContent='';$('go').textContent='⏸ Pause';
   const end=Date.now()+left*1000;
   timer=setInterval(()=>{left=Math.max(0,Math.round((end-Date.now())/1000));draw();
     if(left<=0){clearInterval(timer);timer=null;done();}},250);}
 function resetT(){clearInterval(timer);timer=null;left=total;$('go').textContent='▶ Start';$('msg').textContent='';draw();}
 function beep(){try{const a=new (window.AudioContext||window.webkitAudioContext)();
   [660,880,1040].forEach((f,i)=>{const o=a.createOscillator(),g=a.createGain();o.frequency.value=f;
     o.connect(g);g.connect(a.destination);g.gain.setValueAtTime(.15,a.currentTime+i*.25);
     g.gain.exponentialRampToValueAtTime(.001,a.currentTime+i*.25+.22);
     o.start(a.currentTime+i*.25);o.stop(a.currentTime+i*.25+.25);});}catch(e){}}
 function done(){$('go').textContent='▶ Start';beep();
   if(isFocus){sessions++;$('sess').textContent='Focus sessions done: '+sessions+' 🌸';
     $('msg').textContent='🎉 Amazing job! Session complete — time for a little break 🍵';}
   else{$('msg').textContent='☀️ Break over! Ready for another round? 💪';}
   const em=['🌸','✨','🎀','🤍','⭐','💖'];
   for(let i=0;i<28;i++){const e=document.createElement('div');e.className='fall';e.textContent=em[i%em.length];
     e.style.left=Math.random()*95+'%';e.style.animationDelay=Math.random()*1.2+'s';
     $('app').appendChild(e);setTimeout(()=>e.remove(),5000);}
   if(navigator.vibrate)navigator.vibrate([200,100,200]);}
 draw();
</script>
"""


def page_focus():
    st.markdown("## ⏳ Cozy Focus Room")
    st.caption("Pick a mode, press start, and let the ring do its thing 🍵")
    timer_col, tips_col = st.columns([3, 2], gap="medium")
    with timer_col:
        with st.container(key="card_timer"):
            components.html(POMODORO_HTML, height=520, scrolling=False)
    with tips_col:
        with st.container(key="card_focus_goal"):
            card_title("🎯 Today's goal")
            st.write(get_goal(today_iso()) or "No goal set yet — add one on the Dashboard ✨")
        with st.container(key="card_focus_tips"):
            card_title("🌷 Little tips")
            st.markdown("- 25 min focus → 5 min break → repeat\n- Phone on silent, water nearby 💧\n"
                        "- After 4 rounds, take a longer break 🍵\n- Keep this tab open while the timer runs")


# ----------------------------------------------------------------------------
# 5. Brain Dump
# ----------------------------------------------------------------------------
RISK_PATTERN = re.compile(
    r"(suicid|kill myself|end my life|want to die|wanna die|hurt myself|harm myself|self[- ]?harm|"
    r"don'?t want to (live|be here)|better off dead|"
    r"انتحر|أنتحر|اموت|أموت|عايزة اموت|عايزة أموت|مش عايزة اعيش|مش عايزة أعيش|اؤذي نفسي|أؤذي نفسي|أأذي نفسي|اجرح نفسي|أجرح نفسي)",
    re.IGNORECASE)

CARE_NOTE = ("\n\n🤍 What you're carrying sounds really heavy, and you don't have to hold it alone. "
             "Please talk to an adult you trust right now — a parent, a relative, a teacher or a school counselor — "
             "and tell them how you feel. If you ever feel you might hurt yourself, tell someone near you immediately "
             "or contact your local emergency services.")


def page_dump():
    st.markdown("## ☁️ Brain Dump")
    st.caption("A safe, judgment-free space. Let it all out before you study 🤍")
    left, right = st.columns([3, 2], gap="medium")

    with left:
        with st.container(key="card_dump"):
            card_title("🍵 What's on your mind?")
            with st.form("dump_form", clear_on_submit=True, border=False):
                text = st.text_area("Write here", label_visibility="collapsed",
                                    placeholder="I feel like…")
                send = st.form_submit_button("Let it out 🤍")

        if send:
            if not text.strip():
                st.warning("Write a little something first 🌸")
            elif groq_ready():
                system = (
                    "You are a gentle, empathetic friend for a teenage Egyptian girl who is venting. "
                    "STRICT RULES: ONLY show empathy. NEVER give study advice, productivity tips, schedules, "
                    "solutions or instructions. Do not tell her what to do. Listen, reflect back what she said, and "
                    "validate her feelings (e.g. \"I hear you, take a deep breath, it's okay to feel stressed 🤍\"). "
                    "Reply in warm, simple Egyptian Arabic mixed with a little English, 3-6 short sentences, "
                    "with a few comforting emojis. If she mentions wanting to die or hurting herself, respond with "
                    "deep care and gently encourage her to talk to a trusted adult (a parent, relative, teacher "
                    "or school counselor) right away.")
                with st.spinner("Listening… ☁️"):
                    reply = ask_groq([{"role": "system", "content": system},
                                      {"role": "user", "content": text}], temperature=0.8, max_tokens=500)
                if RISK_PATTERN.search(text):          # deterministic safety net
                    reply += CARE_NOTE
                st.session_state["dump_reply"] = reply
                add_journal(text.strip(), None if reply.startswith("⚠️") else reply)

        if st.session_state["dump_reply"]:
            with st.container(key="card_reply"):
                card_title("🤍 A little hug")
                st.markdown(st.session_state["dump_reply"])

    with right:
        with st.container(key="card_past"):
            card_title("📖 Past entries")
            entries = get_journal()
            if not entries:
                st.caption("Nothing yet ☁️")
            for e in entries:
                with st.expander(f"🌷 {e['created_at']}"):
                    st.write(e["content"])
                    if e["ai_reply"]:
                        st.markdown(f"> 🤍 {e['ai_reply']}")
                    if st.button("Delete 🗑️", key=f"delj_{e['id']}"):
                        delete_journal(e["id"])
                        st.rerun()


# ----------------------------------------------------------------------------
# 6. SOS Exam Mode
# ----------------------------------------------------------------------------
def page_sos():
    st.markdown("## 🚨 SOS Exam Mode")
    st.caption("Deep breath. We're going to get you through this 🤍")
    left, right = st.columns([2, 3], gap="medium")

    with left:
        with st.container(key="card_sos_in"):
            card_title("🚑 Rescue request")
            with st.form("sos_form", border=False):
                subject = st.text_input("Subject", placeholder="e.g. Physics — Electricity")
                hours = st.number_input("Hours left until exam", min_value=0.5, max_value=72.0,
                                        value=6.0, step=0.5)
                extra = st.text_area("(Optional) Topics covered / what scares you most",
                                     height=110, placeholder="Chapter 4, Chapter 5…")
                go = st.form_submit_button("🚨 Rescue me!")

    if go:
        if not subject.strip():
            with left:
                st.warning("Please type the subject 🌸")
        elif groq_ready():
            total_min = int(hours * 60)
            system = (
                "You are a calm, tactical RESCUE COACH for a panicking Egyptian high school girl cramming for an exam. "
                "Start with 2-3 sentences telling her to drop perfectionism, that the ONLY goal is to PASS, and that "
                "she can do this, to relieve panic instantly. Then give a highly prioritized, MINUTE-BY-MINUTE "
                "survival study plan covering the full time left, in clock offsets from now (e.g. 'Minute 0-20'). "
                "Focus ONLY on high-yield topics: the most frequently examined, highest-mark, easiest-to-grab material, "
                "and explicitly tell her which low-yield or hard topics to SKIP. Include short breaks, water/food, and a "
                "final 10-minute calm-down + light-review block; if over 8 hours remain, include a proper sleep block. "
                "If you don't know her exact syllabus, name the typical high-yield topic types for that subject and tell "
                "her to swap in what her teacher stressed. Format as a clean list or table. "
                "Tone: firm, kind, encouraging; Egyptian Arabic mixed with English; punchy lines; some emojis.")
            user = (f"Subject: {subject}\nTime left: {hours} hours ({total_min} minutes)\n"
                    f"Extra info: {extra.strip() or 'none'}")
            with st.spinner("Building your rescue plan… 🚑"):
                st.session_state["sos_plan"] = ask_groq(
                    [{"role": "system", "content": system}, {"role": "user", "content": user}],
                    temperature=0.5, max_tokens=1800)

    with right:
        with st.container(key="card_sos_out"):
            card_title("🛟 Your survival plan")
            if st.session_state["sos_plan"]:
                st.markdown(st.session_state["sos_plan"])
                if st.button("Clear plan"):
                    st.session_state["sos_plan"] = ""
                    st.rerun()
            else:
                st.caption("Your plan will appear here ✨")


# ----------------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("# 🌸 StudyOS")
    st.caption("your cozy study corner ☁️")
    page = st.radio("Navigate", PAGES, label_visibility="collapsed")
    st.markdown("---")
    st.caption("You're doing great 🤍")

{
    "🏠 Dashboard": page_dashboard,
    "📅 Schedule Setup": page_schedule,
    "🤖 AI Bestie": page_bestie,
    "⏳ Focus Room": page_focus,
    "☁️ Brain Dump": page_dump,
    "🚨 SOS Exam Mode": page_sos,
}[page]()
