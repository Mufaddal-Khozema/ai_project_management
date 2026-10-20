# shift the table format here 
from tabulate import tabulate

def chunks(text, n=1990):
    # 
    return[text[i:i + n] for i in range(0, len(text), n)] or [""]

# table formatting for discord messages
# separate these into a different class
def render_table(header, rows):
    """Plain aligned table with a full-width dashed line under the header."""
    table = tabulate(rows, headers=header, tablefmt="plain")
    lines = table.splitlines()
    width = max(len(l) for l in lines)
    lines.insert(1, "-" * width)
    return "\n".join(lines)

def split_reply(text):
    """Split the reply into [("text", str), ("table",str), ...] segments"""
    lines = text.splitlines()
    segments, buffer = [], []
    i=0

    def flush():
        if buffer:
            segments.append(("text", "\n".join(buffer).strip()))
            buffer.clear()

    while i< len(lines):
        if "|" in lines[i] and i+1 <len(lines) and "|" in lines  [i+1]:
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            separator = [c.strip() for c in lines[i + 1].strip().strip("|").split("|")]

            if all (c and set(c) <= {"-", ":"} for c in separator):
                rows =[]
                i +=2
                while i<len(lines) and "|" in lines[i]:
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                    i+=1

                flush()
                segments.append(("table", render_table(header, rows)))
                continue

        buffer.append(lines[i])
        i+=1

    flush()
    return segments
        

def table_chunks(table, limit=1900):
    """Split a long table by lines so every chunk keeps its own code fences."""
    out, current = [], ""
    for line in table.splitlines():
        if len(current) + len(line) + 1 > limit and current:
            out.append(current)
            current = ""
        current += line + "\n"
    if current:
        out.append(current)
    return [f"```text\n{c.rstrip()}\n```" for c in out]


def build_messages(reply):
    """Turn the reply into a list of Discord-ready message strings."""
    messages = []
    for kind, content in split_reply(reply):
        if not content:
            continue
        if kind == "table":
            messages.extend(table_chunks(content))
        else:
            messages.extend(chunks(content))
    return messages
