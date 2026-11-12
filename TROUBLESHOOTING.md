# Troubleshooting DeepSAT Local

## Reproduce with a bundled example

Open PowerShell in the project folder. Run both examples to check the launcher, the upstream code, the two models, and the reference database.

```powershell
git rev-parse --short HEAD
git submodule status
.\Open_DeepSAT.bat --example --channel 1
.\Open_DeepSAT.bat --example --channel 2
```

Successful runs print `Result folder:` and write `candidates.csv`, `hsqc.png`, and `prediction.json`. A run writes `structures.png` when RDKit can draw candidate structures. The 2026-11-12 baseline at commit `89275e3` processed 45 Normal HSQC peaks and 16 Edited HSQC peaks, with zero exclusions and 10 candidates for each. Both runs searched 196,665 reference entries.

## Find the failing step

| Symptom | Check |
| --- | --- |
| The launcher says setup is required or the GUI closes immediately | Check that the Python executable in `.python-path` still exists. Run `Setup-DeepSAT.ps1` again if the environment moved. Try the command-line example to see the error in PowerShell. |
| `No module named 'SMART_3'` or a bundled example is missing | Run `git submodule update --init` from the project folder. The pinned upstream revision is `e50336bc1574a966c2c7831110cfc99b0e8401a3`. |
| A model or database is missing, or setup reports a download error | Check `Get-Command curl.exe` and rerun setup. Setup verifies the size and SHA-256 of each asset and reuses verified files. Record the asset name and the first `Asset setup failed` message if the error repeats. |
| TensorFlow, Keras, or another package fails to import or load | Check the interpreter and installed packages using the commands below. Compare the installed versions with `requirements.txt`. |
| A bundled example works but a sample fails peak validation | Compare the sample header with the template for the selected mode. Use numeric `1H` and `13C` shifts in ppm. Edited HSQC also requires signed `Intensity` values. Check the run log for the reported row or excluded peak count. |
| The run completes with an empty candidate table | In `prediction.json`, check `candidate_count`, `usable_peaks`, `excluded_peaks`, `predicted_mw`, and `search_mw`. Check whether an entered mass changed the search and review the mass and cosine filters in the [README](README.md#output-and-interpretation). |

To check the interpreter and core imports after setup, run the following from the project folder.

```powershell
$deepSatPython = (Get-Content -LiteralPath .python-path -Raw).Trim()
Test-Path -LiteralPath $deepSatPython
& $deepSatPython --version
& $deepSatPython -m pip check
& $deepSatPython -c 'import tensorflow, keras, numpy, pandas, matplotlib, rdkit, tkinter; print("Imports OK")'
```

For a later diagnosis, keep the Git revision, submodule revision, Python version, selected HSQC mode, and the first error with the preceding progress line. If a run completes, keep the relevant values from `prediction.json` and note whether the bundled example behaves the same way. The JSON also stores the full input path. Remove local paths and unpublished peak data before sharing diagnostic excerpts outside the project.
