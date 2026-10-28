#!/usr/bin/env python3
"""Windows-friendly console interface for auto-discovery or manual selection."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent


def _has_target(path:Path)->bool:
    try:
        return (path.is_dir() and any((path/x/'MHP3RD.BIN').is_file()
                                      for x in ('ULJM05800','ULJM05800QST')))
    except OSError:return False


def discover_sources(home:Path|None=None,environ:dict|None=None,app_dir:Path|None=None)->list[Path]:
    """Known PPSSPP locations, not a recursive/full-drive search."""
    home=home or Path.home()
    env=dict(os.environ if environ is None else environ)
    app_dir=app_dir or ROOT
    parents=[home/'Documents',home/'OneDrive'/'Documents',home/'OneDrive',
             home/'Saved Games',home,app_dir,app_dir.parent,Path.cwd()]
    if env.get('USERPROFILE'):parents.append(Path(env['USERPROFILE'])/'Documents')
    if env.get('APPDATA'):parents.append(Path(env['APPDATA']))
    if env.get('LOCALAPPDATA'):parents.append(Path(env['LOCALAPPDATA']))
    if env.get('PPSSPP_MEMSTICK'):parents.append(Path(env['PPSSPP_MEMSTICK']))
    suffixes=[Path('PPSSPP/PSP/SAVEDATA'),Path('PSP/SAVEDATA'),Path('memstick/PSP/SAVEDATA'),
              Path('SAVEDATA'),Path('.')]
    found={}
    for base in parents:
        for suffix in suffixes:
            candidate=base/suffix
            if _has_target(candidate):
                try:key=str(candidate.resolve()).casefold()
                except OSError:continue
                found[key]=candidate
    return sorted(found.values(),key=lambda p:str(p).casefold())


def _browse(kind:str)->Path|None:
    try:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk()
        root.withdraw()
        root.attributes('-topmost',True)
        try:
            if kind=='zip':
                result=filedialog.askopenfilename(title='Select PPSSPP save backup ZIP',
                      filetypes=[('ZIP archives','*.zip'),('All files','*.*')])
            else:
                result=filedialog.askdirectory(title='Select MHP3rd SAVEDATA / PSP / PPSSPP folder')
        finally:root.destroy()
        return Path(result) if result else None
    except Exception as e:
        print('Folder browser unavailable:',e)
        return None


def choose_source():
    while True:
        print('\nMHP3rd DLC Analyzer v0.4.1 — READ ONLY')
        print('  1. Auto-detect PPSSPP saves (recommended)')
        print('  2. Browse for a folder (MHP3rd, SAVEDATA, PSP or PPSSPP)')
        print('  3. Browse for a save backup ZIP')
        print('  4. Enter a folder/ZIP path manually')
        print('  5. Exit')
        try:option=input('Choose 1-5: ').strip()
        except EOFError:return None
        if option=='1':
            candidates=discover_sources()
            if not candidates:
                print('No standard PPSSPP save locations found. Choose Browse or Manual.')
                continue
            if len(candidates)==1:
                print('Detected:',candidates[0])
                return candidates[0]
            print('Found these SAVEDATA locations:')
            for i,p in enumerate(candidates,1):print(f'  {i}. {p}')
            try:selection=input('Select number (blank to cancel): ').strip()
            except EOFError:return None
            if selection.isdigit() and 1<=int(selection)<=len(candidates):return candidates[int(selection)-1]
        elif option in ('2','3'):
            picked=_browse('folder' if option=='2' else 'zip')
            if picked:return picked
            print('Nothing selected. You can also enter the full path manually.')
        elif option=='4':
            try:t=input('Enter full save ZIP or folder path: ').strip().strip('"')
            except EOFError:return None
            if t:return Path(os.path.expandvars(t)).expanduser()
        elif option=='5':return None
        else:print('Invalid selection.')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only analyzer launcher with save discovery')
    parser.add_argument('path',nargs='?',help='Drag-and-drop ZIP, SAVEDATA, PSP or PPSSPP folder')
    parser.add_argument('--auto',action='store_true',help='Auto-select a single detected save location')
    parser.add_argument('--discover',action='store_true',help='List found standard PPSSPP locations and exit')
    parser.add_argument('--no-quests',action='store_true')
    parser.add_argument('--palico',action='append',default=[])
    args=parser.parse_args(argv)
    if args.discover:
        for p in discover_sources():print(p)
        return 0
    if args.path:
        selected=Path(os.path.expandvars(args.path.strip('"'))).expanduser()
    elif args.auto:
        found=discover_sources()
        if len(found)!=1:
            print(f'Auto-detection found {len(found)} locations; select manually if zero or multiple.')
            for p in found:print(' ',p)
            return 2
        selected=found[0]
    else:selected=choose_source()
    if selected is None:
        print('Canceled. No save files or reports changed.')
        return 0
    if not selected.exists():
        print('Selected path does not exist:',selected)
        return 2
    from analyze_dlc import main as run_analysis
    out=ROOT/'Reports'
    # Never write reports into the selected save tree or original ZIP.
    if selected.is_dir():
        try:
            if out.resolve().is_relative_to(selected.resolve()):
                out=Path.home()/'Documents'/'MHP3rd_DLC_Reports'
        except OSError:pass
    out.mkdir(parents=True,exist_ok=True)
    import datetime
    ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    json_path=out/f'DLC_Analysis_{ts}.json'
    html_path=out/f'DLC_Analysis_{ts}_SHAREABLE.html'
    share_path=out/f'DLC_Analysis_{ts}_SHAREABLE.json'
    cmd=['--input',str(selected),'--json',str(json_path),'--html',str(html_path),'--shareable-json',str(share_path)]
    if args.no_quests:cmd.append('--no-quests')
    for p in args.palico:cmd.extend(['--palico',p])
    print('\nInspecting:',selected)
    try:run_analysis(cmd)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code,int) else 2
    print('\nPrivacy-safe HTML report saved:',html_path)
    print('Privacy-safe JSON report saved:',share_path)
    print('Technical JSON (contains local paths/hashes):',json_path)
    print('Save files were NOT modified.')
    try:
        answer=input('Open HTML report in your default browser? [Y/n]: ').strip().casefold()
    except EOFError:answer='n'
    if answer in ('','y','yes'):
        import webbrowser
        webbrowser.open(html_path.as_uri())
    return 0

if __name__=='__main__':raise SystemExit(main())
