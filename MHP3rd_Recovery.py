"""Standalone offline console recovery executable; does not need translation catalog."""
from recovery import main
if __name__=='__main__':
    try:main()
    except Exception as exc:
        import sys
        print('RECOVERY REFUSED:',str(exc),file=sys.stderr)
        print('No unverified restore was attempted. Preserve all backups and pending files.',file=sys.stderr)
        sys.exit(2)
