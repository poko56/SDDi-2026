# D_tester — วันที่ 8

เปิดไฟล์ใน `reference/` (เป็นโค้ดฉบับเต็มที่เสร็จแล้ว) แล้วใส่**เฉพาะส่วนที่ตารางบอก**ลงใน repo `SDDi-2026` ทีละ commit
ไฟล์ใน `reference/` วางไว้ตำแหน่งเดียวกับที่ต้องสร้างใน repo

ก่อนเริ่ม:
```bash
git switch develop
git pull
git switch -c test/watcher-ai
```

ชื่อ branch `test/watcher-ai` บอกว่าวันนี้ทำเรื่องอะไร **อย่าเปลี่ยนชื่อ branch หลังจากเปิด PR แล้ว** เพราะ GitHub จะปิด PR นั้นทิ้ง

| | ไฟล์ | ใส่อะไร (ชื่อจากต้นแบบ) | ทดสอบงาน A วันที่ | ข้อความ commit |
|---|---|---|---|---|
| ☐ | `tests/test_watcher.py` | `Event`, `make_handler`, test ของ handler (6 ตัวแรก) | 7 | `test: watcher handler` |
| ☐ | `tests/test_watcher.py` | `test_start_watching_missing_folder`, `test_start_and_stop_watching` | 7 | `test: WatcherManager` |
| ☐ | `tests/test_services.py` | `FakeGenaiClient`, `fake_genai`, `test_client_*`, `test_changing_key_*`, `test_sdk_errors_are_wrapped` | 7 | `test: GeminiClient` |
| ☐ | `tests/conftest.py`, `tests/test_ai_assistant.py` | import `AIServiceError`, `FakeLLM`, fixture `fake_llm` + ทั้งไฟล์ test_ai_assistant | 7 | `test: AIAssistant with fake LLM` |
| ☐ | `.github/workflows/build.yml` | job `build-mac` | – | `ci: build Mac app` |

แต่ละ commit:
```bash
git add <ไฟล์ที่แก้>
git commit -m "<ข้อความ commit ในตาราง>"
```

ตอนเย็น:
```bash
git push -u origin test/watcher-ai
gh pr create --base develop --fill
```
