# ZipZap — เอกสารประกอบการนำเสนอโครงงาน

**วิชา:** SOFTWARE DESIGN AND DEVELOPMENT 2 (03376124 SDD 2-1/69 SEC-2)
**วันนำเสนอ:** วันพฤหัสบดีที่ 29 ตุลาคม 2569
**ทีม 4 คน:**
- POKOMAN (A — Backend / Lead) — 111 commits
- Sorawitsit19 (B — Frontend 1) — 34 commits
- JetSoGoof (C — Frontend 2) — 24 commits
- weerapat-s (D — Tester) — 46 commits
- รวม 215 commits บน `main` ปัจจุบัน release ล่าสุด **v1.2.2**

**ชื่อโครงงาน:** ZipZap — AI-Powered Smart File Manager
**เทคโนโลยี:** Python 3.11 + CustomTkinter + Gemini + Ollama + GitHub Actions + Caddy + systemd (VPS)
**repo:** <https://github.com/poko56/SDDi-2026>

---

# PART 1 — อ.ไพบูลย์ (Software Architecture & OOP)

## 1. บทนำและเป้าหมายของระบบ

### 1.1 ความสำคัญและความเป็นมาของปัญหา
- ไฟล์ในคอมพิวเตอร์ของผู้ใช้ทั่วไปกระจัดกระจาย ไม่เป็นระเบียบ (รูปปน PDF ปน Zip)
- ไฟล์ซ้ำ (duplicate) และไฟล์ขยะ (.tmp, .log, .DS_Store) กินพื้นที่โดยไม่รู้ตัว
- การจัดเรียงด้วยมือเสียเวลาและผิดพลาดง่าย (ลากผิดโฟลเดอร์ ลบของสำคัญ)
- ผู้ใช้ส่วนใหญ่ไม่กล้าใช้ AI เพราะกลัวว่าไฟล์จะถูกส่งขึ้น cloud

### 1.2 วัตถุประสงค์
1. จัดระเบียบไฟล์อัตโนมัติ (ตามประเภท / เดือน / AI รู้บริบท)
2. หาและลบไฟล์ซ้ำ + ไฟล์ขยะอย่างปลอดภัย (ย้ายไปถังขยะในเครื่อง ไม่ลบจริงทันที)
3. ตั้งชื่อไฟล์ใหม่ด้วย AI (Smart Rename) และแปลงไฟล์ (Word→PDF, PNG→PDF ฯลฯ)
4. ให้ผู้ใช้เลือกใช้ AI ได้ทั้ง **cloud (Gemini / ZipZap AI)** และ **local (Ollama)**
5. ปลอดภัย: API key ไม่ถูกฝังในโค้ด, Undo ได้ทุกการย้าย

### 1.3 ขอบเขตการทำงาน (Scope & Capabilities)
| หน้าฟีเจอร์ | ทำอะไรได้ |
|---|---|
| **Dashboard** | สแกนโฟลเดอร์, โชว์ donut chart, Quick Actions, Undo |
| **Smart Cleaner** | ไฟล์ซ้ำ (SHA-256), ไฟล์ขยะ (extension), ไฟล์ใหญ่ไม่ใช้งาน |
| **Converter** | Word/Markdown/Image/HTML → PDF; รวมหลายรูป |
| **AI Help Chat** | ถาม AI เกี่ยวกับไฟล์ในโฟลเดอร์ปัจจุบัน |
| **Auto Monitor** | ดักไฟล์ใหม่ที่ drop ลงโฟลเดอร์แล้วจัดอัตโนมัติ |
| **Settings** | สลับ provider AI, ใส่/ลบ key, จัดการ Ollama model, โฟลเดอร์ยกเว้น |

---

## 2. สถาปัตยกรรมและการออกแบบระบบ (Architecture & Class Design)

### 2.1 ภาพรวมสถาปัตยกรรม (Layered Architecture)

