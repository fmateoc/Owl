"""Read Exhibit 23 (plan information) from each carrier's Final Exhibits."""
import sys, glob, os, warnings, pandas as pd
warnings.filterwarnings("ignore")
root, out = sys.argv[1], sys.argv[2]
cols = {4: 'hios16', 6: 'metal', 7: 'xchg', 8: 'std', 9: 'child_age', 12: 'ped_dental', 14: 'non_ehb',
        16: 'child_only', 17: 'tiered', 18: 'hsa', 19: 'pnds', 20: 'network'}
rows = []
for f in sorted(glob.glob(os.path.join(root, '*', '*_IN_23_*'))):
    carrier = os.path.basename(os.path.dirname(f)).split('_IND_')[0]
    df = pd.read_excel(f, sheet_name='23', header=None)
    assert str(df.iat[2, 4]).startswith('5. Current HIOS'), (f, df.iat[2, 4])
    for i in range(3, len(df)):
        h = str(df.iat[i, 4]).strip()
        if len(h) != 16:
            continue
        r = {k: df.iat[i, c] for c, k in cols.items()}
        r['carrier'] = carrier; r['plan'] = h[:14]
        rows.append(r)
d = pd.DataFrame(rows); d.to_csv(out, index=False)
print(d.groupby(['carrier', 'xchg']).size().unstack(fill_value=0).to_string())
