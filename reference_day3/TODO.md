# D_tester — วันที่ 3

เปิดไฟล์ใน `reference/` (เป็นโค้ดฉบับเต็มที่เสร็จแล้ว) แล้วใส่**เฉพาะส่วนที่ตารางบอก**ลงใน repo `SDDi-2026` ทีละ commit
ไฟล์ใน `reference/` วางไว้ตำแหน่งเดียวกับที่ต้องสร้างใน repo

ก่อนเริ่ม:
```bash
git switch develop
git pull
git switch -c test/logger-config
```

ชื่อ branch `test/logger-config` บอกว่าวันนี้ทำเรื่องอะไร **อย่าเปลี่ยนชื่อ branch หลังจากเปิด PR แล้ว** เพราะ GitHub จะปิด PR นั้นทิ้ง

| | ไฟล์ | ใส่อะไร (ชื่อจากต้นแบบ) | ทดสอบงาน A วันที่ | ข้อความ commit |
|---|---|---|---|---|
| ☐ | `tests/conftest.py` | import `ActionLogger` + fixture `logger` | 2 | `test: add logger fixture` |
| ☐ | `tests/test_logger.py` | `test_log_action_appends_line`, `test_log_move_records_json_entry` | 2 | `test: action and move logging` |
| ☐ | `tests/test_logger.py` | `test_undo_*` ทั้งหมด (4 ตัว) | 2 | `test: undo last move` |
| ☐ | `tests/test_foundations.py` | `test_config_*`, `test_api_key_*` | 2 | `test: ConfigManager` |
| ☐ | `.github/workflows/build.yml` | job `test` | – | `ci: run pytest` |

แต่ละ commit:
```bash
git add <ไฟล์ที่แก้>
git commit -m "<ข้อความ commit ในตาราง>"
```

ตอนเย็น:
```bash
git push -u origin test/logger-config
gh pr create --base develop --fill
```