```
┌───────────────────────────────────────────────────────────┐
│                      Presentation (ui/)                   │
│  app.py                                                   │
│  pages/{dashboard,cleaner,converter,ai_chat,monitor,      │
│          settings}.py  + widgets.py + theme.py            │
└───────────────────────────────────────────────────────────┘
                              ▼  AppServices
┌───────────────────────────────────────────────────────────┐
│                   Core Services (core/)                   │
│  services.py (composition root → AppServices)             │
│  ├─ config.py    ├─ logger.py    ├─ exclusion.py          │
│  ├─ cleaner.py   ├─ organizer.py ├─ converter.py          │
│  ├─ stats.py     ├─ watcher.py   ├─ ai_assistant.py       │
│  ├─ llm.py (AIRouter + GeminiClient + ZipZapCloudClient)  │
│  ├─ ollama.py    ├─ google_login.py                       │
│  └─ paths.py / file_types.py / system_info.py             │
└───────────────────────────────────────────────────────────┘
                              ▼
┌───────────────────────────────────────────────────────────┐
│         Storage / External APIs                           │
│  Local FS · Gemini API · Ollama REST · ZipZap Proxy (VPS) │
│  Google OAuth 2.0 (loopback + PKCE)                       │
└───────────────────────────────────────────────────────────┘
                              ▲
┌───────────────────────────────────────────────────────────┐
│                     Infrastructure                        │
│  CI/CD: GitHub Actions (.github/workflows/build.yml)      │
│  Server: systemd zipzap-proxy.service + Caddy (TLS)       │
└───────────────────────────────────────────────────────────┘
```

**จุดสำคัญ:** UI ไม่รู้จัก Gemini SDK / Ollama REST เลย รู้จักแค่ `services.llm.generate(...)` ที่เป็น interface กลาง → ย้าย provider ได้โดยไม่แตะ UI

### 2.2 Class Diagram (เน้นความสัมพันธ์ระหว่างวัตถุหลัก)

```
          ┌─────────────────┐
          │   ZipZapApp     │(ui.app)
          │  - services     │
          │  - pages{...}   │
          └────────┬────────┘
                   │ 1 : 1
                   ▼
    ┌─────────────────────────────┐
    │        AppServices          │(core.services)
    │  config, logger, exclusion  │
    │  llm, cleaner, organizer    │
    │  converter, analyzer,       │
    │  watcher, assistant         │
    └───────┬─────────────────────┘
            │   has-a (composition)
   ┌────────┼─────────┬──────────┬──────────┬──────────┐
   ▼        ▼         ▼          ▼          ▼          ▼
 Config  Logger   Exclusion   AIRouter   Cleaner   Organizer
Manager                       │            │           │
                              │ delegates  │ uses      │ uses
                              ▼            ▼           ▼
                        {zipzap,     Logger +   Logger +
                         gemini,     Exclusion  AIRouter +
                         ollama}                Exclusion
                              │
                   ┌──────────┼──────────┐
                   ▼          ▼          ▼
            ZipZapCloud   Gemini     Ollama
              Client      Client     Client
                 │           ▲
                 └─ extends ─┘  (Liskov)
```

**Design Patterns ที่ใช้:**
- **Composition Root** (`build_services()` ใน `core/services.py`) — สร้างทุก service ครั้งเดียวและ wire dependencies
- **Strategy / Proxy** — `AIRouter` ห่อ 3 provider ด้วย interface เดียว (`generate`, `is_configured`, `label`)
- **Observer** — `on_folder_change`, `on_log` ใน `ZipZapApp` (หน้าใหม่ลงทะเบียน listener ได้ ไม่ต้องให้หน้าอื่นรู้จัก)
- **Template Method** — `BasePage.build()` / `on_show()`
- **Facade** — `AIAssistant` ซ่อน prompt engineering + file tree scanning ให้ UI เรียกแค่ `ask_ai(folder, query)`
- **Context Manager** — `logger.batch()` ติด batch id ให้ทุก move ใน run เดียวกัน (ใช้กับ Undo)

### 2.3 การประยุกต์ใช้ SOLID Principles (พร้อมตัวอย่างโค้ด)

**S — Single Responsibility**
- `ActionLogger` รับผิดชอบเฉพาะการบันทึก log (ข้อความ + ประวัติ move)
- `StorageCleaner` รู้แค่การหาและย้ายไฟล์ลง trash
- `WatcherManager` รู้แค่การดัก filesystem event

**O — Open/Closed** *(ตัวอย่างโค้ดจุดที่ 1)*
```python
# core/llm.py — เพิ่ม provider ใหม่ (ZipZapCloudClient) โดยไม่แก้ AIRouter
class AIRouter:
    def __init__(self, providers, active):
        self.providers = {p.name: p for p in providers}
        self.use(active)
    def __getattr__(self, attr):
        return getattr(self._active, attr)  # ส่งทุก call ไปที่ provider ปัจจุบัน

# core/services.py — ใส่ provider เพิ่มก็แค่เพิ่มในลิสต์
llm = AIRouter([zipzap, gemini, ollama], provider)
```
→ ตอน sprint 3 เราเพิ่ม `ZipZapCloudClient` (Gemini ผ่าน proxy) **โดยไม่ต้องแก้ `AIRouter`, UI, หรือ `AIAssistant`** เลย

