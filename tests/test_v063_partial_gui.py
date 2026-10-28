"""One explicit Apply confirmation covers partial results (no approval checkbox)."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import time
import desktop_app as d


def pump(gui,condition,limit=8):
    end=time.monotonic()+limit
    while time.monotonic()<end:
        gui.update()
        if condition():return
        time.sleep(.025)
    raise AssertionError('UI failed to progress')


def synthetic(probe=False):
    rec={'id':'maki','slot':0,'status':'preserved_by_choice' if probe else 'protected_custom_text',
         'reason':'custom user nickname','name':'ｍａｋｉ','proposed_english_name':'ｍａｋｉ'}
    q={'id':'m60031.mib','slot':0,'status':'eligible_translation','title':'神への挑戦',
       'proposed_english_title':'Challenging a God'}
    return {'catalog_quality':{'errors':[]},'options':{'quests':True,'palico_ids':['maki'],'hired_palicoes':False},
       'plan_fingerprint':'partialtest','save_sets':[{'save_set':'.','containers':{
       'ULJM05800QST':{'status':'validated','quest_inventory':{'occupied_slots':1,'records':[q]}},
       'ULJM05800':{'status':'validated','downloaded_palico_references':['o00003.dlo'],
                   'palico_inventory':{'records':[rec]}}}}]}


def run():
    with TemporaryDirectory() as td:
        source=Path(td)/'SAVEDATA';source.mkdir()
        app=d.Desktop()
        try:
            app.source.set(str(source))
            with patch.object(d,'analyze',lambda *args:synthetic(True)), \
                 patch.object(d,'analyze_outputs',lambda *args:(synthetic(False),Path(td)/'p.json',Path(td)/'r.html')):
                app._next();pump(app,lambda:app.available_palico_ids is not None)
                app.preset.set('all');app._apply_preset()
                assert app.palico_vars['maki'].get()
                app._next();pump(app,lambda:app.plan is not None)
            assert len(app.omissions)==1
            assert app.next.instate(['!disabled'])
            assert not [w for w in app.approval.winfo_children() if w.winfo_class()=='TCheckbutton']
            messages=[];partial_flags=[]
            def capture_question(title,text,parent=None):
                messages.append(text);return True
            def mock_execute(source,output,plan,partial):
                partial_flags.append(partial);return {'output':str(output)}
            with patch.object(d.messagebox,'askyesno',capture_question),patch.object(d,'execute',mock_execute):
                app.mode.set('export');app._render_approval()
                app._next();pump(app,lambda:app.step==3)
            assert partial_flags==[True],partial_flags
            assert len(messages)==1 and 'PARTIAL' in messages[0]
            print('PASS partial localized wizard: single explicit confirmation; no checkbox; partial=True passed to writer',flush=True)
        finally:
            try:app.destroy()
            except Exception:pass

if __name__=='__main__':run()
