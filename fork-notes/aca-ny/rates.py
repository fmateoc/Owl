"""Parse approved 2027 individual rate templates (CMS Rates Table Template) into one CSV."""
import sys, glob, os, warnings, pandas as pd
warnings.filterwarnings("ignore")
root, out = sys.argv[1], sys.argv[2]
rows = []
files = [f for f in glob.glob(os.path.join(root, '**', '*'), recursive=True)
         if f.lower().endswith(('.xls', '.xlsm', '.xlsx'))]
for f in sorted(files):
    carrier = os.path.relpath(f, root).split('_IND_')[0]
    xl = pd.ExcelFile(f)
    for sh in xl.sheet_names:
        if 'Rate Table' not in sh:
            continue
        df = pd.read_excel(f, sheet_name=sh, header=None)
        meta = {str(df.iat[i, 0]).strip(): df.iat[i, 1] for i in range(min(12, len(df)))}
        hdr = next((i for i in range(len(df)) if str(df.iat[i, 0]).startswith('Plan ID')), None)
        if hdr is None:
            continue
        for i in range(hdr + 2, len(df)):
            pid = str(df.iat[i, 0]).strip()
            if len(pid) != 14:
                continue
            rows.append(dict(carrier=carrier, file=os.path.basename(f), sheet=sh,
                             method=meta.get('Rating Method*'), eff=meta.get('Rate Effective Date*'),
                             plan=pid, area=df.iat[i, 1], age=df.iat[i, 3],
                             single=df.iat[i, 4], couple=df.iat[i, 6]))
d = pd.DataFrame(rows)
d.to_csv(out, index=False)
print(d.groupby(['carrier', 'area']).plan.nunique().unstack(fill_value=0).to_string())
print(d.method.value_counts(dropna=False).to_string()); print(d.eff.astype(str).value_counts().to_string())
print('couple/single ratio:', (d.couple.astype(float) / d.single.astype(float)).describe().to_string())
