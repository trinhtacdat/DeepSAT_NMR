# DeepSAT Local

Run DeepSAT on Windows with the authors’ trained models and reference database. Peak lists, inference, candidate ranking, and structure drawings stay on this computer. Setup downloads the author assets once. The original code and examples are in `upstream/`, at DeepSAT commit `e50336bc1574a966c2c7831110cfc99b0e8401a3`.

## Install on Windows

1. On GitHub, select **Code → Download ZIP**, then extract the entire ZIP to a writable folder. A Git clone works too.
2. Double-click `Install_DeepSAT.bat` in the extracted folder. Keep the window open until it says **DeepSAT is ready**. The installer retrieves the upstream source if needed, creates a local Python environment, installs the dependencies, and downloads the two models and reference database (about 1.5 GB of model and reference data).
3. Double-click `Open_DeepSAT.bat`. Select **Normal HSQC** or **Edited HSQC**, click **Load example**, and then click **Run DeepSAT**. After setup, analyses can run offline.

The installer targets 64-bit Windows with internet access for setup. If it cannot find 64-bit Python 3.11, it tries to install it for the current user with WinGet. If WinGet is unavailable or fails, install [64-bit Python 3.11](https://www.python.org/downloads/windows/) with the Python launcher and Tcl/Tk enabled, then rerun the installer.

## Run an analysis

1. Double-click `Open_DeepSAT.bat`.
2. Select **Normal HSQC** or **Edited HSQC**. Click **Browse…** to choose a peak list or **Load example** to use the example for that mode.
3. Optionally enter a known molecular weight, then click **Run DeepSAT**.
4. Review the candidate table and use the buttons below it to open the plots or the saved result folder.

Start a new peak list with the [Normal HSQC CSV template](inputs/templates/normal_hsqc_template.csv) or the [Edited HSQC CSV template](inputs/templates/edited_hsqc_template.csv). Save a copy for each sample and enter numeric values below the header.

Supply a comma- or tab-separated peak list with `1H` and `13C` columns in ppm. Use one row per HSQC cross-peak. Edited HSQC also requires an `Intensity` column with positive CH/CH₃ and negative CH₂ peaks. The model uses the sign of edited intensities. The reader reports rows excluded because of zero edited intensity or shifts outside 0 ≤ ¹H < 12 ppm and 0 ≤ ¹³C < 240 ppm. Remove solvent, noise, and unrelated compound peaks during peak picking.

```csv
1H,13C,Intensity
4.89,102.17,8042
3.94,68.30,-6017
```

## Output and interpretation

Each run creates a new folder under `results/` with `candidates.csv`, `hsqc.png`, and `prediction.json`. It also saves `structures.png` when RDKit can draw candidate SMILES. The JSON records the model and database filenames, the predicted molecular weight, the weight used for search, the top three class scores, the glycoside score, and the predicted fingerprint bits.

The local tool uses the upstream 128 × 128 HSQC encoding and candidate search. The upstream web workflow uses the entered weight, if supplied, as the center of its existing mass filter. A reference entry passes when `abs(reference MW - search MW) / reference MW < 0.20`. The search returns distinct SMILES above a fingerprint cosine of 0.60, sorted by score. The candidate list supports dereplication and needs independent structural confirmation. The reference data linked by this repository contain 196,665 records.

## Command line

```powershell
.\Open_DeepSAT.bat --example --channel 1
.\Open_DeepSAT.bat --example --channel 2
.\Open_DeepSAT.bat "C:\Data\sample.tsv" --channel 2 --mw 355 --top 20
```

See [Troubleshooting](TROUBLESHOOTING.md) for example runs, setup checks, and details to save when a run fails.

## Install from PowerShell

```powershell
git clone --recurse-submodules https://github.com/trinhtacdat/DeepSAT_NMR.git
cd DeepSAT_NMR
.\Install_DeepSAT.bat
```

To use an existing Python environment with the packages in `requirements.txt` and Tkinter installed, supply its executable.

```powershell
.\Setup-DeepSAT.ps1 -Python "C:\Path\To\python.exe"
```

The author assets are the February 2021 model releases and the `DB_010621_SM3.json` reference database. [Upstream model download script](https://github.com/mwang87/DeepSAT/blob/e50336bc1574a966c2c7831110cfc99b0e8401a3/Classifier/models_folder/models/get_models.sh) · [Upstream database download script](https://github.com/mwang87/DeepSAT/blob/e50336bc1574a966c2c7831110cfc99b0e8401a3/Classifier/get_database.sh)

For peak preparation and the original workflow, see the [upstream usage guide](https://github.com/mwang87/DeepSAT/blob/e50336bc1574a966c2c7831110cfc99b0e8401a3/Documentation/docs/Usage.md).

## Reference

Kim, H. W., Zhang, C., Reher, R., et al. (2023). DeepSAT: Learning Molecular Structures from Nuclear Magnetic Resonance Data. *Journal of Cheminformatics*, 15, 71. [DOI: 10.1186/s13321-023-00738-4](https://doi.org/10.1186/s13321-023-00738-4) · [Open-access full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10406729/)
