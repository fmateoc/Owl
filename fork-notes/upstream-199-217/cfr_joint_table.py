import re, sys, json
t = open(sys.argv[1]).read()
tables = re.findall(r'(?s)<TABLE.*?</TABLE>', t)[2:27]
J = {}
for tb in tables:
    hdr = [re.sub('<[^>]+>', '', h).strip() for h in re.findall(r'(?s)<TH[^>]*>(.*?)</TH>', tb)][1:]
    for row in re.findall(r'(?s)<TR>(.*?)</TR>', tb):
        cells = [re.sub('<[^>]+>', '', c).strip() for c in re.findall(r'(?s)<TD[^>]*>(.*?)</TD>', row)]
        if not cells or not cells[0].isdigit():
            continue
        a = int(cells[0])
        for h, v in zip(hdr, cells[1:]):
            if h.isdigit() and v:
                J[(a, int(h))] = float(v)
json.dump({f"{a},{b}": v for (a, b), v in J.items()}, open(sys.argv[2], "w"))
print(len(J))
for a, b in [(90, 76), (76, 90), (112, 102), (102, 112), (112, 103), (103, 112), (112, 107), (107, 112)]:
    print(a, b, J.get((a, b)))
