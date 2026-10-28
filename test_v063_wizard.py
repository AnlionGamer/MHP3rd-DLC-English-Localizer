"""GUI tests with synthetic DLC inventories; no game files are touched."""
import tkinter as tk
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
import time
import desktop_app as d


def pump(w, condition, timeout=7):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        w.update()
        if condition():return
        time.sleep(.025)
    raise AssertionError('Timed out waiting for GUI state')


def plan(ids, quests=66, eligible=True):
    return {'catalog_quality':{'errors':[]},'options':{'quests':True,'palico_ids':list(ids),'hired_palicoes':False},
            'plan_fingerprint':'synthetic', 'save_sets':[{'save_set':'.','containers':{
             'ULJM05800QST':{'status':'validated','encryption':'PSP mode 5', 'quest_inventory':{
               'occupied_slots':quests, 'records':[{'id':f'm6{i:04}.mib','slot':i,'status':'eligible_translation',
                 'title':'日本語','proposed_english_title':'English'} for i in range(quests)]}},
             'ULJM05800':{'status':'validated','encryption':'PSP mode 5',
               'downloaded_palico_references':[f'o{i:05}.dlo' for i in range(len(ids))],
               'palico_inventory':{'records':[{'id':id,'slot':i,'name':'カナ','status':'preserved_by_choice',
                 'proposed_english_name':'Name'} for i,id in enumerate(ids)]}}}}]}


def check_inventory(ids,mode,window=(800,590)):
    with TemporaryDirectory() as td:
        source=Path(td)/'SAVEDATA';source.mkdir()
        app=d.Desktop();app.geometry(f'{window[0]}x{window[1]}')
        try:
            app.source.set(str(source));app.update()
            with patch.object(d,'analyze',lambda *args:plan(ids)), \
                 patch.object(d,'analyze_outputs',lambda *args:(plan(ids),Path(td)/'private.json',Path(td)/'report.html')):
                app._next();pump(app,lambda: app.step==1 and app.available_palico_ids is not None)
                assert app.available_palico_ids==set(ids)
                summary=app.inventory_status.cget('text')
                assert f'{len(ids)} of 5' in summary,summary
                assert 'does not download' in app.page.winfo_children()[1].cget('text').lower()
                app.preset.set('all');app._apply_preset()
                chosen={k for k,v in app.palico_vars.items() if v.get()}
                assert chosen==set(ids),(ids,chosen)
                if not ids:assert app._hired_button.instate(['disabled'])
                app.preset.set('custom');app._apply_preset()
                assert len([w for w in app._palico_choices.winfo_children() if isinstance(w,tk.Widget)])==6
                enabled=[]
                for w in app._palico_choices.winfo_children():
                    if hasattr(w,'instate') and w.winfo_class()=='TCheckbutton' and '→' in w.cget('text'):
                        if w.instate(['!disabled']):enabled.append(w)
                        else:assert '(not found)' in w.cget('text')
                assert len(enabled)==len(ids)
                if ids:app.preset.set('all');app._apply_preset()
                else:app.preset.set('quests');app._apply_preset()
                app._next();pump(app,lambda:app.plan is not None)
                assert app.step==2
                assert not any(isinstance(w,tk.Widget) and w.winfo_class()=='TCheckbutton'
                               for w in app.approval.winfo_children()),'Redundant install checkbox returned'
                assert app.next.instate(['!disabled'])
                assert app.next.winfo_rooty()+app.next.winfo_height()<=app.winfo_rooty()+app.winfo_height()
                if mode=='export':app.mode.set('export');app._render_approval()
                with patch.object(d.messagebox,'askyesno',return_value=True), \
                     patch.object(d,'execute',lambda src,out,pl,partial:{'output':str(out)}), \
                     patch.object(d,'install_verified_zip',lambda src,pkg,pl,backup:{'result':'installed','backup':str(backup),'package':str(pkg)}):
                    app._next();pump(app,lambda:app.step==3)
                assert app.finished_result['result']==('installed' if mode=='install' else 'exported')
                assert app.next.cget('text')=='Finish & Close'
                app._next()
                print('PASS inventory, no extra checkbox, '+mode, len(ids),'installed Palicoes',window,flush=True)
        finally:
            try:app.destroy()
            except tk.TclError:pass


def check_bad_source():
    with TemporaryDirectory() as td:
        src=Path(td)/'SAVEDATA';src.mkdir();app=d.Desktop()
        try:
            app.source.set(str(src))
            with patch.object(d,'analyze',side_effect=ValueError('No MHP3rd DLC present')), \
                 patch.object(d.messagebox,'showerror',return_value=None):
                app._next();pump(app,lambda:app.inventory_error is not None)
            assert app.next.instate(['disabled'])
            assert 'Could not check' in app.inventory_status.cget('text')
            print('PASS invalid save cannot advance to Apply',flush=True)
        finally:app.destroy()

if __name__=='__main__':
    allids=[p['id'] for p in d.load_catalog()[0]['palicoes']]
    check_inventory([], 'install')
    check_inventory(allids[:2], 'export', (760,540))
    check_inventory(allids, 'install', (1120,740))
    check_bad_source()
