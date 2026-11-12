# oosscan.py [fam ...] [code=o8] [start=N] [n=N] [full=1]
# Line-level scan of the FULL mark-scheme text of every out-of-scope Paper 2 item for vocabulary of the in-scope subsections.
from state import *
FAM = {
 "1": r"cell wall|cell (surface )?membrane|cytoplasm|nucle(us|i)\b|vacuole|chloroplast|mitochondri|ribosome|plasmid|magnif|microscop|organelle|specialis|root hair|palisade|ciliated|\btissues?\b|organ system",
 "3": r"diffus|osmo|water potential|turgid|turgor|flaccid|plasmoly|partially permeable|semi.?permeable|selectively permeable|concentration gradient|conc\.? gradient|surface area|active (transport|uptake)|actively|against (a |the )?(conc|gradient)",
 "4": r"benedict|biuret|iodine|ethanol|emulsion|dcpip|reducing sugar|fatty acid|glycerol|cellulose|\belements?\b|nucleotide|solvent|large molecule|small(er)? molecule|made (up )?of|polymer|monomer",
 "5": r"enzyme|substrate|active site|denatur|optimum|catalys|lock and key|complementary|specific\b",
 "7": r"xylem|phloem|transpir|transloc|wilt|stomata|cohesi|vascular|lignin|sieve|sucrose|\bsink\b|root pressure|water uptake|uptake of water|mineral (ion|salt)|potometer",
 "11": r"heart|atri(um|a)\b|ventric|valve|arter|vein|vena|capillar|aorta|pulmonary|coronary|plasma|platelet|ha?emoglobin|phagocyt|lymph|antibod|clot|fibrin|tissue fluid|circulat|pulse|blood pressure|red (blood )?cell|white (blood )?cell|blood vessel",
 "13": r"excret|urea|kidney|nephron|ureter|bladder|urethra|urine|deaminat|glomerul|filtrat|reabsor|renal|dialys",
 "14a": r"neurone|nerve|impulse|synap|reflex|receptor|effector|\bCNS\b|brain|spinal|neurotransmit|\beye|retina|\blens|iris|pupil|cornea|ciliary|suspensory|optic|\brods?\b|\bcones?\b|fovea|accommodat|focus|stimul",
 "14b": r"hormone|adrenal|insulin|glucagon|endocrine|\bgland|pancreas|pituitary|testosterone|oestrogen|progesterone|\bFSH\b|\bLH\b|homeosta|negative feedback|set point|body temperature|sweat|vasodilat|vasoconstrict|shiver|hair erect|\bskin\b|hypothalamus|glycogen|blood (glucose|sugar)|diabet|constant internal",
 "15": r"tropi(sm|c)|auxin|phototrop|gravitrop|geotrop|shoot tip|elongat|towards (the )?light|grow(s|th)? towards",
 "17": r"variation|continuous|mutat|mutagen|radiation|\bDNA\b|\bgenes?\b|chromosome|\bbases?\b|double helix|protein synthesis|mRNA|genetic code|allele|genotype|phenotype|homozyg|heterozyg|dominan|recessive|inherit|punnett|\bratio|sex.?linked|\bXX\b|\bXY\b|blood group|haploid|diploid|select|adapt|evolution|evolve|surviv|resistan|fittest|identical|clone",
}
if __name__ == "__main__":
    # usage: oosscan.py [code=o19] [budget=14000] [full=1] [markdone=o16]
    items = load_items(); dec = load_dec(); order_ = order()
    kw = dict(a.split("=") for a in sys.argv[1:] if "=" in a)
    fams = [a for a in sys.argv[1:] if "=" not in a] or list(FAM)
    rx = re.compile("|".join("(?:%s)" % FAM[f] for f in fams), re.I)
    fn = os.path.join(W, "state/oos_scanned.json")
    done = jload("state/oos_scanned.json") if os.path.exists(fn) else []
    dset = set(done)
    if "markdone" in kw:
        new = [i for i in order_ if items[i]["paper"] == 2 and kw["markdone"] in dec[i]["sec"].split("+") and i not in dset]
        jsave("state/oos_scanned.json", done + new); print("marked", len(new)); sys.exit()
    ids = [i for i in order_ if dec[i]["status"] == "oos" and items[i]["paper"] == 2 and (("code" not in kw) or kw["code"] in dec[i]["sec"].split("+")) and i not in dset]
    budget = int(kw.get("budget", 14000)); used = 0; hit = 0; seen = []
    for i in ids:
        it = items[i]
        lines = [l for l in it["ms_text"].split("\n") if not l.startswith("<<MS")]
        m = [k for k, l in enumerate(lines) if rx.search(l)]
        if m:
            q = re.sub(r"\s+", " ", it["qtext"])[-110:]
            out = "## %s [%s] %s\n" % (i, dec[i]["sec"], q)
            out += ("\n".join(lines) if kw.get("full") else "\n".join("   " + lines[k][:230] for k in m))
            if used + len(out) > budget and seen: break
            print(out); used += len(out); hit += 1
        seen.append(i)
    jsave("state/oos_scanned.json", done + seen)
    print("-- scanned %d (hits %d); remaining unscanned for this filter: %d" % (len(seen), hit, len(ids) - len(seen)))
