import json, sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.startswith("{")]
base={(r["decider"],r["objective"],r["horizon_a"]):r.get("value") for r in rows if r["split"]==0.5}
print(f"{'dec':5} {'objective':11} {'A':>3} {'split':>5} {'value':>14} {'vs 0.5':>10} {'LP dep A':>9} {'LP dep B':>9} {'netted':>8} {'deposit years (yr, dA, dB, s)':30} {'s':>5}")
for r in rows:
    v=r.get("value"); b=base.get((r["decider"],r["objective"],r["horizon_a"]))
    dA,dB=(r.get("raw_deposits_today") or [float('nan')]*2)
    dy=";".join(f"{y}:{a//1000}k/{bb//1000}k" for y,a,bb,s in r.get("deposit_years",[]))
    print(f"{r['decider']:5} {r['objective']:11} {r['horizon_a']:>3} {str(r['split']):>5} "
          f"{(v or float('nan')):>14,.2f} {((v-b) if v is not None and b is not None else float('nan')):>10,.2f} "
          f"{dA:>9,.0f} {dB:>9,.0f} {r.get('netted_today',0):>8,.0f} {dy[:30]:30} {r['seconds']:>5.0f}"
          + ("" if r["status"]=="solved" else f" {r['status']}"))
