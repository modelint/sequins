import json, os, re, sys, glob, datetime

# Usage:
#   python3 gen_session_md.py [SESSION.jsonl] [OUTDIR] [BASENAME]
#
#   SESSION.jsonl  source Claude Code transcript. Default: most recently
#                  modified *.jsonl in this project's ~/.claude transcript dir.
#   OUTDIR         where to write the .md file. Default: ../ (documentation/).
#   BASENAME       output stem. Default: model-prompting-session.
# Produces BASENAME.md: a clean, readable dialog (prompts + prose answers, with
# file reads/edits condensed to one-line notes; internal reasoning omitted).

PROJECT_TRANSCRIPTS = os.path.expanduser(
    "~/.claude/projects/-Users-starr-SDEV-Python-PyCharm-Sequins")

def latest_transcript():
    jsonls = glob.glob(os.path.join(PROJECT_TRANSCRIPTS, "*.jsonl"))
    if not jsonls:
        sys.exit(f"No .jsonl transcripts found in {PROJECT_TRANSCRIPTS}")
    return max(jsonls, key=os.path.getmtime)

SRC      = sys.argv[1] if len(sys.argv) > 1 else latest_transcript()
OUTDIR   = sys.argv[2] if len(sys.argv) > 2 else os.path.normpath(
               os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BASENAME = sys.argv[3] if len(sys.argv) > 3 else "model-prompting-session"
CLEAN = os.path.join(OUTDIR, f"{BASENAME}.md")

records = []
with open(SRC) as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))

def base(p):
    return os.path.basename(p) if isinstance(p, str) else str(p)

def strip_reminders(t):
    t = re.sub(r"<system-reminder>.*?</system-reminder>", "", t, flags=re.S)
    return t.strip()

def result_to_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out = []
        for b in content:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    out.append(b.get("text", ""))
                else:
                    out.append(json.dumps(b))
            else:
                out.append(str(b))
        return "\n".join(out)
    return json.dumps(content)

def describe_tool(name, inp):
    inp = inp or {}
    if name == "Read":
        return f"read `{base(inp.get('file_path',''))}`"
    if name == "Write":
        return f"wrote `{base(inp.get('file_path',''))}`"
    if name == "Edit":
        return f"edited `{base(inp.get('file_path',''))}`"
    if name == "Bash":
        d = inp.get("description") or (inp.get("command","")[:50])
        return f"bash: {d}"
    if name == "AskUserQuestion":
        qs = inp.get("questions") or []
        q0 = qs[0].get("question","") if qs else ""
        return f"asked: {q0[:60]}"
    return f"{name}({', '.join(inp.keys())})"

# ---------- CLEAN ----------
clean = []
clean.append("# Sequins — Model-Driven Prompting Session")
clean.append("")
clean.append("> A worked example of *model-driven prompting*: Claude reads an Executable UML")
clean.append("> class model (`sequins.xcm`) plus its wiki, asks clarifying questions and flags")
clean.append("> inconsistencies, and the modeler (Leon Starr) fixes the model in response.")
clean.append(">")
clean.append(f"> Generated from session transcript `{base(SRC)}` on "
             f"{datetime.date.today().isoformat()}. Internal reasoning omitted; file reads")
clean.append("> and edits condensed to one-line notes. See `model-prompting-session.raw.md`")
clean.append("> for the full verbatim record.")
clean.append("")

pending = []
def flush_clean():
    if pending:
        clean.append("")
        clean.append("> 🔧 " + " · ".join(pending))
        clean.append("")
        pending.clear()

turn = 0
for o in records:
    typ = o.get("type")
    if typ not in ("user", "assistant"):
        continue
    msg = o.get("message", {}) or {}
    content = msg.get("content")
    if typ == "user":
        # tool_result user records -> skip in clean
        if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            continue
        text = content if isinstance(content, str) else result_to_text(content)
        if "<command-name>" in text:
            cmd = re.search(r"<command-name>(.*?)</command-name>", text, flags=re.S)
            note = cmd.group(1).strip() if cmd else "command"
            flush_clean()
            clean.append("\n---\n")
            clean.append(f"**Leon:** *(ran `{note}`)*")
            continue
        text = strip_reminders(text)
        if not text:
            continue
        flush_clean()
        turn += 1
        clean.append("\n---\n")
        clean.append(f"**Leon:** {text}")
    else:  # assistant
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            t = b.get("type")
            if t == "thinking":
                continue
            if t == "text":
                flush_clean()
                clean.append("")
                clean.append(f"**Claude:** {b.get('text','').strip()}")
            elif t == "tool_use":
                pending.append(describe_tool(b.get("name"), b.get("input")))
flush_clean()

with open(CLEAN, "w") as fh:
    fh.write("\n".join(clean).rstrip() + "\n")

print("CLEAN:", CLEAN, os.path.getsize(CLEAN), "bytes")
print("records:", len(records))
