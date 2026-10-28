"""Strictly anonymized reports for sharing (never suitable for patch authorization).

The complete technical report and locally generated output/backups are PRIVATE.
Preserve only known structural fields for a shareable diagnostic; do not try to
identify private text by guessing whether it looks like a name.
"""
from __future__ import annotations
from copy import deepcopy

SAFE_RECORD = {'id','slot','hunter_slot','status','planned_action'}
SAFE_INVENTORY = {'occupied_slots','empty_slots','missing_known_quest_ids',
                  'selected_palico_ids','hunter_slot_count'}

def redact_report(report:dict)->dict:
    r=deepcopy(report)
    r['source_path']='[redacted: local ZIP or savedata folder]'
    r['source_archive_sha256']=None
    r['plan_fingerprint']='[redacted: private technical report only]'
    for n,group in enumerate(r.get('save_sets',[]),1):
        group['save_set']=f'Save set {n}'
        for container in group.get('containers',{}).values():
            container.pop('source_hashes',None)
            container.pop('inner_sha256',None)
            container.pop('downloaded_palico_references',None)
            # Diagnostic errors can contain raw paths or decoded source text.
            container['errors']=['[redacted: local diagnostic detail]'] * len(container.get('errors',[]))
            for inventory_name in ('quest_inventory','palico_inventory','hired_palico_inventory'):
                inventory=container.get(inventory_name)
                if inventory is None:continue
                records=inventory.get('records',[])
                container[inventory_name]={
                    **{key:deepcopy(value) for key,value in inventory.items() if key in SAFE_INVENTORY},
                    'records':[{key:deepcopy(value) for key,value in rec.items() if key in SAFE_RECORD}
                               for rec in records],
                }
    r['limitations']=[
        'Shareable report: all player-entered names, comments, creator labels, quest strings, file paths, and private hashes removed.',
        'This report is for structural diagnostics only and cannot authorize patching.',
        'The full technical JSON, localized ZIP and recovery ZIP are PRIVATE. Never publish them.',
    ]
    r['report_privacy']='shareable_anonymized_not_authoritative_for_patching'
    return r
