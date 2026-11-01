"""Report actual local capabilities without installing or changing configuration."""
import importlib.util,json,platform,shutil
from pathlib import Path
if __name__=='__main__':
    modules={m:bool(importlib.util.find_spec(m)) for m in ['pptx','PIL','openpyxl']}
    windows_chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    print(json.dumps({'python':platform.python_version(),'system':platform.system(),'modules':modules,
                      'commands':{c:shutil.which(c) for c in ['python','python3','powershell','soffice','node']},
                      'known_windows_chrome':str(windows_chrome) if windows_chrome.exists() else None,
                      'note':'PATH checks alone do not establish whether an application is installed. Probe Windows application/COM or Linux command paths when needed; WorkBuddy image generation and import remain separate checks.'},ensure_ascii=False,indent=2))
