#!/bin/sh
# Download the DFS 2027 individual-market filings used here into $1 (a new, empty directory).
# Source pages: https://myportal.dfs.ny.gov/fr/web/prior-approval/ind-and-sg-medical/additional-information-2027
# and https://myportal.dfs.ny.gov/fr/web/prior-approval/2027-final-exhibits (no login for direct links).
set -e
out=$1; mkdir -p "$out/appr" "$out/fx"; cd "$out"
base=https://myportal.dfs.ny.gov/documents/538523
get() {  # folder id, file stem, target dir; names the file by its Content-Disposition extension
    curl -sS -D "$3/$2.hdr" -o "$3/$2" "$base/$1/$2"
    ext=$(grep -o 'filename="[^"]*"' "$3/$2.hdr" | sed 's/.*\.\([A-Za-z]*\)"/\1/')
    mv "$3/$2" "$3/$2.$ext"
}
for c in Aetna_Life_IND_OFFX_AETN-134940182 Anthem_HP_IND_BOTHX_AWLP-134943096 CDPHP_IND_BOTHX_CAPD-134941327 \
         Excellus_IND_BOTHX_EXHP-134941380 HIP_IND_BOTHX_HPHP-134946037 Healthfirst_PHSP_IND_BOTHX_HLFT-134940074 \
         Highmark_IND_BOTHX_HLTH-134942567 IHBC_IND_BOTHX_NDPD-134940611 MVP_HP_IND_BOTHX_MVPH-134941994 \
         MetroPlus_IND_ONX_MPHP-134940701 NYQHC_IND_BOTHX_CECO-134948674 Oscar_IND_BOTHX_OHIN-134947352 \
         UHC_IND_BOTHX_UHLC-134947070 UHIC_IND_OFFX_UHLC-134947087; do
    get 47770041 "${c}_ApprRatesTemplate" appr
done
# Exhibits and rate applications: only the filings with Rating Area 4 rates.
for c in Aetna_Life_IND_OFFX_AETN-134940182 Anthem_HP_IND_BOTHX_AWLP-134943096 HIP_IND_BOTHX_HPHP-134946037 \
         Healthfirst_PHSP_IND_BOTHX_HLFT-134940074 MVP_HP_IND_BOTHX_MVPH-134941994 MetroPlus_IND_ONX_MPHP-134940701 \
         NYQHC_IND_BOTHX_CECO-134948674 Oscar_IND_BOTHX_OHIN-134947352 UHC_IND_BOTHX_UHLC-134947070 \
         UHIC_IND_OFFX_UHLC-134947087; do
    get 47770089 "${c}_FinalExhibits" fx
    get 47769861 "${c}_Application" fx
    mkdir -p "fx/unz/$c"; unzip -q -o "fx/${c}_FinalExhibits.zip" -d "fx/unz/$c"
done
for z in appr/*.zip; do mkdir -p "${z%.zip}_unz"; unzip -q -o "$z" -d "${z%.zip}_unz"; done
