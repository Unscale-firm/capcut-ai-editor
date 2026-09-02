"""
One line per chat, appended to the shared CHATLOG so any past work can be found by a word search.

Run at the end of every session (and before every handoff):
  venv/bin/python pipeline/chatlog.py --session <session-id> --ads "F10, ad 13" "cut F10 test, fixed seams, delivered h1"

Log lives on the share (visible from Windows as Z:\\chat-handoffs\\CHATLOG.md):
  /srv/media/chat-handoffs/CHATLOG.md
"""
import argparse, datetime, os

LOG = "/srv/media/chat-handoffs/CHATLOG.md"
HEADER = ("# CHATLOG — one line per chat (search this file by any word)\n\n"
          "| date | session id | ads | what was done |\n|---|---|---|---|\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary", help="plain words, one line: what this chat did / decided / delivered")
    ap.add_argument("--session", required=True, help="Claude session id (from the session link)")
    ap.add_argument("--ads", default="-", help='ads touched, e.g. "F10, ad 13"; "-" if none')
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    line = f"| {a.date} | `{a.session}` | {a.ads} | {a.summary.strip().replace('|', '/')} |\n"
    new = not os.path.exists(LOG)
    with open(LOG, "a", encoding="utf-8") as f:
        if new:
            f.write(HEADER)
        f.write(line)
    print(("created " if new else "appended to ") + LOG)
    print(line.strip())


if __name__ == "__main__":
    main()
