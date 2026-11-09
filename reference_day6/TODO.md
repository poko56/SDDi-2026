# D_tester — วันที่ 6

เปิดไฟล์ใน `reference/` (เป็นโค้ดฉบับเต็มที่เสร็จแล้ว) แล้วใส่**เฉพาะส่วนที่ตารางบอก**ลงใน repo `SDDi-2026` ทีละ commit
ไฟล์ใน `reference/` วางไว้ตำแหน่งเดียวกับที่ต้องสร้างใน repo

ก่อนเริ่ม:
```bash
git switch develop
git pull
git switch -c test/cleaner-organizer
```

ชื่อ branch `test/cleaner-organizer` บอกว่าวันนี้ทำเรื่องอะไร **อย่าเปลี่ยนชื่อ branch หลังจากเปิด PR แล้ว** เพราะ GitHub จะปิด PR นั้นทิ้ง

| | ไฟล์ | ใส่อะไร (ชื่อจากต้นแบบ) | ทดสอบงาน A วันที่ | ข้อความ commit |
|---|---|---|---|---|
| ☐ | `tests/test_cleaner.py` | `test_large_files_differing_after_quick_hash_are_not_duplicates`, `test_clean_files_*` | 5 | `test: quick hash and clean_files` |
| ☐ | `tests/test_organizer.py` | `test_organize_*` ทั้งหมด (8 ตัว) | 5 | `test: organize by type and month` |
| ☐ | `docs/manual_test.md` (ไฟล์ใหม่) | checklist ทดสอบมือสำหรับ Dashboard + Cleaner | – | `docs: manual test checklist` |

แต่ละ commit:
```bash
git add <ไฟล์ที่แก้>
git commit -m "<ข้อความ commit ในตาราง>"
```

ตอนเย็น:
```bash
git push -u origin test/cleaner-organizer
gh pr create --base develop --fill
```

ไฟล์ที่ต้นแบบไม่มี ต้องสร้างเอง: `docs/manual_test.md`