**L — Liskov Substitution**
```python
# core/llm.py
class ZipZapCloudClient(GeminiClient):
    """ใช้แทน GeminiClient ได้ 100% (base_url ชี้ proxy, api_key เป็น session token)"""
    def _new_client(self):
        return genai.Client(api_key=self._api_key,
                            http_options=HttpOptions(base_url=self.base_url, api_version=API_VERSION))
```
UI ที่เรียก `llm.generate(...)` ไม่รู้ว่ากำลังคุยกับ Gemini ตรงๆ หรือผ่าน proxy

**I — Interface Segregation**
- แต่ละ provider เปิด method เล็กๆ เฉพาะที่จำเป็น (`generate`, `is_configured`, `label`, `not_configured_message`, `max_prompt_files`)
- `Ollama` ที่ไม่รองรับ `upload_file` ก็ raise `AIServiceError` ชัดเจน ไม่บังคับให้ implement ทุกอย่าง

**D — Dependency Inversion** *(ตัวอย่างโค้ดจุดที่ 2)*
```python
# core/organizer.py — รับ dependency ผ่าน constructor
class FileOrganizer:
    def __init__(self, logger, llm, exclusion):   # <-- abstractions
        self.logger = logger
        self.llm = llm
        self.exclusion = exclusion

# tests/conftest.py — test ใส่ FakeLLM แทน Gemini ได้ทันที
return FileOrganizer(logger, FakeLLM(configured=False), ExclusionPolicy())
```
→ **175 tests รันได้โดยไม่ต้องยิง Gemini จริง** เพราะทุก service รับ dependency เข้ามา ไม่ได้ `import` เอง

### High Cohesion & Low Coupling (สรุป)
- **Cohesion สูง:** ทุก module ใน `core/` ทำงานอย่างเดียว ชื่อไฟล์ = หน้าที่
- **Coupling ต่ำ:** UI ↔ Core คุยผ่าน `AppServices` อย่างเดียว; Core ↔ External คุยผ่าน abstract client; เพิ่ม/ถอด page หรือ provider ได้โดยไม่กระทบส่วนอื่น

---

## 3. การทำงานร่วมกันผ่าน Git (Team Collaboration Workflow)

### 3.1 Branching Strategy (Feature Branching + GitFlow light)
```
main ─── v1.0.0 ── v1.1.0 ── v1.2.0 ── v1.2.1 ── v1.2.2  (release tags)
  │         ▲         ▲         ▲         ▲         ▲
  └─ develop ─────────┴─────────┴─────────┴─────────┘
         ▲
         ├─ feature/google-login       (A)
         ├─ feature/account-menu       (A)
         ├─ feature/bug-roundup        (A)
         ├─ feature/pdf-export         (C)
         ├─ feature/converter-ui       (B)
         ├─ feature/watchdog-tests     (D)
         └─ feature/<name>-dayN        (friends' daily branches)
```
- ทุก feature ตัดจาก `develop` → PR กลับเข้า `develop`
- Release: PR `develop → main` + tag `vX.Y.Z` → GitHub Actions build ซิป Mac + Windows

