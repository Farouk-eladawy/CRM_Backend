from pathlib import Path
p=Path(\\" "tools/migration_status.py\)
lines=p.read_text(encoding=\utf-8\).splitlines()
out=[]
done=any(\migrate_list_bundle.log\ in l for l in lines)
for line in lines:
  if \migrate_list_fresh.log\ in line and not done:
    out.append(line.replace(\migrate_list_fresh\,\migrate_list_bundle\))
    done=True
  out.append(line)
p.write_text(\\\n\.join(out)+\\\n\,encoding=\utf-8\)
print(\fixed\)
