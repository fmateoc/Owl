"""2026 Region 4 subscriber rates for exchange silver plans, from Exhibit 23 (column 'Region 4 - 2026 Rate')."""
import sys, glob, os, warnings, pandas as pd
warnings.filterwarnings("ignore")
rows = []
for f in sorted(glob.glob(os.path.join(sys.argv[1], '*', '*_IN_23_*'))):
    carrier = os.path.basename(os.path.dirname(f)).split('_IND_')[0]
    df = pd.read_excel(f, sheet_name='23', header=None)
    c26 = next(c for c in range(df.shape[1]) if str(df.iat[2, c]).startswith('Region 4 - 2026 Rate'))
    for i in range(3, len(df)):
        h = str(df.iat[i, 4]).strip()
        if len(h) == 16 and str(df.iat[i, 16]).strip() == 'No' and df.iat[i, 6] == 'Silver' and str(df.iat[i, 7]).strip() == 'On':
            v = pd.to_numeric(df.iat[i, c26], errors='coerce')
            if v > 0:
                rows.append(dict(carrier=carrier, hios16=h, prev=df.iat[i, 5], child_age=df.iat[i, 9], rate2026=v))
d = pd.DataFrame(rows).drop_duplicates(['carrier', 'rate2026', 'child_age']).sort_values('rate2026')
print(d.head(12).to_string(index=False))
