"""Check that unrelated missing/custom inventory isn't misrepresented as a partial patch."""
import desktop_app as gui
from patch_dlc import _approved_statuses, _expected_plan


def make(quests=True,pids=()):
    return {'options':{'quests':quests,'palico_ids':list(pids),'hired_palicoes':False},
        'catalog_quality':{'errors':[]},'save_sets':[{'save_set':'.','containers':{
            'ULJM05800QST':{'status':'validated','quest_inventory':{'records':[
                {'id':'m60001.mib','slot':0,'status':'eligible_translation'},
                {'id':'modded','slot':1,'status':'skipped_unknown_quest','reason':'unknown'}]}},
            'ULJM05800':{'status':'validated','palico_inventory':{'records':[
                {'id':None,'slot':0,'status':'skipped_unrecognized_or_custom_palico','reason':'unknown'},
                {'id':'maki','slot':1,'status':'protected_custom_text','reason':'custom'},
                {'id':'ue','slot':2,'status':'eligible_translation'}]}}}}]}

a=make(quests=True,pids=[])
try:_approved_statuses(a,False)
except ValueError as exc:assert '1 selected' in str(exc)
else:raise AssertionError('Selected unknown quest must require approval')
a=make(quests=False,pids=['ue'])
assert _approved_statuses(a,False)==[]
assert gui.omissions_in_plan(a)==[]
assert gui.summary_of(a)['counts']=={'eligible_translation':1}
print('PASS unrelated unknown/custom Palicoes do not block selected ue',flush=True)
a=make(quests=False,pids=['maki'])
assert len(gui.omissions_in_plan(a))==1
try:_approved_statuses(a,False)
except ValueError:pass
else:raise AssertionError('Selected customized Palico requires approval')
assert len(_approved_statuses(a,True))==1
print('PASS selected customized Palico requires explicit partial approval',flush=True)
plan={'analyzer_version':'0.6.3','operation':'READ_ONLY_ANALYZE','plan_fingerprint':'test',
      'options':{'quests':True,'palico_ids':[]},'catalog_sha256':'catalog'}
_expected_plan(plan,dict(plan))
print('PASS v0.6.3 plan recognized by current patch engine',flush=True)
