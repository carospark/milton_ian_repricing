"""Separate compact status-sheet edition; never writes the original summary."""
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def build():
    original=(ROOT/'docs/Hurricane_Repricing_Summary.html').read_text()
    runtime=re.search(r'<script>(.*?)</script>',original,re.S)[1]
    runtime=runtime.replace("'#aa6730'","'var(--s2)'")
    return (ROOT/'scripts/templates/research_status.html').read_text().replace('@@RUNTIME@@',runtime)


def run():
    path=ROOT/'docs/Hurricane_Repricing_Status.html'
    path.write_text(build(),encoding='utf-8');print(path)


if __name__=='__main__':run()
