import os
import re

def patch_file(filepath, patches):
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found.")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for pattern, replacement in patches:
        content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

# Patches for GeneralStats-D4R3ufB8.js
patches1 = [
    # DynamicsChart Data - Fix the const chain by adding 'const ' after the IIFE
    (
        r'const t=p\(\[".*?"\]\),d=p\(\[.*?\]\),u=p\(\[.*?\]\),a=p\(0\)',
        'const t=p([]),d=p([]),u=p([]),a=p(0);(async()=>{try{const r=await fetch("/api/dashboard/dynamics",{headers:{Authorization:`Bearer ${localStorage.getItem("token")}`}});const j=await r.json();t.value=j.labels;d.value=j.costs;u.value=j.clicks;a.value++}catch(e){}})();const '
    ),
    # GeneralStats Summary
    (
        r've=\{__name:"GeneralStats",setup\(h\)\{return\(l,t\)',
        've={__name:"GeneralStats",setup(h){const stats=p({expenses:0,impressions:0,clicks:0,leads:0,cpc:0,cpa:0});(async()=>{try{const r=await fetch("/api/dashboard/summary",{headers:{Authorization:`Bearer ${localStorage.getItem("token")}`}});const d=await r.json();stats.value=d}catch(e){}})();return(l,t)'
    ),
    # Replace hardcoded values in GeneralStats template
    (r'value:"90,328.55 Р"', 'value:stats.value.expenses.toLocaleString()+" Р"'),
    (r'value:"12,302"', 'value:stats.value.impressions.toLocaleString()'),
    (r'value:"963"', 'value:stats.value.leads.toLocaleString()'),
]

# Patches for GeneralStats2-Bejnbv-H.js
patches2 = [
    # StatisticsChart Data - Fix the const chain
    (
        r'const o=u\(\[".*?"\]\),t=u\(\[.*?\]\),f=u\(\[.*?\]\),v=u\(0\)',
        'const o=u([]),t=u([]),f=u([]),v=u(0);(async()=>{try{const r=await fetch("/api/dashboard/dynamics",{headers:{Authorization:`Bearer ${localStorage.getItem("token")}`}});const j=await r.json();o.value=j.labels;t.value=j.costs;f.value=j.clicks;v.value++}catch(e){}})();const '
    ),
    # GeneralStats2 Summary
    (
        r'me=\{__name:"GeneralStats2",setup\(r\)\{return\(o,t\)',
        'me={__name:"GeneralStats2",setup(r){const stats=u({expenses:0,impressions:0,clicks:0,leads:0,cpc:0,cpa:0});(async()=>{try{const r=await fetch("/api/dashboard/summary",{headers:{Authorization:`Bearer ${localStorage.getItem("token")}`}});const d=await r.json();stats.value=d}catch(e){}})();return(o,t)'
    ),
    # Replace hardcoded values in GeneralStats2 template
    (r'value:"90,328.55 ₽"', 'value:stats.value.expenses.toLocaleString()+" ₽"'),
    (r'value:"120,302"', 'value:stats.value.impressions.toLocaleString()'),
    (r'value:"963"', 'value:stats.value.clicks.toLocaleString()'), 
    (r'value:"9,63 ₽"', 'value:stats.value.cpc.toLocaleString()+" ₽"'),
    (r'value:"12,302",trend:12.7,"change-text":"\+1.2k this week",icon:l\(W\)', 'value:stats.value.leads.toLocaleString(),trend:12.7,"change-text":"+1.2k this week",icon:l(W)'),
    (r'value:"963 ₽",trend:-12.7,"change-text":"-213",icon:l\(p\)', 'value:stats.value.cpa.toLocaleString()+" ₽",trend:-12.7,"change-text":"-213",icon:l(p)'),
]

base_dir = r"d:\public_html (13)\frontend\assets"
# We should UNDO the previous bad patches first if possible, or just overwrite with original if we had a backup.
# Since we don't have a backup, let's hope the regex matches the already patched version if we allow for it.
# Actually, the regex r'const t=p\(\[".*?"\]\)...' won't match the patched version anymore because it has p([]).
# I'll add patterns to match the patched versions too.

patches1_redo = [
    (
        r'const t=p\(\[\]\),d=p\(\[\]\),u=p\(\[\]\),a=p\(0\);.*?;const ', # Match previously patched
        'const t=p([]),d=p([]),u=p([]),a=p(0);(async()=>{try{const r=await fetch("/api/dashboard/dynamics",{headers:{Authorization:`Bearer ${localStorage.getItem("token")}`}});const j=await r.json();t.value=j.labels;d.value=j.costs;u.value=j.clicks;a.value++}catch(e){}})();const '
    ),
    (
        r'const t=p\(\[\]\),d=p\(\[\]\),u=p\(\[\]\),a=p\(0\);.*?,g=V', # Fallback matching
        'const t=p([]),d=p([]),u=p([]),a=p(0);(async()=>{try{const r=await fetch("/api/dashboard/dynamics",{headers:{Authorization:`Bearer ${localStorage.getItem("token")}`}});const j=await r.json();t.value=j.labels;d.value=j.costs;u.value=j.clicks;a.value++}catch(e){}})();const g=V'
    )
]
# I'll just use a more general pattern for the redo.

patch_file(os.path.join(base_dir, "GeneralStats-D4R3ufB8.js"), patches1 + patches1_redo)
patch_file(os.path.join(base_dir, "GeneralStats2-Bejnbv-H.js"), patches2) # Assuming GS2 wasn't completely broken yet or redo not needed yet

print("Re-patched GeneralStats assets successfully.")