### 3.2 Commit History, Pull Requests, Code Review
- ใช้ **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`
- ทุก PR ต้องผ่าน CI (lint + test + build 2 แพลตฟอร์ม) ก่อน merge
- Code review ใน PR: comment ที่บรรทัด, เสนอการแก้, ต้อง approve ก่อน merge
- รวม **51 PRs** merged, **215 commits** บน main
- ตัวอย่าง PR สำคัญ: #46 (Google login), #48 (account menu), #50 (bug roundup)

**การกระจายงาน (เห็นจาก `git log --format='%an' | uniq -c`):**
| สมาชิก | หน้าที่ | commits | สัดส่วน |
|---|---|---|---|
| POKOMAN (A) | Backend core, services, CI/CD, server, security | 111 | 51.6% |
| weerapat-s (D) | Tester, test suite, QA | 46 | 21.4% |
| Sorawitsit19 (B) | Frontend (Converter, Monitor pages) | 34 | 15.8% |
| JetSoGoof (C) | Frontend (Dashboard, Assets, Smart Rename UI) | 24 | 11.2% |

---

## 4. การสาธิตการทำงานของโปรแกรม (Live Demo Checklist)

### 4.1 Use Case หลักที่จะ demo
1. **เปิดแอป** → Dashboard โชว์ "ยังไม่ได้เลือกโฟลเดอร์"
2. **เลือกโฟลเดอร์** (แนะนำใช้ `~/ZipZap_Demo_v1` ที่สร้างจาก `scripts/make_demo_folder.py`)
   → เห็น "กำลังสแกน... N ไฟล์" แล้ว donut chart
3. **Smart Cleaner** → scan → เห็น duplicate / junk → เลือก → ย้ายลง `.zipzap_trash/`
4. **Undo (ปุ่มเดียวคืนทั้งหมด)** → Dashboard
5. **Organize by Category** → ไฟล์กระจายเข้าโฟลเดอร์ Documents/Images/Videos/…
6. **Undo** → ไฟล์กลับที่เดิม
7. **AI Chat** → ลอง login Google (รูปโปรไฟล์มุมล่างซ้าย) → ถาม "มี PDF กี่ไฟล์?" → AI ตอบพร้อมปุ่มเปิดไฟล์
8. **สลับ provider ในหน้า Chat** → เปลี่ยนเป็น Gemini key ของตัวเอง หรือ Local AI
9. **Converter** → ลาก Word drop → ได้ PDF
10. **Auto Monitor** → เริ่ม monitor → ลาก `emptyfile.mp4` (0 byte) ลงโฟลเดอร์ → ถูกจัดเข้า Videos อัตโนมัติ
11. **Settings** → เห็นการ์ดใหม่พร้อม icon badge + status pill, Google OAuth avatar, โควตาวันนี้

### 4.2 Error/Edge Cases ที่จะโชว์
- เลือกโฟลเดอร์ว่าง → donut เป็นสีเทาไม่ error
- AI chat ตอน offline / ยังไม่ได้ login → ขึ้นข้อความ "กรุณา login ด้วย Google…" (provider-aware)
- Smart Rename ไฟล์เสียหาย → AI ตอบ "ไฟล์เสียหาย อ่านไม่ได้" ไม่ crash
- Gemini key หมดโควตา → proxy ส่ง 429 → UI โชว์ข้อความไทย ไม่ใช่ stack trace
- Path traversal: ลองให้ AI ตอบด้วยไฟล์นอก target folder → `safe_join` return None, blocks open

---

## 5. สรุปผลและข้อเสนอแนะ

### 5.1 ปัญหาและอุปสรรคในการออกแบบเชิงวัตถุ
1. **UI Threading (CustomTkinter + tkinter mainloop)** — ทุก background task ต้อง marshal กลับ UI thread → แก้ด้วย `ZipZapApp.run_background(task, on_done, on_error)` + `call_in_ui()` queue
2. **Gemini SDK versioning** — SDK 3.0 default ยิง `/v1/...` แต่ `-latest` models ต้องใช้ `/v1beta/...` → บังคับผ่าน `HttpOptions(api_version="v1beta")`
3. **State across many pages** — ต้องให้ Dashboard เปลี่ยนโฟลเดอร์แล้วหน้าอื่นรู้ → ใช้ Observer pattern (`on_folder_change`)
4. **Secret management** — API key / session token ห้ามฝังในโค้ด → ใช้ env var + `~/.zipzap/config.json` (0600) + proxy เก็บ secret ฝั่ง server เท่านั้น

### 5.2 Refactoring Opportunities
- **Event bus** แทน list of listeners (ยืดหยุ่นกว่า ถ้าเพิ่ม 5-6 ชนิด event)
- **Plug-in system** สำหรับ file converter (ตอนนี้ hardcode แต่ละชนิด → อยากให้เพิ่ม format ใหม่โดยแค่ drop module)
- **Async I/O** สำหรับ scan folder ใหญ่ (ตอนนี้ใช้ thread ธรรมดา ถ้าเป็น `asyncio` จะ cancel ได้ง่าย)
- **ย้าย AI prompt เป็นไฟล์** (ตอนนี้อยู่ใน `ai_assistant.py` SYSTEM_PROMPT) → ง่ายต่อการปรับปรุงภาษาและ A/B test

---

# PART 2 — อ.สุระชัย (Security + CI/CD)

## 1. Threat Analysis (20%)

### 1.1 Threat Modeling ด้วย DFD

```
┌────────┐   files       ┌───────────┐  scan/organize  ┌────────────┐
│  User  │ ─────────────▶│ ZipZap    │ ───────────────▶│  Local FS  │
│        │◀────── UI ────│ Desktop   │◀────────────────│            │
└────────┘               │  (Py+CTk) │                 └────────────┘
     │                   └─────┬─────┘
     │ OAuth code              │ HTTPS
     ▼                         ▼
┌────────────────┐     ┌─────────────────┐    POST /v1/..:generateContent
│ Google OAuth   │◀────│ ZipZap Proxy    │ ──────▶ ┌────────────┐
│ (accounts.g.c) │     │ (Caddy→systemd  │          │ Gemini API │
└────────┬───────┘     │  :8787 on VPS)  │◀─────── └────────────┘
         │ id_token    └───┬─────────────┘
         │                 │
         │                 ▼
         │          ┌──────────────┐
         └─────────▶│ usage.db     │  (SQLite: sessions, usage)
                    │  sha256(sid) │
                    └──────────────┘

