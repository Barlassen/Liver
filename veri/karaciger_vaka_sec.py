"""AbdomenAtlas 3.0 Mini metadata'sindan karaciger vakalarini secer ve indirme planini cikarir.
Girdi: AbdomenAtlas3.0MiniWithMeta.csv, TrainTestIDS/IID_train.csv, TrainTestIDS/IID_test.csv
Cikti: karaciger_vakalar.csv (secilen vakalar + split + tumor bilgisi), indirme_plani.csv (gereken parcalar)
Kullanim: python karaciger_vaka_sec.py --meta META.csv --ids TrainTestIDS --parca-sayisi 6
"""
import argparse, pandas as pd

L = 'number of liver lesion instances'
D = 'largest liver lesion diameter (cm)'
PARCA = 232        # her tar.gz parcasinda 232 vaka var (BDMAP_00000001-00000232, ...)
RSNA_BASLANGIC = 5196  # bu ID'den sonrasi RSNA Trauma; karaciger tumoru nadir

p = argparse.ArgumentParser()
p.add_argument('--meta', default='AbdomenAtlas3.0MiniWithMeta.csv')
p.add_argument('--ids', default='TrainTestIDS')
p.add_argument('--parca-sayisi', type=int, default=6, help='ilk kac parca indirilecek')
a = p.parse_args()

m = pd.read_csv(a.meta)
m['num'] = m['BDMAP ID'].str[6:].astype(int)
m['parca'] = (m['num'] - 1) // PARCA
m['tumor_var'] = m[L] > 0
test = set(pd.read_csv(f'{a.ids}/IID_test.csv')['BDMAP ID'])
m['split'] = m['BDMAP ID'].map(lambda x: 'test' if x in test else 'train')
m['boyut_grubu'] = pd.cut(m[D], [0, 1, 2, 5, 1000], right=False,
                          labels=['<1cm', '1-2cm', '2-5cm', '>=5cm']).astype(str).where(m['tumor_var'], 'yok')

sec = m[(m['parca'] < a.parca_sayisi) & (m['num'] < RSNA_BASLANGIC)]
cols = ['BDMAP ID', 'split', 'tumor_var', L, D, 'boyut_grubu', 'contrast', 'spacing', 'parca']
sec[cols].to_csv('karaciger_vakalar.csv', index=False)

plan = sec.groupby('parca').agg(tumorlu=('tumor_var', 'sum'), toplam=('tumor_var', 'size')).reset_index()
plan['dosya'] = plan['parca'].map(lambda i: 'AbdomenAtlas3_images_BDMAP_BDMAP_%08d_BDMAP_%08d.tar.gz'
                                  % (i * PARCA + 1, min((i + 1) * PARCA, 9262)))
plan.to_csv('indirme_plani.csv', index=False)

print(sec.groupby(['split', 'tumor_var']).size().rename('vaka').to_string())
print('\nTumorlu vakalarda boyut dagilimi:')
print(sec[sec.tumor_var].groupby(['split', 'boyut_grubu']).size().unstack(fill_value=0).to_string())
