import os
with open("fb_webhook_debug.jsonl", "r", encoding="utf-8") as f:
    lines = f.readlines()
with open("tail_out.txt", "w", encoding="utf-8") as out:
    out.write("Total lines: " + str(len(lines)) + "\n")
    for line in lines[-5:]:
        out.write(line)
