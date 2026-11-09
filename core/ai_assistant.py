import datetime
import os

from core.file_types import format_size
from core.llm import AINotConfiguredError, AIServiceError
from core.paths import TRASH_DIR_NAME

MAX_FILES_IN_PROMPT = 500

SYSTEM_PROMPT = (
    "You are a helpful File Manager AI Assistant. "
    "The user will ask you questions about their files. "
    "Here is the list of files in their current folder:\n\n"
    "{file_tree}\n\n"
    "Please answer the user's question clearly and concisely in Thai language. "
    "Only rely on the file list provided above. "
    "IMPORTANT: Whenever you mention a specific file in your response, you MUST append its exact relative path "
    "using this format: [OPEN: relative/path/to/file.ext]. "
    "For example: '1. budget.xlsx [OPEN: budget.xlsx]'"
)
NOT_CONFIGURED_MESSAGE = "กรุณาตั้งค่า AI ในหน้า Settings ก่อนใช้งาน (ใส่ Gemini API Key หรือเลือกโมเดล Local AI)"


class AIAssistant:
    """Answers questions about the files in a folder using an injected LLM client."""

    def __init__(self, llm):
        self.llm = llm

    def scan_directory(self, folder_path, limit=MAX_FILES_IN_PROMPT):
        """Describe up to `limit` files as text lines; stops walking as soon as the limit is hit."""
        if not os.path.isdir(folder_path):
            return "ไม่พบโฟลเดอร์"
        lines = []
        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if d != TRASH_DIR_NAME]
            for name in files:
                if len(lines) >= limit:
                    lines.append(f"... (มีไฟล์มากเกินไป แสดงผลแค่ {limit} รายการแรก)")
                    return "\n".join(lines)
                path = os.path.join(root, name)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                mtime = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d")
                rel_path = os.path.relpath(path, folder_path)
                lines.append(f"- {rel_path} (Size: {format_size(st.st_size)}, Date: {mtime})")
        return "\n".join(lines)

    def ask_ai(self, folder_path, user_query):
        if not self.llm.is_configured:
            return NOT_CONFIGURED_MESSAGE
        if not folder_path or not os.path.isdir(folder_path):
            return "กรุณาเลือกโฟลเดอร์เป้าหมายในหน้า Dashboard ก่อนครับ"

        limit = min(MAX_FILES_IN_PROMPT, self.llm.max_prompt_files)
        prompt = SYSTEM_PROMPT.format(file_tree=self.scan_directory(folder_path, limit))
        try:
            return self.llm.generate(f"{prompt}\n\nUser Query: {user_query}")
        except AINotConfiguredError:
            return NOT_CONFIGURED_MESSAGE
        except AIServiceError as e:
            return f"เกิดข้อผิดพลาดในการเชื่อมต่อกับ AI: {e}"
