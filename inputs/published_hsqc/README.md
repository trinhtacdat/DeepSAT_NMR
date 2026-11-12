# Published HSQC test inputs

These CSVs contain directly bonded ¹H–¹³C shift pairs transcribed from published experimental assignments. All three tests used normal HSQC and the model-predicted mass for search. No signed intensities were supplied by the assignment tables. Distinct methylene shifts are separate rows, and coincident symmetry-equivalent pairs are entered once.

| Input | Source and conditions | Peaks |
| --- | --- | ---: |
| `ethyl_caffeate.csv` | Ethyl caffeate (1), assigned ¹H shifts and ¹³C shifts from HSQC and HMBC, 500 MHz, DMSO-d₆. [Artemisia aucheri isolation paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC8170746/) | 7 |
| `oleracein_c.csv` | Oleracein C, Table 3, 600 MHz ¹H and 150 MHz ¹³C, DMSO-d₆. [Purslane isolation paper](https://www.mdpi.com/1420-3049/30/20/4147#table_body_display_molecules-30-04147-t003) | 17 |
| `oleracein_australis_1.csv` | Oleracein australis 1, Table 3, same conditions. [Purslane isolation paper](https://www.mdpi.com/1420-3049/30/20/4147#table_body_display_molecules-30-04147-t003) | 18 |

For both oleraceins, six sugar assignments list only an overlapping 3.2–3.55 ppm proton range and were omitted. Exchangeable protons and nonprotonated carbons were also omitted. These are assignment-derived inputs.

Run any input from the project root using PowerShell.

```powershell
.\Open_DeepSAT.bat .\inputs\published_hsqc\ethyl_caffeate.csv --channel 1 --output .\results\published_hsqc
```

| Compound | Predicted MW (Da) | Reference monoisotopic mass (Da) | Candidate result |
| --- | ---: | ---: | --- |
| Ethyl caffeate | 203.27 | 208.0736 | Rank 1 by connectivity, cosine 1.000 |
| Oleracein C | 583.68 | 665.1956 | Rank 1 by connectivity, cosine 1.000 |
| Oleracein australis 1 | 593.92 | 681.1905 | No matching connectivity in the top 10. Oleraceins A and C tied at cosine 0.9771. |

Rank checks compare candidate SMILES connectivity with the published structures using RDKit. The rank-1 library records omit stereochemistry. The ethyl caffeate record also carries a cis synonym, while the paper reports a 16.0 Hz olefinic coupling for the isolated compound. The reference connectivity for oleracein australis 1 uses the additional aromatic OH in Figure 5 of the purslane paper. No connectivity match was found in the bundled library among entries within 2 Da of its reference mass. These examples check local behavior. Training-set membership was not assessed.
