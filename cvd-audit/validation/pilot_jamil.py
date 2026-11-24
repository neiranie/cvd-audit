"""Pilot: do simple image-level CVD metrics track the published human ratings
of Jamil & Denes (2024)? Secondary analysis, no new respondents."""
import sys, numpy as np, pandas as pd
from PIL import Image
from skimage.color import rgb2lab, deltaE_ciede2000
from scipy.stats import spearmanr
root = sys.argv[1]
d = pd.read_csv(f"{root}/data_clean.csv")
st = (d.groupby('stimulus')
        .agg(fs=('func','mean'), n=('func','size'), aes=('aes','mean'),
             app=('app','first'), hc=('hc','first'), ref=('ref','first'),
             deut=('deut','first'), prot=('prot','first'), trit=('trit','first'))
        .reset_index())
def load(p, f=4):
    im = Image.open(f"{root}/screenshots/{p}").convert('RGB')
    im = im.reduce(f)
    return rgb2lab(np.asarray(im)/255.0)
rows=[]
for _,r in st.iterrows():
    ref = load(r.ref); per=[]
    for k in ('deut','prot','trit'):
        sim = load(r[k])
        if sim.shape!=ref.shape:
            im = Image.open(f"{root}/screenshots/{r[k]}").convert('RGB')
            im = im.resize((ref.shape[1],ref.shape[0]))
            sim = rgb2lab(np.asarray(im)/255.0)
        de = deltaE_ciede2000(ref, sim)
        per.append((de.mean(), np.percentile(de,95), (de>10).mean()))
    m = np.mean(per,axis=0)
    rows.append(dict(stimulus=r.stimulus, app=r.app, hc=r.hc, fs=r.fs, n=r.n,
                     dE_mean=m[0], dE_p95=m[1], frac_gt10=m[2]))
o = pd.DataFrame(rows); o.to_csv(sys.argv[2], index=False)
print(len(o),'stimuli')
rng=np.random.default_rng(0)
for c in ('dE_mean','dE_p95','frac_gt10'):
    rho,p = spearmanr(o[c], o.fs)
    bs=[spearmanr(o[c].values[i], o.fs.values[i])[0] for i in (rng.integers(0,len(o),len(o)) for _ in range(2000))]
    print(f"{c}: rho={rho:.3f} p={p:.4f} 95%CI=[{np.percentile(bs,2.5):.3f},{np.percentile(bs,97.5):.3f}]")
for hc,g in o.groupby('hc'):
    rho,p=spearmanr(g.dE_mean,g.fs); print('hc=',hc,'n=',len(g),f'rho(dE_mean)={rho:.3f} p={p:.4f}')
