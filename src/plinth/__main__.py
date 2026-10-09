"""``python -m plinth``. The console script entry point is ``plinth.cli:main``;
both run the same preflight, which lives inside ``main`` so neither path skips it.
"""

from .cli import main

raise SystemExit(main())
