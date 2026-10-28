#!/usr/bin/env python3
"""Simple one-time guided MHP3rd DLC localization, Tk desktop UI.

Uses the same validated analyzer and patch writer as v0.5.1; installation into
PPSSPP is optional and explicitly authorized after independent verification and
recovery backup. The app only closes on Finish or explicit cancellation.
"""
from __future__ import annotations
import datetime
import json
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import uuid
import webbrowser

from analyze_dlc import analyze, load_catalog
from start_analyzer import discover_sources
from report_privacy import redact_report
from html_report import render_html
from patch_dlc import execute
from safe_install import install_verified_zip
from recovery import pending_for_source, restore_pending

VERSION='1.0.0'
BG='#f3f6f9'; WHITE='#ffffff'; INK='#193047'; MUTED='#5a6b7d'
BLUE='#1263a5'; BLUE_HOVER='#0b4d88'; BORDER='#c8d5e0'; GREEN='#177451'


def default_base()->Path:
    # User-private local app data avoids assuming Documents is not OneDrive-synced.
    if os.name=='nt' and os.environ.get('LOCALAPPDATA'):
        return Path(os.environ['LOCALAPPDATA'])/'MHP3rd_DLC_Localizer'
    return Path.home()/'.local'/'share'/'MHP3rd_DLC_Localizer'


def record_is_selected(plan:dict, inventory:str, record:dict)->bool:
    """Unselected or missing DLC must not trigger an Apply warning.

    All records remain in the complete technical/HTML reports. The short
    wizard review includes only actual selected categories and known Palicoes.
    """
    options=plan.get('options',{})
    if inventory=='quest_inventory':return bool(options.get('quests',False))
    selected=set(options.get('palico_ids',[]))
    if inventory=='hired_palico_inventory' and not options.get('hired_palicoes',False):return False
    return record.get('id') in selected


def omissions_in_plan(plan:dict)->list[dict]:
    result=[]
    for item in plan['save_sets']:
        for folder,container in item['containers'].items():
            for key in ('quest_inventory','palico_inventory','hired_palico_inventory'):
                for record in container.get(key,{}).get('records',[]):
                    if record_is_selected(plan,key,record) and record['status'].startswith(('skipped','blocked','protected')):
                        result.append({'folder':folder,**record})
    return result


def summary_of(plan:dict)->dict:
    counts={};modes=[]
    for item in plan['save_sets']:
        for folder,container in item['containers'].items():
            modes.append(f'{folder}: {container.get("encryption","unknown")} ({container["status"]})')
            for key in ('quest_inventory','palico_inventory','hired_palico_inventory'):
                for record in container.get(key,{}).get('records',[]):
                    if not record_is_selected(plan,key,record):continue
                    status=record['status'];counts[status]=counts.get(status,0)+1
    return {'counts':counts,'modes':modes,'omissions':omissions_in_plan(plan)}


def analyze_outputs(src:Path,quest:bool,palicoes:set[str],reportdir:Path,hired:bool=False):
    plan=analyze(src,quest,palicoes,hired)
    if src.is_dir() and (src.resolve()==reportdir.resolve() or src.resolve() in reportdir.resolve().parents):
        raise ValueError('Reports must be outside the PPSSPP save directory')
    reportdir.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_'+uuid.uuid4().hex[:5]
    technical=reportdir/f'Analysis_{stamp}_PRIVATE.json'
    share=reportdir/f'Analysis_{stamp}_SHAREABLE.html'
    try:
        with technical.open('x',encoding='utf-8') as handle:json.dump(plan,handle,ensure_ascii=False,indent=2)
        with share.open('x',encoding='utf-8') as handle:handle.write(render_html(redact_report(plan)))
    except BaseException:
        technical.unlink(missing_ok=True);share.unlink(missing_ok=True);raise
    return plan,technical,share


def timestamp()->str:
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_'+uuid.uuid4().hex[:5]


class Desktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f'MHP3rd DLC Localizer v{VERSION}')
        # Size to the available monitor, not a hard-coded screen resolution.
        sw,sh=self.winfo_screenwidth(),self.winfo_screenheight()
        ww=min(1120,max(760,int(sw*.76)))
        hh=min(780,max(570,int(sh*.79)))
        self.geometry(f'{min(ww,sw)}x{min(hh,sh)}')
        self.minsize(740,520)
        self.configure(bg=BG)
        self.protocol('WM_DELETE_WINDOW',self._close)
        self.queue=queue.Queue();self.busy=False;self.step=0
        self.catalog=load_catalog()[0]
        self.found=discover_sources()
        self.source=tk.StringVar(value=str(self.found[0]) if len(self.found)==1 else '')
        self.preset=tk.StringVar(value='quests')
        self.localize_quests=tk.BooleanVar(value=True)
        self.palico_vars={p['id']:tk.BooleanVar(value=False) for p in self.catalog['palicoes']}
        self.hired=tk.BooleanVar(value=False)
        self.mode=tk.StringVar(value='install' if self.found else 'export')
        self.output_dir=tk.StringVar(value=str(default_base()/'Outputs'))
        self.status=tk.StringVar(value='')
        self.plan=None;self.source_snapshot=None;self.report_path=None;self.omissions=[]
        self.discovered=None;self.available_palico_ids=None;self.inventory_status=None;self.inventory_error=None
        self.technical_path=None;self.finished_result=None;self.records={}
        self._style();self._layout()
        for variable in (self.source,self.preset,self.localize_quests,self.hired,*self.palico_vars.values()):
            variable.trace_add('write',self._invalidate)
        self.source.trace_add('write',self._reset_discovery)
        self.show_step(0)
        self._poll_job=self.after(125,self._poll)

    def _style(self):
        st=ttk.Style(self)
        if 'clam' in st.theme_names():st.theme_use('clam')
        st.configure('TFrame',background=BG);st.configure('White.TFrame',background=WHITE)
        st.configure('TLabel',background=BG,foreground=INK,font=('Segoe UI',11))
        st.configure('Small.TLabel',background=BG,foreground=MUTED,font=('Segoe UI',10))
        st.configure('Title.TLabel',background=BG,foreground=INK,font=('Segoe UI Semibold',21))
        st.configure('Heading.TLabel',background=BG,foreground=INK,font=('Segoe UI Semibold',14))
        st.configure('SmallWhite.TLabel',background=WHITE,foreground=MUTED,font=('Segoe UI',11))
        st.configure('TCheckbutton',background=BG,foreground=INK,font=('Segoe UI',11))
        st.configure('TRadiobutton',background=BG,foreground=INK,font=('Segoe UI',11))
        st.configure('TButton',padding=(10,7),font=('Segoe UI',11))
        st.configure('Next.TButton',padding=(22,11),font=('Segoe UI Semibold',12),background=BLUE,foreground='white')
        st.map('Next.TButton',background=[('active',BLUE_HOVER),('disabled','#b6c3ce')],foreground=[('disabled','white')])
        st.configure('Treeview',rowheight=29,font=('Segoe UI',9),background=WHITE,fieldbackground=WHITE)
        st.configure('Treeview.Heading',font=('Segoe UI Semibold',9),background='#e8edf3')
        st.map('Treeview',background=[('selected','#c4dff1')],foreground=[('selected',INK)])

    def _layout(self):
        base=ttk.Frame(self,padding=(18,12,18,10));base.pack(fill='both',expand=True)
        self.base=base
        ttk.Label(base,text='Monster Hunter Portable 3rd',style='Small.TLabel').pack(anchor='w')
        ttk.Label(base,text='DLC English Localizer',style='Title.TLabel').pack(anchor='w')
        self.stepbar=ttk.Frame(base);self.stepbar.pack(fill='x',pady=(10,4))
        self.steps=[]
        for i,label in enumerate(('1  Find saves','2  Choose DLC','3  Review & apply')):
            frame=tk.Label(self.stepbar,text=label,font=('Segoe UI Semibold',10),padx=8,pady=6,
                           bg='#e8edf2',fg=MUTED,bd=0)
            frame.pack(side='left',fill='x',expand=True,padx=(0,5));self.steps.append(frame)
        ttk.Separator(base).pack(fill='x',pady=(3,7))
        # Reserve the footer FIRST so action buttons can never be pushed offscreen
        # by a long review table or a smaller resized window.
        self.foot=ttk.Frame(base);self.foot.pack(side='bottom',fill='x',pady=(6,0))
        self.page=ttk.Frame(base);self.page.pack(fill='both',expand=True)
        self.back=ttk.Button(self.foot,text='Back',command=self._back)
        self.back.pack(side='left')
        self.next=ttk.Button(self.foot,text='Next',style='Next.TButton',command=self._next)
        self.next.pack(side='right')
        self.cancel=ttk.Button(self.foot,text='Cancel',command=self._close)
        self.cancel.pack(side='right',padx=10)
        self.busybar=ttk.Progressbar(self.foot,mode='indeterminate',length=160)
        # Progress bar appears only during background analysis / localization.
        self.status_label=ttk.Label(self.foot,textvariable=self.status,style='Small.TLabel')
        self.status_label.pack(side='bottom',anchor='w',fill='x',pady=(4,0))

    def _clear(self):
        for widget in self.page.winfo_children():widget.destroy()

    def _heading(self,title,subtitle):
        ttk.Label(self.page,text=title,style='Heading.TLabel').pack(anchor='w',pady=(0,4))
        ttk.Label(self.page,text=subtitle,style='Small.TLabel',wraplength=700,justify='left').pack(anchor='w',pady=(0,9))

    def show_step(self,step:int):
        self.step=step;self._clear()
        for i,frame in enumerate(self.steps):
            frame.configure(bg=(BLUE if i==step and step<3 else '#dcebe6' if i<step else '#e8edf2'),
                            fg=('white' if i==step and step<3 else GREEN if i<step else MUTED))
        self.back.configure(state='normal' if 0<step<3 else 'disabled')
        self.cancel.configure(text='Cancel' if step<3 else 'Close')
        if step==0:
            self._heading('Find your game saves','The app can automatically locate PPSSPP. It recognizes MHP3rd DLC inside SAVEDATA, PSP and PPSSPP folders.')
            if len(self.found)==1:ttk.Label(self.page,text='PPSSPP saves detected',font=('Segoe UI Semibold',11),foreground=GREEN).pack(anchor='w',pady=(0,8))
            elif len(self.found)>1:ttk.Label(self.page,text='Multiple PPSSPP installations found — select the correct one using Detect again.',font=('Segoe UI Semibold',10),foreground=INK,wraplength=820).pack(anchor='w',pady=(0,8))
            ttk.Label(self.page,text='Save directory or backup ZIP').pack(anchor='w')
            srcrow=ttk.Frame(self.page);srcrow.pack(fill='x',pady=(6,4))
            ttk.Entry(srcrow,textvariable=self.source,font=('Segoe UI',11)).pack(fill='x',expand=True)
            # Browsing controls get a separate row: no forced window width.
            browse=ttk.Frame(self.page);browse.pack(fill='x',pady=(4,6))
            ttk.Button(browse,text='Auto-detect',command=self._detect).pack(side='left',padx=(0,8))
            ttk.Button(browse,text='Browse folder',command=self._browse_folder).pack(side='left',padx=(0,8))
            ttk.Button(browse,text='Browse ZIP',command=self._browse_zip).pack(side='left')
            ttk.Button(self.page,text='Restore an interrupted installation…',command=self._recover).pack(anchor='w',pady=(4,0))
            ttk.Label(self.page,text='No game files are changed while you make your choices. You will review all changes before approving them.',
                      style='Small.TLabel',wraplength=780).pack(anchor='w',pady=(10,0))
            self.next.configure(text='Next: Choose DLC  ›',state='normal')
            self.status.set('Step 1 of 3 — select your PPSSPP save location.')
        elif step==1:
            self._heading('Choose what to localize',
                'Only DLC already present in the selected save can be translated. This program does not download or install missing DLC.')
            self.inventory_status=ttk.Label(self.page,text='Checking installed DLC in your save…',style='Heading.TLabel')
            self.inventory_status.pack(anchor='w',pady=(2,12))
            options_area=ttk.Frame(self.page);options_area.pack(fill='both',expand=True)
            canvas=tk.Canvas(options_area,highlightthickness=0,borderwidth=0,bg=BG)
            scrollbar=ttk.Scrollbar(options_area,orient='vertical',command=canvas.yview)
            canvas.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
            inner=ttk.Frame(canvas)
            window=canvas.create_window((0,0),window=inner,anchor='nw')
            inner.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
            self._options_canvas=canvas
            def wheel(event):
                canvas.yview_scroll(-int(event.delta/120) if event.delta else 0,'units')
            canvas.bind('<Enter>',lambda e:canvas.bind_all('<MouseWheel>',wheel))
            canvas.bind('<Leave>',lambda e:canvas.unbind_all('<MouseWheel>'))
            for val,label,info in (
                ('quests','Installed DLC quests only','Translate recognized quests already in this save; no missing quests are added.'),
                ('all','All recognized installed DLC — recommended','Translate recognized installed quests and any supported promotional Palicoes actually found in this save.'),
                ('custom','Select individual content','Choose installed quests and specific recognized promotional Palicoes below.')):
                line=ttk.Frame(inner);line.pack(fill='x',pady=(0,9))
                ttk.Radiobutton(line,text=label,variable=self.preset,value=val,command=self._apply_preset).pack(anchor='w')
                ttk.Label(line,text=info,style='Small.TLabel').pack(anchor='w',padx=25)
            self._palico_choices=ttk.Frame(inner);self._palico_choices.pack(fill='x',pady=(4,4))
            self._populate_palico_choices()
            ttk.Separator(inner).pack(fill='x',pady=(5,7))
            self._hired_button=ttk.Checkbutton(inner,text='Also update matching promotional Palicoes already recruited (optional)',variable=self.hired)
            self._hired_button.pack(anchor='w')
            ttk.Label(inner,text='Only positively identified copies of selected Palicoes are updated. Customized names and comments, stats, skills and equipment are protected.',
                      style='Small.TLabel',wraplength=690).pack(anchor='w',padx=25,pady=(3,0))
            self._apply_preset()
            self.next.configure(text='Next: Review changes  ›',state='disabled')
            self.status.set('Step 2 of 3 — identifying installed DLC before making a selection.')
            if self.discovered is None:
                self._start_discovery()
            else:
                self._show_discovery()
        elif step==2:
            self.source_snapshot=Path(self.source.get().strip().strip('\"')).expanduser()
            self._heading('Review your changes','The game data was analyzed without modifications. When you approve, we verify the output and preserve an original recovery backup before installing.')
            self.count_label=ttk.Label(self.page,text='Preparing read-only preview…',style='Heading.TLabel');self.count_label.pack(anchor='w',pady=(0,4))
            self.mode_frame=ttk.Frame(self.page);self.mode_frame.pack(fill='x',pady=(0,4))
            self._mode_controls()
            self.review_frame=ttk.Frame(self.page);self.review_frame.pack(fill='both',expand=True)
            self.approval=ttk.Frame(self.page);self.approval.pack(fill='x',pady=(4,2))
            self.next.configure(text='Apply English Localization',state='disabled')
            self.status.set('Analyzing game data and creating a clear change preview…')
            self._start_analyze()
        elif step==3:
            self.back.configure(state='disabled')
            self._heading('Localization complete','The app has finished the approved operation. Your results and recovery files are shown below.')
            result=self.finished_result
            if result['result']=='installed':
                headline='English DLC installed successfully'
                details='Localized game data was installed into PPSSPP. A verified backup of the original save files was kept for recovery.'
            elif result['result']=='already':
                headline='Your selected DLC is already localized'
                details='No files needed to be changed. Your game saves are unchanged.'
            else:
                headline='Localized files prepared successfully'
                details='Your game saves are unchanged. The new ZIP is ready for manual installation or testing; it has not been installed into PPSSPP.'
            ttk.Label(self.page,text=headline,style='Heading.TLabel',foreground=GREEN).pack(anchor='w',pady=(10,9))
            ttk.Label(self.page,text=details,wraplength=790,justify='left').pack(anchor='w',pady=(0,18))
            if result.get('backup'):
                ttk.Label(self.page,text='Recovery backup',font=('Segoe UI Semibold',10)).pack(anchor='w')
                ttk.Label(self.page,text=result['backup'],wraplength=835,style='Small.TLabel').pack(anchor='w',pady=(3,12))
            if result.get('package'):
                ttk.Label(self.page,text='Verified localization package',font=('Segoe UI Semibold',10)).pack(anchor='w')
                ttk.Label(self.page,text=result['package'],wraplength=835,style='Small.TLabel').pack(anchor='w',pady=(3,12))
            ttk.Button(self.page,text='Open results folder',command=self._open_results).pack(anchor='w',pady=(5,0))
            self.next.configure(text='Finish & Close',state='normal')
            self.status.set('Finished. Select Finish & Close to exit the program.')

    def _invalidate(self,*_):
        self.plan=None;self.source_snapshot=None

    def _reset_discovery(self,*_):
        self.discovered=None;self.available_palico_ids=None;self.inventory_error=None

    def _start_discovery(self):
        src=Path(self.source.get().strip().strip('"')).expanduser()
        self._start_job('discover',lambda:analyze(src,True,set(),False),
                        'Reading the installed quest and promotional Palico inventory…')

    def _show_discovery(self):
        if self.step!=1:return
        if self.inventory_error:
            self.inventory_status.configure(text='Could not check the DLC in this save. Return to Find Saves and select a valid source.',
                                            foreground='#9a3412')
            self.next.configure(state='disabled')
            self.status.set('DLC inventory check failed: '+self.inventory_error)
            return
        data=self.discovered
        if data is None:return
        ids=set();q_count=0;q_recognized=0;unrecognized=0
        for item in data.get('save_sets',[]):
            for folder,container in item['containers'].items():
                if folder=='ULJM05800QST':
                    inv=container.get('quest_inventory',{})
                    q_count+=inv.get('occupied_slots',0)
                    q_recognized+=sum(1 for r in inv.get('records',[]) if r.get('id') and not r.get('status','').startswith(('skipped','blocked')))
                elif folder=='ULJM05800':
                    if container.get('status')=='validated' and container.get('downloaded_palico_references'):
                        for r in container.get('palico_inventory',{}).get('records',[]):
                            if r.get('id') and not r.get('status','').startswith(('skipped','blocked','protected')):
                                ids.add(r['id'])
        self.available_palico_ids=ids
        missing=5-len(ids)
        self.inventory_status.configure(text=(f'Found {q_count} installed quests ({q_recognized} recognized)  ·  '
            f'{len(ids)} of 5 known promotional Palicoes recognized'),foreground=GREEN if ids or q_recognized else INK)
        # The list is informational. No unknown or missing record will be installed.
        self._apply_preset()
        self._update_hired_enabled()
        self.next.configure(state='normal')
        self.status.set(f'Step 2 of 3 — select from the DLC currently present. {missing} known Palico(s) not recognized in this save.')

    def _update_hired_enabled(self):
        if not hasattr(self,'_hired_button') or not self._hired_button.winfo_exists():return
        has_selected=any(v.get() for v in self.palico_vars.values())
        if not has_selected:self.hired.set(False)
        self._hired_button.configure(state='normal' if has_selected else 'disabled')

    def _apply_preset(self):
        val=self.preset.get()
        if val not in ('quests','all'):
            if hasattr(self,'_palico_choices') and self._palico_choices.winfo_exists():self._populate_palico_choices()
            return
        enable=(val=='all')
        for pid,item in self.palico_vars.items():
            item.set(enable and (self.available_palico_ids is None or pid in self.available_palico_ids))
        self.localize_quests.set(True)
        if not enable:self.hired.set(False)
        if hasattr(self,'_palico_choices') and self._palico_choices.winfo_exists():
            self._populate_palico_choices()
        self._update_hired_enabled()

    def _populate_palico_choices(self):
        for w in self._palico_choices.winfo_children():w.destroy()
        if self.preset.get()!='custom':return
        if self.available_palico_ids is None:
            ttk.Label(self._palico_choices,text='Checking which promotional Palicoes are installed…',style='Small.TLabel').pack(anchor='w')
            return
        ttk.Checkbutton(self._palico_choices,text='Translate installed DLC quests',variable=self.localize_quests).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,6))
        for i,p in enumerate(self.catalog['palicoes']):
            present=p['id'] in self.available_palico_ids
            if not present:self.palico_vars[p['id']].set(False)
            ttk.Checkbutton(self._palico_choices,text=p['ja']['name']+' → '+p['en']['name']+('  (not found)' if not present else ''),
                            variable=self.palico_vars[p['id']],command=self._update_hired_enabled,
                            state='normal' if present else 'disabled').grid(row=1+i//2,column=i%2,sticky='w',padx=(0,24),pady=4)

    def _detect(self):
        results=discover_sources();self.found=results
        if not results:
            messagebox.showinfo('Saves not found','Browse to the PPSSPP SAVEDATA directory or select an existing backup ZIP.',parent=self);return
        if len(results)==1:self.source.set(str(results[0]));return
        win=tk.Toplevel(self);win.title('Choose PPSSPP installation');win.geometry('750x310');win.transient(self);win.grab_set()
        ttk.Label(win,text='Select the PPSSPP save directory:',padding=(14,14)).pack(anchor='w')
        select=tk.Listbox(win,font=('Consolas',10));select.pack(fill='both',expand=True,padx=14)
        for p in results:select.insert('end',str(p))
        select.selection_set(0)
        def choose():
            if select.curselection():self.source.set(str(results[select.curselection()[0]]))
            win.destroy()
        ttk.Button(win,text='Use this directory',command=choose).pack(pady=10)

    def _browse_folder(self):
        path=filedialog.askdirectory(parent=self,title='Select PPSSPP SAVEDATA / PSP / PPSSPP directory')
        if path:self.source.set(path)

    def _browse_zip(self):
        path=filedialog.askopenfilename(parent=self,title='Select game save backup ZIP',filetypes=[('ZIP archives','*.zip')])
        if path:self.source.set(path)

    def _recover(self):
        if self.busy:return
        current=Path(self.source.get().strip().strip('"')).expanduser()
        pending=[]
        if current.is_dir():
            try:pending=pending_for_source(current)
            except (OSError,ValueError):pass
        if not pending:
            chosen=filedialog.askdirectory(parent=self,title='Select SAVEDATA folder requiring recovery')
            if not chosen:return
            target=Path(chosen)
            try:pending=pending_for_source(target)
            except (OSError,ValueError) as exc:
                messagebox.showerror('Recovery not found',str(exc),parent=self);return
        if len(pending)!=1:
            messagebox.showerror('Recovery selection',
                ('No interrupted installation found in that folder.' if not pending else
                 'Multiple interrupted installations found. Select one SAVEDATA folder at a time.'),parent=self)
            return
        journal=pending[0]
        if not messagebox.askyesno('Restore original DLC save files',
                'A previously interrupted localization has a recovery record in:\n'+str(journal.parent)+
                '\n\nRestore the originally backed-up DLC save files? PPSSPP must be closed. Other files will be left unchanged.',parent=self):return
        self._start_job('recover',lambda:restore_pending(journal),'Restoring original files from a verified backup…')

    def _mode_controls(self):
        if self.source_snapshot and self.source_snapshot.is_dir():
            self.mode.set('install')
            ttk.Radiobutton(self.mode_frame,text='Install directly into PPSSPP (with automatic verified backup)',
                            variable=self.mode,value='install',command=self._render_approval).pack(anchor='w',pady=(2,2))
            ttk.Radiobutton(self.mode_frame,text='Prepare ZIP only — keep my current game saves untouched',
                            variable=self.mode,value='export',command=self._render_approval).pack(anchor='w',pady=(2,2))
        else:
            self.mode.set('export')
            ttk.Label(self.mode_frame,text='Backup ZIP selected: the app will prepare a verified package. It will not guess where to install it.',style='Small.TLabel').pack(anchor='w')

    def _start_job(self,name,job,description):
        self.busy=True;self._button_state()
        self.busybar.pack(side='right',padx=8);self.busybar.start(11);self.status.set(description)
        def runner():
            try:self.queue.put((name,'ok',job()))
            except Exception as exc:self.queue.put((name,'error',str(exc)))
        threading.Thread(target=runner,daemon=True,name='MHP3rd-'+name).start()

    def _finish_job(self):
        self.busy=False;self.busybar.stop();self.busybar.pack_forget();self._button_state()

    def _button_state(self):
        self.next.configure(state='disabled' if self.busy else 'normal')
        self.back.configure(state='disabled' if self.busy or self.step in (0,3) else 'normal')
        self.cancel.configure(state='disabled' if self.busy else 'normal')

    def _start_analyze(self):
        src=Path(self.source.get().strip().strip('"')).expanduser()
        self.source_snapshot=src
        palicoes={k for k,v in self.palico_vars.items() if v.get()}
        quests=self.localize_quests.get();hired=self.hired.get()
        job=lambda:analyze_outputs(src,quests,palicoes,default_base()/'Reports',hired)
        self._start_job('analyze',job,'Analyzing installed quests and Palicoes. Original files remain unchanged…')

    def _render_approval(self):
        if not hasattr(self,'approval') or not self.approval.winfo_exists():return
        for w in self.approval.winfo_children():w.destroy()
        if self.mode.get()=='install':
            ttk.Label(self.approval,text='Close PPSSPP before applying. The installer also checks that PPSSPP is not running and creates a verified recovery backup first.',
                      style='Small.TLabel',wraplength=840).pack(anchor='w',pady=(0,3))
        else:
            ttk.Label(self.approval,text='Export only: a verified ZIP will be created. Your PPSSPP saves will not be changed.',
                      style='Small.TLabel').pack(anchor='w')
        if self.omissions:
            ttk.Label(self.approval,text=f'{len(self.omissions)} selected record(s) cannot be changed safely and will be left untouched. The confirmation dialog will ask you to approve this partial result.',
                      foreground='#9a3412',wraplength=840).pack(anchor='w',pady=(6,0))
        self._refresh_apply()

    def _refresh_apply(self):
        if self.step!=2 or self.busy or self.plan is None:return
        valid=not self.plan['catalog_quality']['errors']
        self.next.configure(state='normal' if valid else 'disabled')

    def _render_review(self):
        info=summary_of(self.plan)
        self.omissions=info['omissions']
        eligible=sum(n for k,n in info['counts'].items() if k.startswith('eligible'))
        already=info['counts'].get('already_localized',0)
        self.eligible_count=eligible
        self.count_label.configure(text=f'{eligible} changes ready   ·   {already} already localized   ·   {len(self.omissions)} skipped/protected')
        if eligible==0 and not self.omissions:
            self.finished_result={'result':'already'}
            self.show_step(3);return
        body=self.review_frame
        cols=('type','old','new','status')
        grid=ttk.Treeview(body,columns=cols,show='headings',height=4)
        for col,title,width in (('type','Kind',125),('old','Current (Name · Meowster)',240),('new','After (Name · Meowster)',260),('status','Decision',170)):
            grid.heading(col,text=title);grid.column(col,width=width,minwidth=80,stretch=col in ('old','new'))
        vbar=ttk.Scrollbar(body,orient='vertical',command=grid.yview)
        hbar=ttk.Scrollbar(body,orient='horizontal',command=grid.xview)
        grid.configure(yscrollcommand=vbar.set,xscrollcommand=hbar.set)
        vbar.pack(side='right',fill='y');hbar.pack(side='bottom',fill='x')
        grid.pack(side='left',fill='both',expand=True)
        self.records={}
        for item in self.plan['save_sets']:
            for folder,container in item['containers'].items():
                inventories=([('Quest','quest_inventory')] if folder=='ULJM05800QST' else
                             [('Download Palico','palico_inventory'),('Recruited Palico','hired_palico_inventory')])
                for kind,key in inventories:
                    for rec in container.get(key,{}).get('records',[]):
                        if not record_is_selected(self.plan,key,rec):continue
                        old=rec.get('title',rec.get('name',''))
                        new=rec.get('proposed_english_title',rec.get('proposed_english_name',''))
                        if kind!='Quest':
                            before=rec.get('original_creator','')
                            after=rec.get('proposed_english_owner','')
                            if before:old+=f'  ·  {before}'
                            if after:new+=f'  ·  {after}'
                        key_id=grid.insert('',tk.END,values=(kind,old,new,rec['status'].replace('_',' ')))
                        self.records[key_id]=rec
        controls=ttk.Frame(self.page);controls.pack(fill='x',pady=(5,0))
        ttk.Button(controls,text='View full translation report',command=self._open_report).pack(side='left')
        ttk.Label(controls,text='Original fullwidth Meowsters stay intact; Japanese names are romanized. Stats and gear remain unchanged.',style='Small.TLabel').pack(side='left',padx=10)
        if self.plan['catalog_quality']['errors']:
            messagebox.showerror('Translation catalog problem','Catalog validation failed; installation is blocked.',parent=self)
        self._render_approval()
        self.status.set('Step 3 of 3 — review the proposed localization, then select Apply English Localization.')

    def _open_report(self):
        if self.report_path and self.report_path.exists():webbrowser.open(self.report_path.resolve().as_uri())

    def _apply(self):
        if self.plan is None or self.busy:return
        selected=sorted(k for k,v in self.palico_vars.items() if v.get())
        kind='Install to PPSSPP' if self.mode.get()=='install' else 'Prepare ZIP (no installation)'
        message=(f'Operation: {kind}\n\nDLC quests: {"Yes" if self.localize_quests.get() else "No"}\n'
                 f'Downloadable Palicoes: {len(selected)}\n'
                 f'Update existing recruited copies: {"Yes" if self.hired.get() else "No"}\n'
                 f'Skipped/protected: {len(self.omissions)}\n\n')
        if self.omissions:
            message+=f'This will be a PARTIAL localization. {len(self.omissions)} selected record(s) cannot be changed safely and will remain untouched.\n\n'
        message+=('Close PPSSPP before continuing. The installer will check that it is not running and will create a verified backup before installing. Original fullwidth Meowster names are preserved; Japanese-script Meowsters are romanized; custom labels stay protected.'
                  if self.mode.get()=='install' else 'The program will create a verified ZIP; PPSSPP saves will not be changed.')
        if not messagebox.askyesno('Apply English Localization',message+'\n\nContinue?',parent=self):return
        source=self.source_snapshot;plan=self.plan;partial=bool(self.omissions);mode=self.mode.get()
        file_stamp=timestamp()
        output=default_base()/'Outputs'/f'MHP3rd_Localized_{file_stamp}.zip'
        backup=default_base()/'Backups'/f'MHP3rd_Original_Backup_{file_stamp}.zip'
        def job():
            result=execute(source,output,plan,partial)
            if mode=='install':return install_verified_zip(source,Path(result['output']),plan,backup)
            return {'result':'exported','package':result['output']}
        self._start_job('apply',job,'Building, decoding and verifying localized DLC…')

    def _poll(self):
        try:
            while True:
                name,status,payload=self.queue.get_nowait()
                self._finish_job()
                if status=='error':
                    self.status.set('Operation stopped safely: '+payload)
                    messagebox.showerror('Cannot complete operation',payload+'\n\nReview the source and try again. The app has not silently ignored this error.',parent=self)
                    if name=='discover':
                        self.inventory_error=payload;self._show_discovery()
                    elif name=='analyze':self.show_step(1)
                    else:self._refresh_apply()
                elif name=='discover':
                    self.discovered=payload;self.inventory_error=None;self._show_discovery()
                elif name=='analyze':
                    self.plan,self.technical_path,self.report_path=payload
                    self._render_review()
                elif name=='recover':
                    messagebox.showinfo('Recovery successful',
                        'The original DLC save files have been restored and verified. The original recovery backup was retained.',parent=self)
                    self.discovered=None;self.plan=None;self.status.set('Original save files successfully restored.')
                elif name=='apply':
                    self.finished_result=payload
                    self.show_step(3)
        except queue.Empty:pass
        self._poll_job=self.after(125,self._poll)

    def _next(self):
        if self.busy:return
        if self.step==0:
            src=Path(self.source.get().strip().strip('"')).expanduser()
            if not src.exists():messagebox.showerror('Save folder not found','Choose a valid PPSSPP directory or existing backup ZIP.',parent=self);return
            if not (src.is_file() and src.suffix.lower()=='.zip' or src.is_dir()):
                messagebox.showerror('Unsupported source','Select a PPSSPP folder or a ZIP backup.',parent=self);return
            if src.is_dir():
                try:pending=pending_for_source(src)
                except (OSError,ValueError) as exc:
                    messagebox.showerror('Unsafe save selection',str(exc),parent=self);return
                if pending:
                    messagebox.showwarning('Restore before proceeding',
                        'An interrupted localization was detected. Use Restore an interrupted installation on this page before analyzing or applying changes.\n\n'+str(pending[0]),parent=self)
                    return
            self.show_step(1)
        elif self.step==1:
            if not self.localize_quests.get() and not any(v.get() for v in self.palico_vars.values()):
                messagebox.showwarning('Nothing selected','Choose quests or one or more promotional Palicoes.',parent=self);return
            self.show_step(2)
        elif self.step==2:self._apply()
        elif self.step==3:self._close()

    def _back(self):
        if not self.busy and 0<self.step<3:self.show_step(self.step-1)

    def _open_results(self):
        import os
        folder=default_base()/'Outputs'
        if not folder.exists():folder=default_base()
        try:
            if os.name=='nt':os.startfile(str(folder))
            else:webbrowser.open(folder.resolve().as_uri())
        except OSError as exc:messagebox.showerror('Cannot open folder',str(exc),parent=self)

    def _close(self):
        if self.busy:
            messagebox.showwarning('Operation in progress','Wait for the current verification/backup operation to finish.',parent=self);return
        if hasattr(self,'_poll_job'):
            try:self.after_cancel(self._poll_job)
            except tk.TclError:pass
        self.destroy()


def main():Desktop().mainloop()

if __name__=='__main__':main()