Trust boundary 1 (Desktop ↔ Internet)  │  Trust boundary 2 (Proxy ↔ Gemini)
```

### 1.2 STRIDE Threats + Mitigations
| STRIDE | Threat | Mitigation (มีในโค้ด) |
|---|---|---|
| **S**poofing | ปลอม session token สวมรอยคนอื่น | sha256 hash session → DB; session byte length 32 จาก `secrets.token_hex(32)` |
| | ปลอม Google ตัวเอง | proxy แลก code กับ Google ตรงผ่าน TLS + ตรวจ `aud`, `iss`, `exp`, `email_verified` ของ id_token |
| **T**ampering | ยัด path `../../etc/passwd` ให้ AI เปิด | `core/paths.safe_join()` ใช้ `realpath` + ตรวจว่าอยู่ใต้ root |
| | แก้ไฟล์ config ให้ชี้ proxy ปลอม | `DEFAULT_PROXY_URL` ใน code + ตรวจ `https://` |
| **R**epudiation | อ้างว่าไม่ได้ลบไฟล์ | `ActionLogger` เก็บ log txt + JSON ทุกการ move/rename พร้อม timestamp |
| **I**nfo disclosure | API key หลุด | เก็บ key ใน `~/.zipzap/config.json` chmod 0600, อ่านจาก env; ไม่ฝังใน code; proxy เก็บ `GEMINI_API_KEY` ใน `/etc/zipzap-proxy.env` 0600 (root) |
| | Error ตอบกลับโชว์ stack trace | ทุก exception ของ provider ถูก wrap เป็น `AIServiceError` ที่ message เป็นไทย |
| **D**oS | user ใช้ AI หนักจน key หมด | proxy limit: **50 req/user/day, 150/IP, 1000 total, 30 login/IP/day** (reset เที่ยงคืน Thai) |
| | upload ไฟล์ใหญ่ | Caddy `max_size 21MB` และ proxy `_read_body(limit)` |
| **E**oP (Elevation) | สวมรอย OAuth flow | PKCE (S256) + `state` + loopback `127.0.0.1` เท่านั้น (regex `^http://127\.0\.0\.1:\d{1,5}$`) |

### 1.3 Misuse Case Diagram (คำบรรยาย)
1. **ผู้ประสงค์ร้ายส่ง prompt injection ผ่านเนื้อหาไฟล์** → System prompt ของ `AIAssistant` ระบุชัดว่าให้ตอบจาก file list เท่านั้น + ตอบด้วย `[OPEN: path]` → UI ตรวจ `safe_join` ก่อนเปิด
2. **ผู้ใช้ลบ `~/.zipzap/config.json` เพื่อ reset โควตา** → ล้มเหลว เพราะ proxy นับที่ `sub` (Google account id) ไม่ใช่ที่ install token
3. **Attacker ขโมย laptop ใช้ session ของผู้ใช้** → session หมดอายุ 30 วัน + ผู้ใช้กด Logout ที่ไหนก็ได้ (`DELETE` จาก DB)
4. **Attacker ส่ง link `http://evil.com/?code=...` ให้ผู้ใช้** → proxy reject เพราะ `redirect_uri` ต้อง match `^http://127\.0\.0\.1:\d{1,5}$`

### 1.4 Asset List
| Asset | ที่เก็บ | ชั้นป้องกัน |
|---|---|---|
| Google OAuth Client Secret | `/etc/zipzap-proxy.env` (VPS, 0600 root) | ไม่อยู่ใน repo, ssh-only access |
| Gemini API Key | เหมือนกัน | เหมือนกัน |
| Session tokens | DB SQLite เก็บเป็น sha256 เท่านั้น | ถึงแม้ dump DB ก็ login ไม่ได้ |
| User API Key (เลือกใช้เอง) | `~/.zipzap/config.json` 0600 | ไม่ sync ไปไหน, ไม่ถูกส่งผ่าน proxy |
| User files | เครื่อง user เอง | ไม่มีการ upload นอกจากที่ user สั่ง AI ให้อ่าน |
| Activity log | `~/.zipzap/action_log.{txt,json}` | เขียนทับได้โดย user |

