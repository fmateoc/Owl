import glob, io, os
import numpy as np
import owlplanner as owl
from owlplanner import socialsecurity as ss
EX = "/home/user/Owl/examples"
for f in sorted(glob.glob(f"{EX}/Case_*.toml")):
    p = owl.readConfig(f, verbose=False, logstreams=[io.StringIO()])
    hfp = f.replace("Case_", "HFP_").replace("-spending", "").replace("-bequest", "").replace(".toml", ".xlsx")
    if os.path.exists(hfp):
        p.readHFP(hfp)
    name = os.path.basename(f)[5:-5]
    y0 = int(p.year_n[0])
    e, _ = p._earnings_test_inputs()
    k1 = p.kappa_ijn[:, 1, : p.N_n]
    hit229 = [(p.inames[i], y0 + n, round(k1[i, n])) for i in range(p.N_i) for n in range(p.N_n)
              if p.omega_in[i, n] <= 0 < k1[i, n]]
    hit232 = []
    if p.N_i == 2:
        sb = ss.getSpousalBenefits(np.asarray(p.ssecAmounts, dtype=np.int32))
        fras = ss.getFRAs(p.yobs, p.mobs, p.tobs)
        for j in range(2):
            i = 1 - j
            if sb[j] <= 0:
                continue
            fra_j = ss._ent_start_abs(p.yobs[j], p.mobs[j], ss._fra_conventional_age(fras[j], p.tobs[j] == 1))
            fra_i = ss._ent_start_abs(p.yobs[i], p.mobs[i], ss._fra_conventional_age(fras[i], p.tobs[i] == 1))
            ent_i = ss._ent_start_abs(p.yobs[i], p.mobs[i], max(p.ssecAges[i], 62))
            for n in range(p.N_n):
                y = y0 + n
                if e[i, n] > ss.get_exempt_amounts(y).annual and y * 12 + 11 >= fra_j and ent_i <= y * 12 + 11 and y * 12 < fra_i:
                    hit232.append((p.inames[i], y))
    print(f"{name:28s} #229 years wages=0, 401k/IRA>0: {hit229 or '-'};  #232 worker over exempt after spouse FRA: {hit232 or '-'}")
