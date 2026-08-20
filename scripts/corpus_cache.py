#!/usr/bin/env python3
"""qcm_corpus_cache.py — QCM MCP Corpus SQLite Cache

启动时间优化：
  - 首次构建 cache：~1s
  - 增量更新：~50ms
  - 文件未变化：~5ms

Schema:
  corpus_files (name TEXT PRIMARY KEY, mtime INTEGER, content TEXT, size INTEGER)
  tools (num TEXT PRIMARY KEY, name TEXT, face TEXT, dims TEXT)
  masters (name TEXT PRIMARY KEY, info TEXT)

用法：
  from corpus_cache import CorpusCache
  cache = CorpusCache("/path/to/references")
  cache.build() # 首次构建
  files = cache.get_all_files() # {name: content}
  cache.incremental_update() # 增量更新（基于 mtime）
"""
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional


class CorpusCache:
    """SQLite-backed corpus cache"""

    def __init__(self, references_dir: str, db_path: Optional[str] = None):
        self.references_dir = references_dir
        self.db_path = db_path or os.path.join(
            os.environ.get("QCM_CACHE_DIR", "/tmp/qcm-cache"),
            "corpus.db"
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库 schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS corpus_files (
                    name TEXT PRIMARY KEY,
                    mtime REAL NOT NULL,
                    content TEXT NOT NULL,
                    size INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_corpus_mtime ON corpus_files(mtime);
            """)

    def build(self) -> float:
        """首次构建 cache（读取所有文件并入库）"""
        start = time.time()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM corpus_files")

            # V8.4 修复：os.listdir 顶层 → rglob 递归（V8.3.1 重组后知识库在 12 子目录）
            for fpath in sorted(Path(self.references_dir).rglob("*.md")):
                if ".deprecated" in fpath.name:
                    continue
                fname = fpath.relative_to(self.references_dir).as_posix()
                try:
                    mtime = os.path.getmtime(fpath)
                    size = os.path.getsize(fpath)
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()
                    cursor.execute(
                        "INSERT OR REPLACE INTO corpus_files (name, mtime, content, size) VALUES (?, ?, ?, ?)",
                        (fname, mtime, content, size)
                    )
                except Exception:
                    pass
            conn.commit()
        return time.time() - start

    def incremental_update(self) -> Dict[str, int]:
        """增量更新（基于 mtime）"""
        stats = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            current_files = {}

            for fpath in sorted(Path(self.references_dir).rglob("*.md")):
                if ".deprecated" in fpath.name:
                    continue
                fname = fpath.relative_to(self.references_dir).as_posix()
                try:
                    mtime = os.path.getmtime(fpath)
                    current_files[fname] = mtime

                    # 检查 cache 中是否存在
                    row = cursor.execute(
                        "SELECT mtime FROM corpus_files WHERE name = ?", (fname,)
                    ).fetchone()

                    if row is None:
                        # 新增
                        size = os.path.getsize(fpath)
                        with open(fpath, encoding="utf-8") as f:
                            content = f.read()
                        cursor.execute(
                            "INSERT INTO corpus_files (name, mtime, content, size) VALUES (?, ?, ?, ?)",
                            (fname, mtime, content, size)
                        )
                        stats["added"] += 1
                    elif row[0] < mtime:
                        # 更新
                        size = os.path.getsize(fpath)
                        with open(fpath, encoding="utf-8") as f:
                            content = f.read()
                        cursor.execute(
                            "UPDATE corpus_files SET mtime=?, content=?, size=? WHERE name=?",
                            (mtime, content, size, fname)
                        )
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1
                except Exception:
                    pass

            # 检测删除
            cached_names = {r[0] for r in cursor.execute("SELECT name FROM corpus_files").fetchall()}
            for cached_name in cached_names:
                if cached_name not in current_files:
                    cursor.execute("DELETE FROM corpus_files WHERE name = ?", (cached_name,))
                    stats["removed"] += 1

            conn.commit()
        return stats

    def get_all_files(self) -> Dict[str, str]:
        """获取所有文件 {name: content}"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            return {r[0]: r[1] for r in cursor.execute("SELECT name, content FROM corpus_files").fetchall()}

    def get_stats(self) -> dict:
        """获取 cache 统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            total = cursor.execute("SELECT COUNT(*), SUM(size) FROM corpus_files").fetchone()
            return {
                "files": total[0] or 0,
                "total_size_bytes": total[1] or 0,
                "db_path": self.db_path,
            }

    def is_built(self) -> bool:
        """cache 是否已构建"""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute("SELECT COUNT(*) FROM corpus_files").fetchone()[0]
            return count > 0

    def clear(self):
        """清空 cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM corpus_files")
            conn.commit()


class CorpusWatcher:
    """Corpus 文件监控（mtime 检测 + 自动增量更新）"""

    def __init__(self, cache: CorpusCache, references_dir: str, interval_s: float = 5.0):
        self.cache = cache
        self.references_dir = references_dir
        self.interval_s = interval_s
        self._last_mtimes: Dict[str, float] = {}
        self._running = False

    def start(self):
        """启动后台监控线程"""
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        """监控循环"""
        while self._running:
            try:
                stats = self.cache.incremental_update()
                if stats["added"] or stats["updated"] or stats["removed"]:
                    print(f"[CorpusWatcher] Reloaded: {stats}", flush=True)
            except Exception as e:
                print(f"[CorpusWatcher] Error: {e}", flush=True)
            time.sleep(self.interval_s)

    def check_once(self) -> Dict[str, int]:
        """单次检查（用于测试）"""
        return self.cache.incremental_update()


if __name__ == "__main__":
    # Demo
    from paths import REFERENCES
    REF_DIR = str(REFERENCES)
    cache = CorpusCache(REF_DIR)

    print("=== 首次构建 cache ===")
    elapsed = cache.build()
    print(f"  耗时：{elapsed:.3f}s")
    stats = cache.get_stats()
    print(f"  文件：{stats['files']}")
    print(f"  大小：{stats['total_size_bytes']/1024:.1f}KB")

    print()
    print("=== 增量更新（无变化）===")
    stats = cache.incremental_update()
    print(f"  {stats}")

    print()
    print("=== 模拟修改文件 ===")
    import tempfile
    test_file = os.path.join(REF_DIR, "test_cache.md")
    with open(test_file, "w") as f:
        f.write("# Test cache file")
    stats = cache.incremental_update()
    print(f"  {stats}")
    os.unlink(test_file)
    stats = cache.incremental_update()
    print(f"  删除后：{stats}")