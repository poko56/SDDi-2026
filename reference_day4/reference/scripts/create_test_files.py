import os
import random
import time


def create_large_test_folder():
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "TestFolder")
    # Create or clean
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    os.makedirs(os.path.join(test_dir, "Convert_to_PDF"), exist_ok=True)

    # File templates
    templates = [
        ("report_Q{}.docx", ["Q1", "Q2", "Q3", "Q4"]),
        ("budget_202{}.xlsx", ["3", "4", "5", "6"]),
        ("meeting_notes_{}.txt", ["jan", "feb", "mar", "apr", "may", "jun"]),
        ("vacation_{}_{}.jpg", ["japan", "korea", "thai", "usa"], ["2023", "2024", "2025"]),
        ("receipt_{}_{}.png", ["starbucks", "apple", "amazon", "shopee"], ["jan", "feb", "mar"]),
        ("project_proposal_{}.pdf", ["v1", "v2", "final", "draft"]),
        ("invoice_{}.pdf", [str(i) for i in range(1001, 1020)]),
        ("presentation_{}.pptx", ["marketing", "sales", "dev", "design"]),
        ("song_{}.mp3", ["rock", "pop", "jazz", "lofi"]),
        ("interview_{}.mp4", ["candidate1", "candidate2", "candidate3"]),
        ("backup_{}.zip", ["db", "files", "config"]),
        ("screenshot_{}.png", [str(i) for i in range(1, 10)]),
        ("IMG_{}.heic", [str(i) for i in range(9900, 9920)])
    ]

    # Generate 60 files
    files_created = 0
    now = time.time()

    for i in range(60):
        # Pick random template
        tmpl = random.choice(templates)
        name_template = tmpl[0]
        args = [random.choice(opts) for opts in tmpl[1:]]
        filename = name_template.format(*args)

        # Ensure unique name to some extent
        if i % 5 == 0:
            filename = f"duplicate_of_{filename}"

        file_path = os.path.join(test_dir, filename)

        # Write dummy content
        content_size = random.randint(100, 50000)  # Random size up to 50KB
        with open(file_path, "w") as f:
            f.write("A" * content_size)

        # Random date between now and 2 years ago
        days_ago = random.randint(0, 730)
        mtime = now - (days_ago * 24 * 60 * 60)
        os.utime(file_path, (mtime, mtime))
        files_created += 1

    # Also add a huge dummy image (just a 6MB dummy text file named .jpg)
    huge_path = os.path.join(test_dir, "raw_camera_photo.jpg")
    with open(huge_path, "wb") as f:
        f.seek((6 * 1024 * 1024) - 1)
        f.write(b"\0")

    print(f"Created {files_created + 1} files in {test_dir}")


if __name__ == "__main__":
    create_large_test_folder()
