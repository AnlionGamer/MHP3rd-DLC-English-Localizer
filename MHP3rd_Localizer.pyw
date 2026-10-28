"""Double-clickable desktop app entrypoint, no console or BAT menu.

First-run dependency setup is optional, private to this program folder, and
never touches PPSSPP. Building a self-contained EXE removes this requirement.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent


def launch():
    if sys.version_info<(3,10):
        from tkinter import messagebox
        messagebox.showerror('Python version not supported','Python 3.10 or newer is required.')
        return
    if getattr(sys,'frozen',False):
        from desktop_app import main
        main()
        return
    # Always prefer the program's private environment if present. No system-wide
    # imports or packages are replaced or modified.
    venv=HERE/'.venv'/'Scripts'
    private=venv/'pythonw.exe'
    if sys.platform=='win32' and private.is_file() and Path(sys.executable).resolve()!=private.resolve():
        subprocess.Popen([str(private),str(HERE/'MHP3rd_Localizer.pyw')],cwd=str(HERE))
        return
    try:
        from cryptography.hazmat.primitives.ciphers import algorithms
        from cryptography.hazmat.primitives.cmac import CMAC
    except ImportError:
        import tkinter as tk
        from tkinter import messagebox,ttk
        root=tk.Tk();root.withdraw()
        answer=messagebox.askyesno('First-run component setup',
            'This program needs the cryptography library to read encrypted PPSSPP DLC.\n\n'
            'Install it into a private .venv beside the application?\n'
            'This requires an internet connection and does NOT change PPSSPP saves or system-wide Python packages.',parent=root)
        if not answer:root.destroy();return
        root.deiconify();root.title('MHP3rd DLC Localizer — first-run setup');root.geometry('560x125');root.resizable(False,False)
        ttk.Label(root,text='Installing private runtime components…',padding=(18,16)).pack(anchor='w')
        bar=ttk.Progressbar(root,mode='indeterminate',length=510);bar.pack(padx=18,fill='x');bar.start(12)
        import queue,threading
        q=queue.Queue()
        def work():
            try:
                subprocess.run([sys.executable,'-m','venv',str(HERE/'.venv')],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
                pip=(venv/'python.exe')
                done=subprocess.run([str(pip),'-m','pip','install','-r',str(HERE/'requirements.txt')],check=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
                check=subprocess.run([str(pip),'-c','import cryptography; from cryptography.hazmat.primitives.cmac import CMAC'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
                if check.returncode:raise RuntimeError('Installed cryptography could not be loaded')
                q.put(('ok',''))
            except Exception as exc:q.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()
        def poll():
            try:state,message=q.get_nowait()
            except queue.Empty:root.after(150,poll);return
            bar.stop()
            if state=='ok':
                try:subprocess.Popen([str(private),str(HERE/'MHP3rd_Localizer.pyw')],cwd=str(HERE))
                except OSError as exc:messagebox.showerror('Unable to start',str(exc),parent=root)
            else:messagebox.showerror('Private dependency install failed',message+'\n\nNo save files were changed.',parent=root)
            root.destroy()
        root.after(150,poll)
        root.mainloop()
        return
    from desktop_app import main
    main()


if __name__=='__main__':
    try:launch()
    except Exception as exc:
        import tkinter as tk
        from tkinter import messagebox
        r=tk.Tk();r.withdraw()
        messagebox.showerror('MHP3rd Localizer startup failed',f'{type(exc).__name__}: {exc}',parent=r)
        r.destroy()