### 1.5 Security Requirements (SR)
- **SR-01:** ห้ามฝัง secret ลง source code หรือ binary release
- **SR-02:** API key / session token ที่เก็บในเครื่องต้องมี permission 0600
- **SR-03:** OAuth flow ต้องใช้ PKCE และ state
- **SR-04:** Session token ต้องเก็บเป็น hash บน server
- **SR-05:** ต้องมี per-user และ per-IP rate limit
- **SR-06:** ทุก path user supply ต้องผ่าน `safe_join()` ก่อนใช้งาน
- **SR-07:** Error ที่โชว์ให้ user ต้องไม่รั่ว stack trace หรือค่าภายใน
- **SR-08:** HTTPS บังคับใช้สำหรับการสื่อสารกับ ZipZap proxy (Caddy TLS auto)

---

## 2. Risk Register (10%)

| ID | Risk | Likeli hood | Impact | Mitigation | Status |
|---|---|---|---|---|---|
| R-01 | API key หลุดจาก config file | M | H | chmod 0600, ไม่ sync cloud, docs เตือน | ✅ |
| R-02 | Gemini quota หมดเพราะคนใช้หนัก | H | M | Proxy limit 50/user/day, 1000 total | ✅ |
| R-03 | Session token ถูกขโมยจาก DB | L | H | เก็บ sha256 เท่านั้น | ✅ |
| R-04 | Path traversal จาก AI output | M | H | `safe_join` ทุกจุดก่อนเปิดไฟล์ | ✅ |
| R-05 | Prompt injection ลบไฟล์ผ่าน AI | L | H | AI ไม่มีสิทธิ์ลบ; UI เป็นคนลบ | ✅ |
| R-06 | VPS โดนยึด → ขโมย Gemini key | L | H | ssh key-only, Caddy TLS, DynamicUser systemd | ⚠️ติด backup rotation |
| R-07 | Supply-chain จาก pip package | M | H | pin version, `pip install --require-hashes` planned | ⏳ |
| R-08 | Watchdog ไม่ cancel pending ตอน quit | L | L | `cancel_pending()` ใน `WatcherManager.stop_watching()` | ✅ |
| R-09 | Undo ผิดไฟล์เพราะแชร์ log กันหลาย session | L | M | `threading.Lock` รอบการเขียน JSON | ✅ |
| R-10 | DoS proxy ด้วย request จำนวนมาก | M | M | per-IP limit 150/day; Caddy rate-limit optional | ✅ |

---

## 3. Secure Coding & Refactor (20%)

### 3.1 จุดที่ทำ Secure Coding อ้างอิง OWASP + Python best practice
**A — Input Validation / Path Safety** (`core/paths.py`)
```python
def safe_join(root, *parts):
    """คืน None ถ้า path รวมแล้วหลุดออกจาก root (ป้องกัน path traversal)"""
    target = os.path.realpath(os.path.join(root, *parts))
    if not target.startswith(os.path.realpath(root) + os.sep):
        return None
    return target
```

**B — Secret Management** (`server/zipzap_proxy.py`)
```python
# อ่าน secret จาก env (systemd EnvironmentFile=/etc/zipzap-proxy.env 0600 root)
api_key           = env["GEMINI_API_KEY"]
google_client_id  = env["GOOGLE_CLIENT_ID"]
google_client_sec = env["GOOGLE_CLIENT_SECRET"]
# proxy ไม่เคย print / log secret
```

**C — Token Handling** (`server/zipzap_proxy.py`)
```python
def create_session(self, sub, email, name, days):
    token = "zs-" + secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()   # ← เก็บเฉพาะ hash
    self._db.execute("INSERT INTO sessions ...", (token_hash, sub, email, name, expires))
    return token      # ส่งคืน user ครั้งเดียว
```

**D — OAuth** (`core/google_login.py`)
```python
# PKCE S256 + state (เพิ่งแก้เมื่อ v1.2.0)
verifier, challenge = _pkce_pair()              # verifier → S256 → challenge
state = secrets.token_urlsafe(16)
# ตรวจ state หลัง callback
if result.get("state") != state:
    raise LoginError("state ไม่ตรงกัน")
# redirect_uri ต้องเป็น loopback เท่านั้น
LOOPBACK_REDIRECT_RE = re.compile(r"^http://127\.0\.0\.1:\d{1,5}$")
```

**E — Exception Hygiene** (`core/llm.py`)
```python
try:
    response = client.models.generate_content(...)
except Exception as e:
    raise AIServiceError(str(e)) from e     # user เห็นแค่ message ภาษาไทย
                                            # stack chain เก็บไว้ debug ภายใน
```

