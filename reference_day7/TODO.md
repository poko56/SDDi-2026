# D_tester — วันที่ 7

เปิดไฟล์ใน `reference/` (เป็นโค้ดฉบับเต็มที่เสร็จแล้ว) แล้วใส่**เฉพาะส่วนที่ตารางบอก**ลงใน repo `SDDi-2026` ทีละ commit
ไฟล์ใน `reference/` วางไว้ตำแหน่งเดียวกับที่ต้องสร้างใน repo

ก่อนเริ่ม:
```bash
git switch develop
git pull
git switch -c test/converter
```

ชื่อ branch `test/converter` บอกว่าวันนี้ทำเรื่องอะไร **อย่าเปลี่ยนชื่อ branch หลังจากเปิด PR แล้ว** เพราะ GitHub จะปิด PR นั้นทิ้ง

| | ไฟล์ | ใส่อะไร (ชื่อจากต้นแบบ) | ทดสอบงาน A วันที่ | ข้อความ commit |
|---|---|---|---|---|
| ☐ | `tests/test_converter.py` | `test_convert_png_with_alpha_to_jpg`, `test_convert_image_*` | 6 | `test: image conversion` |
| ☐ | `tests/test_converter.py` | `test_compress_*`, `test_docx_to_pdf_rejects_other_types`, `test_extract_audio_rejects_non_video` | 6 | `test: compress, docx and audio` |
| ☐ | `tests/test_converter.py` | `test_registry_*`, `test_convert_dispatches_*`, `test_convert_unknown_combination`, `test_convert_never_overwrites_*`, `test_convert_same_format_keeps_source` | 6 | `test: converter registry` |
| ☐ | `.github/workflows/build.yml` | job `build-windows` | – | `ci: build Windows exe` |

แต่ละ commit:
```bash
git add <ไฟล์ที่แก้>
git commit -m "<ข้อความ commit ในตาราง>"
```

ตอนเย็น:
```bash
git push -u origin test/converter
gh pr create --base develop --fill
```
