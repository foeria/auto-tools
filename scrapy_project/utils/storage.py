"""
数据存储模块
使用 SQLite 实现轻量级存储（替代 MongoDB）
"""
import sqlite3
import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 数据库文件路径
DB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DB_DIR, 'data', 'storage.db')


class SQLiteStorage:
    """SQLite 存储 - 轻量级替代方案"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_db_exists()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def _ensure_db_exists(self):
        """确保数据库和表存在"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = self._get_connection()
        try:
            # 任务表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'pending',
                    result TEXT,
                    error TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 模板表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    url_pattern TEXT,
                    actions TEXT NOT NULL,
                    extractors TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 工作流表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    nodes TEXT NOT NULL,
                    edges TEXT,
                    actions TEXT,
                    url_pattern TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            # 爬取数据表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS crawled_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    url TEXT,
                    data TEXT NOT NULL,
                    created_at TEXT,
                    FOREIGN KEY (task_id) REFERENCES tasks(id)
                )
            ''')

            conn.commit()
            logger.info(f"Database initialized: {self.db_path}")
        finally:
            conn.close()

    def save_task(self, task: Dict[str, Any]) -> str:
        """保存任务"""
        conn = self._get_connection()
        try:
            task['updated_at'] = datetime.now().isoformat()
            conn.execute('''
                INSERT OR REPLACE INTO tasks
                (id, url, actions, priority, status, result, error, metadata, created_at, started_at, completed_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task['id'],
                task['url'],
                json.dumps(task.get('actions', [])),
                task.get('priority', 1),
                task.get('status', 'pending'),
                json.dumps(task.get('result')) if task.get('result') else None,
                task.get('error'),
                json.dumps(task.get('metadata', {})),
                task.get('created_at') or datetime.now().isoformat(),
                task.get('started_at'),
                task.get('completed_at'),
                task['updated_at']
            ))
            conn.commit()
            return task['id']
        finally:
            conn.close()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务"""
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def update_task_status(self, task_id: str, status: str, result: Dict[str, Any] = None):
        """更新任务状态"""
        conn = self._get_connection()
        try:
            update_data = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            if result:
                update_data['result'] = json.dumps(result)
            if status == 'completed':
                update_data['completed_at'] = datetime.now().isoformat()

            set_clause = ', '.join([f'{k} = ?' for k in update_data.keys()])
            values = list(update_data.values()) + [task_id]

            conn.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
            conn.commit()
        finally:
            conn.close()

    def list_tasks(self, status: str = None, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        """列出任务"""
        conn = self._get_connection()
        try:
            query = 'SELECT * FROM tasks'
            params = []
            if status:
                query += ' WHERE status = ?'
                params.append(status)
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, skip])

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        conn = self._get_connection()
        try:
            # 先删除关联数据
            conn.execute('DELETE FROM crawled_data WHERE task_id = ?', (task_id,))
            result = conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    def save_crawled_data(self, data: Dict[str, Any]) -> str:
        """保存爬取的数据"""
        conn = self._get_connection()
        try:
            data['created_at'] = datetime.now().isoformat()
            cursor = conn.execute('''
                INSERT INTO crawled_data (task_id, url, data, created_at)
                VALUES (?, ?, ?, ?)
            ''', (
                data.get('task_id'),
                data.get('url'),
                json.dumps(data.get('data', {})),
                data['created_at']
            ))
            conn.commit()
            return str(cursor.lastrowid)
        finally:
            conn.close()

    def get_crawled_data(self, task_id: str) -> List[Dict[str, Any]]:
        """获取爬取的数据"""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                'SELECT * FROM crawled_data WHERE task_id = ? ORDER BY created_at DESC',
                (task_id,)
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def save_template(self, template: Dict[str, Any]) -> str:
        """保存模板"""
        conn = self._get_connection()
        try:
            template['updated_at'] = datetime.now().isoformat()
            conn.execute('''
                INSERT OR REPLACE INTO templates
                (id, name, description, url_pattern, actions, extractors, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template['id'],
                template['name'],
                template.get('description', ''),
                template.get('url_pattern', ''),
                json.dumps(template.get('actions', [])),
                json.dumps(template.get('extractors', [])),
                template.get('created_at') or datetime.now().isoformat(),
                template['updated_at']
            ))
            conn.commit()
            return template['id']
        finally:
            conn.close()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板"""
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT * FROM templates WHERE id = ?', (template_id,)).fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有模板"""
        conn = self._get_connection()
        try:
            rows = conn.execute('SELECT * FROM templates ORDER BY created_at DESC').fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        conn = self._get_connection()
        try:
            result = conn.execute('DELETE FROM templates WHERE id = ?', (template_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    # ============ 工作流相关方法 ============

    def save_workflow(self, workflow: Dict[str, Any]) -> str:
        """保存工作流"""
        conn = self._get_connection()
        try:
            workflow['updated_at'] = datetime.now().isoformat()
            conn.execute('''
                INSERT OR REPLACE INTO workflows
                (id, name, description, nodes, edges, actions, url_pattern, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                workflow['id'],
                workflow['name'],
                workflow.get('description', ''),
                json.dumps(workflow.get('nodes', [])),
                json.dumps(workflow.get('edges', [])),
                json.dumps(workflow.get('actions', [])),
                workflow.get('url_pattern', ''),
                workflow.get('created_at') or datetime.now().isoformat(),
                workflow['updated_at']
            ))
            conn.commit()
            return workflow['id']
        finally:
            conn.close()

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流"""
        conn = self._get_connection()
        try:
            row = conn.execute('SELECT * FROM workflows WHERE id = ?', (workflow_id,)).fetchone()
            if row:
                result = dict(row)
                # 解析JSON字段
                for field in ['nodes', 'edges', 'actions']:
                    if result.get(field) and isinstance(result[field], str):
                        try:
                            result[field] = json.loads(result[field])
                        except json.JSONDecodeError:
                            result[field] = []
                return result
            return None
        finally:
            conn.close()

    def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        conn = self._get_connection()
        try:
            rows = conn.execute('SELECT * FROM workflows ORDER BY updated_at DESC').fetchall()
            result = []
            for row in rows:
                result.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'] or '',
                    'url_pattern': row['url_pattern'] or '',
                    'created_at': row['created_at'] or '',
                    'updated_at': row['updated_at'] or ''
                })
            return result
        finally:
            conn.close()

    def delete_workflow(self, workflow_id: str) -> bool:
        """删除工作流"""
        conn = self._get_connection()
        try:
            result = conn.execute('DELETE FROM workflows WHERE id = ?', (workflow_id,))
            conn.commit()
            return result.rowcount > 0
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self._get_connection()
        try:
            total_tasks = conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
            completed_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'").fetchone()[0]
            failed_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'failed'").fetchone()[0]
            running_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'").fetchone()[0]
            total_data = conn.execute('SELECT COUNT(*) FROM crawled_data').fetchone()[0]

            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'running_tasks': running_tasks,
                'total_data_records': total_data
            }
        finally:
            conn.close()

    def list_task_history(
        self,
        start_date: str = None,
        end_date: str = None,
        status: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取任务历史记录（按时间范围筛选）"""
        conn = self._get_connection()
        try:
            query = 'SELECT * FROM tasks WHERE 1=1'
            params = []

            if start_date:
                query += ' AND created_at >= ?'
                params.append(start_date)
            if end_date:
                query += ' AND created_at <= ?'
                params.append(end_date)
            if status:
                query += ' AND status = ?'
                params.append(status)

            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_task_duration(self, task_id: str) -> Optional[float]:
        """获取任务执行时长（秒）"""
        conn = self._get_connection()
        try:
            row = conn.execute(
                'SELECT started_at, completed_at FROM tasks WHERE id = ?',
                (task_id,)
            ).fetchone()
            if row and row['started_at'] and row['completed_at']:
                start = datetime.fromisoformat(row['started_at'])
                end = datetime.fromisoformat(row['completed_at'])
                return (end - start).total_seconds()
            return None
        finally:
            conn.close()

    def get_recent_tasks(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的任务列表"""
        return self.list_tasks(limit=count, skip=0)


class InMemoryQueue:
    """内存任务队列 - 轻量级替代 Redis"""

    def __init__(self):
        self._queue: Dict[int, List[str]] = {0: [], 1: [], 2: [], 3: []}  # 按优先级分组
        self._task_status: Dict[str, str] = {}
        self._running_tasks: set = set()

    def enqueue_task(self, task_id: str, priority: int = 0):
        """入队任务"""
        priority = max(0, min(3, priority))
        self._queue[priority].append(task_id)
        self._task_status[task_id] = 'pending'
        logger.info(f"Task {task_id} enqueued with priority {priority}")

    def dequeue_task(self) -> Optional[str]:
        """出队任务（高优先级优先）"""
        for priority in [3, 2, 1, 0]:
            if self._queue[priority]:
                task_id = self._queue[priority].pop(0)
                self._task_status[task_id] = 'dequeued'
                return task_id
        return None

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return sum(len(q) for q in self._queue.values())

    def set_task_status(self, task_id: str, status: str):
        """设置任务状态"""
        self._task_status[task_id] = status

    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        return self._task_status.get(task_id)

    def add_running_task(self, task_id: str):
        """添加运行中任务"""
        self._running_tasks.add(task_id)

    def remove_running_task(self, task_id: str):
        """移除运行中任务"""
        self._running_tasks.discard(task_id)

    def get_running_tasks(self) -> List[str]:
        """获取运行中任务列表"""
        return list(self._running_tasks)


class StorageManager:
    """存储管理器 - 统一管理 SQLite 和内存队列"""

    def __init__(self, db_path: str = None):
        self.db = SQLiteStorage(db_path)
        self.queue = InMemoryQueue()

    def save_task_with_queue(self, task: Dict[str, Any], priority: int = 0):
        """保存任务并入队"""
        self.db.save_task(task)
        self.queue.enqueue_task(task['id'], priority)
        self.queue.set_task_status(task['id'], 'pending')

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """获取下一个任务"""
        task_id = self.queue.dequeue_task()
        if task_id:
            return self.db.get_task(task_id)
        return None

    def update_task_progress(self, task_id: str, status: str, progress: int = 0):
        """更新任务进度"""
        self.db.update_task_status(task_id, status)
        self.queue.set_task_status(task_id, status)
        if status == 'running':
            self.queue.add_running_task(task_id)
        elif status in ['completed', 'failed']:
            self.queue.remove_running_task(task_id)

    def save_crawled_data_with_task(self, task_id: str, data: Dict[str, Any]):
        """保存爬取数据"""
        data['task_id'] = task_id
        self.db.save_crawled_data(data)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        mongo_stats = self.db.get_statistics()
        return {
            **mongo_stats,
            'queue_size': self.queue.get_queue_size(),
            'running_tasks_count': len(self.queue.get_running_tasks())
        }

    def close(self):
        """关闭连接"""
        pass  # SQLite 不需要显式关闭


# 创建全局存储管理器实例
storage_manager = StorageManager()