### 3.2 Refactor ที่ทำตามหลักการ Secure / Clean Code
| Refactor | หลักการที่อ้างอิง | Before → After |
|---|---|---|
| ย้ายการเก็บ `install_id` ออก, ใช้ Google `sub` แทน | OWASP A07 Auth | นับโควตาต่อบัญชีจริง ไม่ reset ได้ด้วยการลบไฟล์ |
| `AIRouter.__getattr__` → polymorphism | SOLID OCP | เดิม if-else ทุก provider ใน UI → หายทั้งหมด |
| แยก `ZipZapCloudClient` extends `GeminiClient` | Liskov | ลดโค้ดซ้ำ ~40 บรรทัด |
| `logger.batch()` context manager | Single Writer + Atomicity | Undo ทีละชุด แทนทีละไฟล์ |
| `services.sign_in_with_google()` เป็น method เดียว | Facade | UI เรียกบรรทัดเดียว, ไม่ต้องรู้ PKCE / loopback server |
| ลบ 0-byte skip ใน watcher | YAGNI / Correctness | จัดไฟล์ว่างได้ ไม่มี silent skip |

---

## 4. Traceability Matrix (10%)

| Requirement | Design Artifact | Implementation | Test | Status |
|---|---|---|---|---|
| REQ-01 สแกน & แสดงสถิติโฟลเดอร์ | `StorageAnalyzer` | `core/stats.py` | `test_foundations.py::test_storage_stats_*` | ✅ |
| REQ-02 ลบไฟล์ซ้ำ | `StorageCleaner._find_duplicates` | `core/cleaner.py` | `test_cleaner.py::test_duplicates_*` | ✅ |
| REQ-03 ย้ายไฟล์ไป trash (undo ได้) | `StorageCleaner.clean_files` + `ActionLogger` | `core/cleaner.py`, `core/logger.py` | `test_cleaner.py`, `test_logger.py::test_undo_*` | ✅ |
| REQ-04 จัดไฟล์ตามประเภท/เดือน | `FileOrganizer.organize_folder` | `core/organizer.py` | `test_organizer.py` | ✅ |
| REQ-05 Smart Rename ด้วย AI | `FileOrganizer.smart_rename` | `core/organizer.py` | `test_organizer.py::test_smart_rename_*` | ✅ |
| REQ-06 AI Chat ตอบเกี่ยวกับไฟล์ | `AIAssistant.ask_ai` | `core/ai_assistant.py` | `test_ai_assistant.py` | ✅ |
| REQ-07 Auto Monitor จัดไฟล์ใหม่ | `WatcherManager` + `SmartFileHandler` | `core/watcher.py` | `test_watcher.py` | ✅ |
| REQ-08 Converter หลายฟอร์แมต | `FileConverter` | `core/converter.py` | `test_converter.py` | ✅ |
| REQ-09 Login Google (ไม่ต้องกรอก API key) | `google_login.sign_in` + proxy | `core/google_login.py`, `server/zipzap_proxy.py` | `test_zipzap_proxy.py` | ✅ |
| REQ-10 Undo กดครั้งเดียวคืนทั้ง batch | `ActionLogger.batch()` | `core/logger.py` | `test_logger.py::test_undo_reverses_a_whole_batch_*` | ✅ |
| SR-01..08 (ดู 1.5) | ตาม design | หลายไฟล์ | รวม 180 tests | ✅ |

---

## 5. การติดตั้งแบบอัตโนมัติ (40%)

### 5.1 กระบวนการ CI (Continuous Integration)
**ไฟล์:** `.github/workflows/build.yml`
**Trigger:** push และ pull_request เข้า `develop` / `main` + `v*.*.*` tag

```
PR / push
   │
   ├─ lint    (flake8 --max-line-length=120)       ~10s
   ├─ test    (pytest 180 tests, ubuntu-latest)    ~55s
   ├─ build-mac     (pyinstaller → ZipZap.app)      ~1m15s
   └─ build-windows (pyinstaller → ZipZap.exe)      ~1m40s
          │
          └─ ✅ ทุก job เขียว → อนุญาต merge (branch protection)
```

