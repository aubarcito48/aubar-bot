import sys

if '--legacy' in sys.argv:
    from .ui.app import main
else:
    from .ui.desktop.window import main

raise SystemExit(main())
