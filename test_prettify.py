import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','oklahoma_dashboard.settings')
import django
django.setup()
from stats.cfb_api import prettify_stat_name
examples=['ThirdDownEff','third_down_eff','rushingYds','PassYds','INTs','thirdDownEffPct','CompletionPct','FGM','SACKS','ATT','CMP','FUM']
for e in examples:
    print(f"{e} -> {prettify_stat_name(e)}")

