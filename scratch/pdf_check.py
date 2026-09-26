import subprocess, sys, re, io
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import pymupdf

doc = pymupdf.open('paper/main.pdf')
print('pages after :', doc.page_count)
flat = re.sub(r'\s+', '', ''.join(p.get_text() for p in doc))
print('text chars  :', len(flat))

# page count of the committed version
try:
    blob = subprocess.run(['git', 'show', 'HEAD:main.pdf'], cwd='paper',
                          capture_output=True).stdout
    old = pymupdf.open(stream=blob, filetype='pdf')
    print('pages before:', old.page_count)
    oldflat = re.sub(r'\s+', '', ''.join(p.get_text() for p in old))
    print('before chars:', len(oldflat))
except Exception as e:
    print('old pdf unavailable:', e)
    oldflat = None

checks_new = [
    ('missingness new wording', '某个列表型字段整条缺失'),
    ('fig q1gating half-width 0.0093', '半宽0.0093'),
    ('conflict column header new', 'CD1固定阈0.25'),
    ('conflict body label new', 'CD1固定阈0.25下0.994'),
    ('book caliber note', '等n对照重抽给出的半宽为0.00880'),
    ('book caliber cross-source', '同量级但不同源'),
    ('mixture 1B upper endpoint', '1.5×10-5'),
    ('tier counts A8/B11/C3', '证据可直接核验者8项'),
    ('tier sensitivity sentence', '并另报方向替换下的敏感性'),
    ('length exposure 0.499', 'Spearman相关为0.499'),
    ('A12/A14 scoping', '其中外推表'),
    ('regmix citation resolved', 'liu2024regmix'),
]
checks_old = [
    ('missingness OLD wording', '在6个列表型字段上整行为空'),
    ('fig OLD 0.0091', '半宽0.0091'),
    ('conflict OLD header', 'MAD锚定(一维离散度)&'),
    ('body OLD label', 'MAD锚定下0.994'),
    ('mixture OLD 0.00002', '+0.00002)'),
    ('OLD 三位有效数字 caption', '区间端点按三位有效数字舍入'),
    ('OLD tier counts', 'A8项/B8项/C6项'),
    ('OLD 本队自行计算 (this section)', 'A18的文本统计量由本队自行计算'),
]

print('\n--- expected PRESENT in new build ---')
for n, s in checks_new:
    print('  %-32s %s' % (n, 'FOUND' if s.replace(' ', '') in flat else 'MISSING'))

print('\n--- expected ABSENT (old wording) ---')
for n, s in checks_old:
    hit = s.replace(' ', '') in flat
    print('  %-32s %s' % (n, 'STILL PRESENT' if hit else 'gone'))

if oldflat is not None:
    print('\n--- absent in old build (confirms the change is new) ---')
    for n, s in checks_new[:11]:
        k = s.replace(' ', '')
        print('  %-32s old=%s new=%s' % (n, k in oldflat, k in flat))
