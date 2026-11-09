# D_tester — วันที่ 9

เปิดไฟล์ใน `reference/` (เป็นโค้ดฉบับเต็มที่เสร็จแล้ว) แล้วใส่**เฉพาะส่วนที่ตารางบอก**ลงใน repo `SDDi-2026` ทีละ commit
ไฟล์ใน `reference/` วางไว้ตำแหน่งเดียวกับที่ต้องสร้างใน repo

ก่อนเริ่ม:
```bash
git switch develop
git pull
git switch -c test/rename-ollama
```

ชื่อ branch `test/rename-ollama` บอกว่าวันนี้ทำเรื่องอะไร **อย่าเปลี่ยนชื่อ branch หลังจากเปิด PR แล้ว** เพราะ GitHub จะปิด PR นั้นทิ้ง

| | ไฟล์ | ใส่อะไร (ชื่อจากต้นแบบ) | ทดสอบงาน A วันที่ | ข้อความ commit |
|---|---|---|---|---|
| ☐ | `tests/test_organizer.py` | `test_sanitize_filename`, `test_smart_rename_*` (ยกเว้น `…gregorian_year_hint`) | 8 | `test: Smart Rename` |
| ☐ | `tests/test_ollama.py` | `FakeOllama`, fixture `server`, `test_status_*` … `test_pull_error_is_raised` | 8 | `test: OllamaClient with fake server` |
| ☐ | `tests/test_ollama.py` | `test_validate_url_*`, `test_keeps_data_local_*`, `test_recommend_model`, `test_router_*`, `test_services_switch_*` | 8 | `test: provider switching` |
| ☐ | `tests/test_services.py` | fixture `services`, `test_services_share_*` | 8 | `test: services wiring` |
| ☐ | `scripts/make_demo_folder.py` | ทั้งไฟล์ | – | `feat(scripts): build demo folder` |

แต่ละ commit:
```bash
git add <ไฟล์ที่แก้>
git commit -m "<ข้อความ commit ในตาราง>"
```

ตอนเย็น:
```bash
git push -u origin test/rename-ollama
gh pr create --base develop --fill
```
