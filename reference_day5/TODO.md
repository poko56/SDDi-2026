# D_tester — วันที่ 5

เปิดไฟล์ใน `reference/` (เป็นโค้ดฉบับเต็มที่เสร็จแล้ว) แล้วใส่**เฉพาะส่วนที่ตารางบอก**ลงใน repo `SDDi-2026` ทีละ commit
ไฟล์ใน `reference/` วางไว้ตำแหน่งเดียวกับที่ต้องสร้างใน repo

ก่อนเริ่ม:
```bash
git switch develop
git pull
git switch -c test/cleaner-scan
```

ชื่อ branch `test/cleaner-scan` บอกว่าวันนี้ทำเรื่องอะไร **อย่าเปลี่ยนชื่อ branch หลังจากเปิด PR แล้ว** เพราะ GitHub จะปิด PR นั้นทิ้ง

| | ไฟล์ | ใส่อะไร (ชื่อจากต้นแบบ) | ทดสอบงาน A วันที่ | ข้อความ commit |
|---|---|---|---|---|
| ☐ | `tests/test_cleaner.py` | `names` + `test_duplicates_*`, `test_same_size_different_content_is_not_duplicate`, `test_empty_files_are_not_duplicates` | 4 | `test: duplicate finder` |
| ☐ | `tests/test_cleaner.py` | `test_junk_*`, `test_large_files_require_size_and_age`, `test_one_walk_reports_every_enabled_check` | 4 | `test: junk and large files` |
| ☐ | `tests/test_cleaner.py` | `test_scan_skips_*`, `test_scan_missing_folder_returns_empty` | 4 | `test: scan skips trash and excluded` |

แต่ละ commit:
```bash
git add <ไฟล์ที่แก้>
git commit -m "<ข้อความ commit ในตาราง>"
```

ตอนเย็น:
```bash
git push -u origin test/cleaner-scan
gh pr create --base develop --fill
```
