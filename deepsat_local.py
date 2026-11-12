"""Run the upstream DeepSAT models and candidate search on local HSQC files."""

import argparse
import csv
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4


ROOT = Path(__file__).resolve().parent
CLASSIFIER = ROOT / "upstream" / "Classifier"
ASSETS = ROOT / "assets"
DATABASE = ASSETS / "DB_010621_SM3.json"
MODELS = {
    channel: ASSETS / "models" / f"(020321)SMART3_v3_{channel}ch_multitask_final.hdf5"
    for channel in (1, 2)
}
EXAMPLES = {
    1: ROOT / "upstream" / "test" / "swinolide.csv",
    2: CLASSIFIER / "input" / "Calcd_42086.csv",
}


def read_peaks(path, channel):
    columns = ["1H", "13C"]
    if channel == 2:
        columns.append("Intensity")

    peaks = []
    excluded = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        header = next((line for line in source if line.strip()), "")
        delimiter = "\t" if "\t" in header else ","
        reader = csv.reader(source, delimiter=delimiter, strict=True)
        headers = [cell.strip() for cell in next(csv.reader([header], delimiter=delimiter), [])]
        if any(headers.count(column) != 1 for column in columns):
            raise ValueError(f"Expected a CSV or TSV with one column each for {', '.join(columns)}.")
        positions = [headers.index(column) for column in columns]

        for row in reader:
            if not any(cell.strip() for cell in row):
                continue
            try:
                values = [float(row[position]) for position in positions]
            except (IndexError, ValueError) as error:
                raise ValueError(f"Peak row {reader.line_num} after the header needs numeric values for {', '.join(columns)}.") from error
            if not all(map(math.isfinite, values)):
                raise ValueError(f"Peak row {reader.line_num} after the header contains a non-finite number.")
            proton, carbon = values[:2]
            if 0 <= proton < 12 and 0 <= carbon < 240 and (channel == 1 or values[2] != 0):
                peaks.append(values)
            else:
                excluded += 1

    if not peaks:
        raise ValueError("No usable peaks in the model's 1H [0, 12) and 13C [0, 240) ppm ranges. Edited HSQC also requires nonzero signed intensities.")
    return columns, peaks, excluded


def run_search(input_path, channel, molecular_weight, top, output_root):
    columns, peaks, excluded = read_peaks(input_path, channel)
    model_path = MODELS[channel]
    for asset in (model_path, DATABASE):
        if not asset.is_file():
            raise FileNotFoundError(f"Missing {asset.name}. Run Setup-DeepSAT.ps1 to download the author files.")

    print(f"Read {len(peaks)} usable peaks ({excluded} excluded). Loading the {channel}-channel model…", flush=True)
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "4")
    os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
    os.environ["MPLBACKEND"] = "Agg"

    import numpy as np
    import pandas as pd
    from rdkit import Chem
    from rdkit.Chem import Draw
    from tensorflow import keras

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(CLASSIFIER))
    import SMART_3

    model = keras.models.load_model(model_path, compile=False)
    expected_input = (None, 128, 128, channel)
    if model.input_shape != expected_input:
        raise ValueError(f"Expected model input {expected_input}, found {model.input_shape}.")

    print("Predicting fingerprint, molecular weight, and classes…", flush=True)
    matrix = SMART_3._convert_data(pd.DataFrame(peaks, columns=columns), channel)
    batch = {"input_1": matrix[None].astype(np.float32)}
    outputs = [np.asarray(output) for output in model(batch, training=False)]
    expected_outputs = [(1, 6144), (1, 1), (1, 77), (1, 2)]
    if [output.shape for output in outputs] != expected_outputs or not all(np.isfinite(output).all() for output in outputs):
        raise ValueError("The model returned unexpected or non-finite fingerprint, mass, class, or glycoside outputs.")
    bits, predicted_mw, class_indices, class_scores, glycoside = SMART_3.refine_predict_nmr(*outputs)
    search_mw = float(predicted_mw) if molecular_weight is None else molecular_weight

    print("Searching the author reference database…", flush=True)
    # The upstream loader takes the class mapping from its own directory. The
    # standalone assets directory holds only the externally downloaded files.
    with (CLASSIFIER / "superclass.json").open(encoding="utf-8") as source:
        classes = json.load(source)
    database = pd.read_json(DATABASE)[["Name", "FP", "SMILES", "MW"]].to_numpy()
    if len(bits):
        hits = SMART_3.search_database(bits, search_mw, database, top_candidates=top)
    else:
        hits = pd.DataFrame(columns=["Name", "SMILES", "Cosine score", "MW"])

    class_by_index = {index: name for name, index in classes.items()}
    report = {
        "input_file": str(input_path),
        "channel": channel,
        "model_file": model_path.name,
        "reference_database": DATABASE.name,
        "database_entries": len(database),
        "usable_peaks": len(peaks),
        "excluded_peaks": excluded,
        "predicted_mw": float(predicted_mw),
        "search_mw": search_mw,
        "provided_mw": molecular_weight,
        "predicted_classes": [
            {"name": class_by_index[index], "score": float(score)}
            for index, score in zip(class_indices, class_scores)
        ],
        "glycoside_score": float(glycoside),
        "fingerprint_on_bits": bits.tolist(),
        "candidate_count": len(hits),
    }

    print("Saving candidate table, HSQC plot, and prediction details…", flush=True)
    output_root.mkdir(parents=True, exist_ok=True)
    run_dir = output_root / f"{input_path.stem[:60]}_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:8]}"
    with TemporaryDirectory(dir=output_root) as staging:
        stage = Path(staging)
        result = stage / "result"
        result.mkdir()
        hits["Name"] = hits["Name"].map(lambda names: " | ".join(names) if isinstance(names, list) else names)
        hits.to_csv(result / "candidates.csv", index=False, encoding="utf-8-sig")
        SMART_3._draw_search_image(result / "hsqc.png", matrix, class_indices, class_scores, glycoside, index_super=classes)
        molecules = []
        legends = []
        for rank, row in enumerate(hits.head(10).to_dict(orient="records"), 1):
            molecule = Chem.MolFromSmiles(row["SMILES"])
            if molecule is not None:
                molecules.append(molecule)
                legends.append(f"#{rank}   Cosine {row['Cosine score']:.3f}   MW {row['MW']}")
        if molecules:
            Draw.MolsToGridImage(molecules, molsPerRow=2, subImgSize=(360, 270), legends=legends).save(result / "structures.png")
        (result / "prediction.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        result.rename(run_dir)
    return run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("input", type=Path, nargs="?", help="CSV or TSV peak list")
    source.add_argument("--example", action="store_true", help="run the bundled example for the selected channel")
    parser.add_argument("--channel", type=int, choices=(1, 2), default=1, help="1 for normal HSQC or 2 for edited HSQC")
    parser.add_argument("--mw", type=float, help="optional molecular weight used as the center of the upstream mass filter")
    parser.add_argument("--top", type=int, default=10, help="maximum number of candidates (default 10)")
    parser.add_argument("--output", type=Path, default=ROOT / "results", help="parent folder for the new result folder")
    args = parser.parse_args()

    if args.mw is not None and (not math.isfinite(args.mw) or args.mw <= 0):
        parser.error("--mw must be a positive finite number")
    if args.top < 1:
        parser.error("--top must be at least 1")
    input_path = EXAMPLES[args.channel] if args.example else args.input.resolve()

    # Keep progress and the result path readable in Windows GUI subprocess pipes.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        output = run_search(input_path, args.channel, args.mw, args.top, args.output.resolve())
    except (ValueError, OSError, ImportError, csv.Error) as error:
        print(f"DeepSAT: {error}", file=sys.stderr)
        return 1
    print(f"Result folder: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
