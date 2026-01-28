"""数据管理模块 - 统一管理对话数据和持久化（SQLite3）"""

import json
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class SentenceRecord:
    """单条句子记录"""
    id: str              # UUID
    timestamp: float     # Unix timestamp
    original: str        # 原文
    translation: str     # 翻译
    is_completed: bool   # 是否完成
    session_id: str      # 会话 ID


class DataManager:
    """数据管理器 - 统一管理所有对话数据（SQLite3 持久化）

    职责:
    1. 维护全局句子列表（内存缓存）
    2. 提供线程安全的读写接口
    3. 自动持久化到 SQLite 数据库
    4. 管理会话
    """

    def __init__(self, storage_path: str = "~/.mac-transcriber"):
        self.storage_path = os.path.expanduser(storage_path)
        os.makedirs(self.storage_path, exist_ok=True)

        self.db_path = os.path.join(self.storage_path, "conversations.db")
        self._lock = threading.Lock()
        self._sentences: list[SentenceRecord] = []
        self._current_session_id = self._generate_session_id()

        # 初始化数据库
        self._init_database()

        # 加载当前会话数据
        self._load_current_session()

    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 创建句子表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentences (
                id TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                original TEXT NOT NULL,
                translation TEXT DEFAULT '',
                is_completed INTEGER DEFAULT 0,
                session_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建会话表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time REAL NOT NULL,
                end_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id
            ON sentences(session_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON sentences(timestamp)
        """)

        conn.commit()
        conn.close()

    def _load_current_session(self):
        """加载当前会话数据到内存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 查找最近的会话
        cursor.execute("""
            SELECT session_id FROM sessions
            ORDER BY start_time DESC
            LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            self._current_session_id = result[0]
            # 加载该会话的所有句子
            cursor.execute("""
                SELECT id, timestamp, original, translation, is_completed, session_id
                FROM sentences
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (self._current_session_id,))

            rows = cursor.fetchall()
            self._sentences = [
                SentenceRecord(
                    id=row[0],
                    timestamp=row[1],
                    original=row[2],
                    translation=row[3],
                    is_completed=bool(row[4]),
                    session_id=row[5]
                )
                for row in rows
            ]
        else:
            # 创建新会话
            self._create_session()

        conn.close()

    def _create_session(self):
        """创建新会话"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sessions (session_id, start_time)
            VALUES (?, ?)
        """, (self._current_session_id, time.time()))

        conn.commit()
        conn.close()

    def add_sentence(self, original: str, translation: str = "",
                     is_completed: bool = False) -> SentenceRecord:
        """添加新句子

        Args:
            original: 原文
            translation: 翻译（可选）
            is_completed: 是否完成

        Returns:
            SentenceRecord: 新创建的句子记录
        """
        with self._lock:
            record = SentenceRecord(
                id=str(uuid.uuid4()),
                timestamp=time.time(),
                original=original,
                translation=translation,
                is_completed=is_completed,
                session_id=self._current_session_id,
            )
            self._sentences.append(record)

            # 立即写入数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sentences (id, timestamp, original, translation, is_completed, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (record.id, record.timestamp, record.original, record.translation,
                  int(record.is_completed), record.session_id))
            conn.commit()
            conn.close()

            return record

    def update_sentence(self, sentence_id: str,
                       original: str | None = None,
                       translation: str | None = None,
                       is_completed: bool | None = None):
        """更新句子

        Args:
            sentence_id: 句子 ID
            original: 新的原文（可选）
            translation: 新的翻译（可选）
            is_completed: 新的完成状态（可选）
        """
        with self._lock:
            # 更新内存中的数据
            for sentence in self._sentences:
                if sentence.id == sentence_id:
                    if original is not None:
                        sentence.original = original
                    if translation is not None:
                        sentence.translation = translation
                    if is_completed is not None:
                        sentence.is_completed = is_completed

                    # 更新数据库
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()

                    update_fields = []
                    update_values = []

                    if original is not None:
                        update_fields.append("original = ?")
                        update_values.append(original)
                    if translation is not None:
                        update_fields.append("translation = ?")
                        update_values.append(translation)
                    if is_completed is not None:
                        update_fields.append("is_completed = ?")
                        update_values.append(int(is_completed))

                    if update_fields:
                        update_values.append(sentence_id)
                        cursor.execute(f"""
                            UPDATE sentences
                            SET {', '.join(update_fields)}
                            WHERE id = ?
                        """, update_values)
                        conn.commit()

                    conn.close()
                    break

    def get_recent_sentences(self, count: int = 4) -> list[SentenceRecord]:
        """获取最近 N 句（用于 Overlay 显示）

        Args:
            count: 句子数量

        Returns:
            list[SentenceRecord]: 最近的句子列表
        """
        with self._lock:
            return self._sentences[-count:] if len(self._sentences) > count else self._sentences.copy()

    def get_recent_sentences_after(self, after_timestamp: float, count: int = 4) -> list[SentenceRecord]:
        """获取指定时间戳之后的最近 N 句（用于 Overlay 当前会话显示）

        Args:
            after_timestamp: 时间戳阈值，只返回此时间之后的句子
            count: 句子数量

        Returns:
            list[SentenceRecord]: 最近的句子列表
        """
        with self._lock:
            # 过滤出指定时间之后的句子
            filtered = [s for s in self._sentences if s.timestamp > after_timestamp]
            # 返回最近 N 句
            return filtered[-count:] if len(filtered) > count else filtered.copy()

    def get_all_sentences(self) -> list[SentenceRecord]:
        """获取所有句子（用于主窗口显示）

        Returns:
            list[SentenceRecord]: 所有句子的副本
        """
        with self._lock:
            return self._sentences.copy()

    def get_current_session_sentences(self) -> list[SentenceRecord]:
        """获取当前会话的句子

        Returns:
            list[SentenceRecord]: 当前会话的句子列表
        """
        with self._lock:
            return [s for s in self._sentences if s.session_id == self._current_session_id]

    def new_session(self):
        """开始新会话"""
        with self._lock:
            # 结束当前会话
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET end_time = ?
                WHERE session_id = ?
            """, (time.time(), self._current_session_id))
            conn.commit()
            conn.close()

            # 创建新会话
            self._current_session_id = self._generate_session_id()
            self._sentences = []
            self._create_session()

    def clear_current_session(self):
        """清空当前会话"""
        with self._lock:
            # 从数据库删除
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sentences
                WHERE session_id = ?
            """, (self._current_session_id,))
            conn.commit()
            conn.close()

            # 从内存清除
            self._sentences = []

    def get_current_session_id(self) -> str:
        """获取当前会话 ID

        Returns:
            str: 当前会话 ID
        """
        return self._current_session_id

    def _generate_session_id(self) -> str:
        """生成会话 ID

        Returns:
            str: 格式为 YYYYMMDD_HHMMSS 的会话 ID
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def stop(self):
        """停止数据管理器（结束当前会话）"""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sessions
                SET end_time = ?
                WHERE session_id = ? AND end_time IS NULL
            """, (time.time(), self._current_session_id))
            conn.commit()
            conn.close()

    def export_to_json(self, filepath: str):
        """导出为 JSON

        Args:
            filepath: 导出文件路径
        """
        with self._lock:
            data = {
                "export_time": datetime.now().isoformat(),
                "total_sentences": len(self._sentences),
                "sentences": [asdict(s) for s in self._sentences]
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def export_to_txt(self, filepath: str):
        """导出为纯文本

        Args:
            filepath: 导出文件路径
        """
        with self._lock:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总句数: {len(self._sentences)}\n")
                f.write("=" * 80 + "\n\n")

                for sentence in self._sentences:
                    time_str = datetime.fromtimestamp(sentence.timestamp).strftime("%H:%M:%S")
                    f.write(f"[{time_str}]\n")
                    f.write(f"原文: {sentence.original}\n")
                    f.write(f"翻译: {sentence.translation}\n")
                    f.write("-" * 80 + "\n\n")

    def get_all_sessions(self) -> list[tuple[str, float, float | None]]:
        """获取所有会话列表

        Returns:
            list: [(session_id, start_time, end_time), ...]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, start_time, end_time
            FROM sessions
            ORDER BY start_time DESC
        """)
        sessions = cursor.fetchall()
        conn.close()
        return sessions

    def load_session(self, session_id: str):
        """加载指定会话

        Args:
            session_id: 会话 ID
        """
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, timestamp, original, translation, is_completed, session_id
                FROM sentences
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))

            rows = cursor.fetchall()
            self._sentences = [
                SentenceRecord(
                    id=row[0],
                    timestamp=row[1],
                    original=row[2],
                    translation=row[3],
                    is_completed=bool(row[4]),
                    session_id=row[5]
                )
                for row in rows
            ]
            self._current_session_id = session_id

            conn.close()