**ผลลัพธ์ที่โชว์ในสไลด์:**
- Screenshot GitHub Actions ของ PR #46, #48, #50 (ทุกช่องเขียวหมด)
- ตัวอย่าง flake8 fail → fix → เขียว (PR #40 ตอนแรก fail เพราะ line too long 124)
- ตัวอย่าง pytest fail → fix → เขียว (PR #50 แก้ `test_watcher` ตามการ remove 0-byte skip)

### 5.2 กระบวนการ CD (Continuous Deployment)

**Release pipeline:**
```
git tag v1.2.2 && git push origin v1.2.2
           │
           ▼
  GitHub Actions: workflow "release"
  ├─ build Mac    → ditto --keepParent ZipZap.app  → ZipZap-Mac.zip  (66 MB)
  ├─ build Win    → Compress-Archive dist\\ZipZap\\* → ZipZap-Windows.zip (97 MB)
  └─ softprops/action-gh-release@v2
         │
         └─▶ GitHub Release v1.2.2 (public download)
```

**Server deployment (VPS):**
```bash
# ส่งไฟล์
scp server/zipzap_proxy.py xver@185.84.160.168:/tmp/
# ติดตั้งแบบ atomic
ssh xver@185.84.160.168 \
    'sudo install -m 644 /tmp/zipzap_proxy.py /opt/zipzap-proxy/zipzap_proxy.py \
     && sudo systemctl restart zipzap-proxy'
# ตรวจสุขภาพ
curl https://185-84-160-168.sslip.io/health   # → {"ok": true, "login": true}
```

**การตั้งค่า secret (ไม่อยู่ใน repo เลย):**
- `server/set_gemini_key.sh` — ssh เข้า VPS, อ่าน key แบบ hidden (`read -rsp`), เขียน `/etc/zipzap-proxy.env`, restart service
- `server/set_google_client.sh` — ลักษณะเดียวกันสำหรับ Google OAuth client

**Service config** (`server/zipzap-proxy.service`):
```ini
[Service]
DynamicUser=yes                    # ไม่ต้องสร้าง user เอง, ได้ UID ชั่วคราว
StateDirectory=zipzap-proxy        # SQLite อยู่ใน /var/lib/zipzap-proxy
EnvironmentFile=/etc/zipzap-proxy.env  # 0600 root:root
ProtectSystem=strict               # read-only ทั้ง /
ProtectHome=yes
PrivateTmp=yes
NoNewPrivileges=yes
```

**Caddy** (TLS อัตโนมัติ):
```caddy
185-84-160-168.sslip.io {
    request_body { max_size 21MB }
    reverse_proxy 127.0.0.1:8787
}
```

### 5.3 แสดงผลลัพธ์การติดตั้ง (ที่จะโชว์ในสไลด์)
- **Release page:** <https://github.com/poko56/SDDi-2026/releases> → 7 releases (v1.0.0 → v1.2.2) ทั้งหมดมีไฟล์ Mac + Windows
- **CI matrix:** screenshot Actions tab แสดง build ทั้ง 215 commits เป็นเขียวเกือบทั้งหมด
- **Server uptime:** `systemctl status zipzap-proxy` → active since <วัน deploy>
- **Live health check:** เปิด <https://185-84-160-168.sslip.io/health> → `{"ok": true, "login": true}`
- **Live Google login จาก app:** โควตาวันนี้ขึ้น ex. `3/50` หลังถาม AI 3 ครั้ง

---

# สรุปสุดท้าย (สำหรับสไลด์หน้าปิด)

- **Architecture:** Layered + Composition Root + 3 provider interchangeable (ZipZap AI / Gemini / Ollama)
- **SOLID:** ประยุกต์ครบทั้ง 5 ข้อ พร้อมตัวอย่างโค้ด 2 จุด
- **Teamwork:** 4 คน, 51 PRs, 215 commits, ทุกคน contribute ผ่าน Git
- **Security:** PKCE OAuth, session hashing, rate limit 3 ชั้น, chmod 0600, safe_join, STRIDE + Misuse case ครบ
- **CI/CD:** 4 CI jobs + auto-release บน tag + atomic VPS deploy
- **ผลลัพธ์:** v1.2.2 production-ready, ดาวน์โหลด Mac/Windows ได้ทันที, มี live backend บน VPS

---

## เช็กลิสต์ก่อนขึ้น present (29 ต.ค. 2569)
- [ ] ปริ้นเอกสารนี้สำหรับทุกคนในทีม
- [ ] เตรียม slide deck (Google Slides หรือ PowerPoint) — ใช้หัวข้อตามด้านบน
- [ ] เตรียม demo folder `~/ZipZap_Demo_v1` ไว้พร้อม (ไฟล์ซ้ำ, ไฟล์ขยะ, ไฟล์ 0 byte ชื่อ `emptyfile.mp4`)
- [ ] ทดสอบ Google login จากเครื่องที่จะใช้ present (อย่าลืม add email อาจารย์ใน Test users)
- [ ] เปิด GitHub, GitHub Actions, Release page ไว้พร้อม (tab คนละ tab)
- [ ] เปิด `/health` endpoint ไว้พิสูจน์ server live
- [ ] ซ้อมพูด 15 นาที (ใช้เกณฑ์ % เป็น guideline: Architecture 30% ของอ.ไพบูลย์ = ~4 นาที)
