# VisuLogic Demo Dataset

This folder holds small, local-only diagrams used for demo rehearsal and regression checks.

Generate the sample PNGs with:

```powershell
cd data
..\backend\.venv\Scripts\python.exe .\generate_demo_diagrams.py
```

The generator is deterministic and overwrites only the known demo files listed in
`demo_manifest.json`.
