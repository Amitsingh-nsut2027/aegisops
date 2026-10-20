"""Start the local API, refresh the private viewer session, then serve the workbench."""
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
try:
    subprocess.run([sys.executable, str(root / 'scripts' / 'init_local_env.py')], cwd=root, check=True)
    subprocess.run(['docker', 'compose', '--profile', 'api', 'up', '-d', '--build', '--wait', 'api'], cwd=root, check=True)
    subprocess.run([sys.executable, str(root / 'scripts' / 'create_viewer_token.py')], cwd=root, check=True)
    subprocess.run([sys.executable, str(root / 'scripts' / 'serve_frontend.py')], cwd=root, check=True)
except KeyboardInterrupt:
    print('\nWorkbench stopped. Existing API/database containers remain running.')
except subprocess.CalledProcessError:
    raise SystemExit('Workbench startup failed. Review the preceding local service output.') from None
