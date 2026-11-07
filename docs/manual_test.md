# Manual test checklist: Dashboard and Cleaner

Prepare test data first:

```bash
python scripts/create_test_files.py
```

This creates `TestFolder/` with 60 dummy files plus a 6 MB `raw_camera_photo.jpg`.

## Dashboard

| | Step | Expected |
|---|---|---|
| ☐ | Open the app, go to Dashboard | "Storage Overview" and "Target Folder" cards show; folder reads "No folder selected" |
| ☐ | Click **Select Folder**, pick `TestFolder` | Folder path appears under "Target Folder" |
| ☐ | Wait for the stats to load | Donut shows "Loading..." then a chart; no "Error" |
| ☐ | Read the legend | Documents, multimedia, other and free disk space each show a size (e.g. `2.0 KB`) |
| ☐ | Compare with the folder in File Explorer | Total size roughly matches; `.docx/.xlsx/.pdf/.txt` count as documents, `.jpg/.png/.mp3/.mp4` as multimedia |
| ☐ | Pick a folder that is empty | Stats show 0 B, no crash |
| ☐ | Add a folder to Settings exclusions, return to Dashboard | The app still works and the excluded folder is not offered for cleaning |

## Cleaner

| | Step | Expected |
|---|---|---|
| ☐ | Scan `TestFolder` with duplicates on | Files named `duplicate_of_*` are not mistaken for originals; the shallowest copy is kept, others listed |
| ☐ | Create two files with identical content, scan | One is listed as duplicate, the other kept |
| ☐ | Create two same-size files with different content | Neither is listed as duplicate |
| ☐ | Create two empty files | Neither is listed as duplicate |
| ☐ | Add `x.tmp` and `y.LOG`, scan with junk on | Both listed as junk (case-insensitive) |
| ☐ | Scan with large files on (min 5 MB, 30 days) | `raw_camera_photo.jpg` listed only if it is older than 30 days |
| ☐ | Scan with a missing or deleted folder | Empty result, no crash |
| ☐ | Put a file in an excluded folder, scan | The file is not listed |
| ☐ | Select results and clean | Files move to the trash folder inside the target, keeping their relative path |
| ☐ | Clean a file whose name already exists in the trash | Old file kept, new one saved as `name_1.ext` |
| ☐ | Scan again after cleaning | Trash folder contents are not reported |
| ☐ | Undo the last action | Cleaned files return to their original location |

## Result

- Tester:
- Date:
- Build / branch:
- Failures found:
