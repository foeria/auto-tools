"""
数据存储模块
支持MongoDB和Redis存储
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import redis
import json
import logging

logger = logging.getLogger(__name__)


class MongoDBStorage:
    """MongoDB存储"""
    
    def __init__(self, uri: str = 'mongodb://localhost:27017', db_name: str = 'smart_crawler'):
        self.client = MongoClient(uri)
        self.db: Database = self.client[db_name]
        self._tasks_collection = None
        self._data_collection = None
        self._templates_collection = None
    
    @property
    def tasks_collection(self) -> Collection:
        if self._tasks_collection is None:
            self._tasks_collection = self.db['tasks']
            self._tasks_collection.create_index('created_at')
            self._tasks_collection.create_index('status')
        return self._tasks_collection
    
    @property
    def data_collection(self) -> Collection:
        if self._data_collection is None:
            self._data_collection = self.db['crawled_data']
            self._data_collection.create_index('task_id')
            self._data_collection.create_index('url')
        return self._data_collection
    
    @property
    def templates_collection(self) -> Collection:
        if self._templates_collection is None:
            self._templates_collection = self.db['templates']
        return self._templates_collection
    
    def save_task(self, task: Dict[str, Any]) -> str:
        task['updated_at'] = datetime.now()
        result = self.tasks_collection.update_one(
            {'id': task['id']},
            {'$set': task},
            upsert=True
        )
        return task['id']
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.tasks_collection.find_one({'id': task_id})
    
    def update_task_status(self, task_id: str, status: str, result: Dict[str, Any] = None):
        update_data = {
            'status': status,
            'updated_at': datetime.now()
        }
        if result:
            update_data['result'] = result
        if status == 'completed':
            update_data['completed_at'] = datetime.now()
        
        self.tasks_collection.update_one(
            {'id': task_id},
            {'$set': update_data}
        )
    
    def list_tasks(self, status: str = None, limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
        query = {}
        if status:
            query['status'] = status
        
        return list(
            self.tasks_collection.find(query)
            .sort('created_at', -1)
            .skip(skip)
            .limit(limit)
        )
    
    def save_crawled_data(self, data: Dict[str, Any]) -> str:
        data['created_at'] = datetime.now()
        result = self.data_collection.insert_one(data)
        return str(result.inserted_id)
    
    def get_crawled_data(self, task_id: str) -> List[Dict[str, Any]]:
        return list(self.data_collection.find({'task_id': task_id}))
    
    def save_template(self, template: Dict[str, Any]) -> str:
        template['updated_at'] = datetime.now()
        self.templates_collection.update_one(
            {'id': template['id']},
            {'$set': template},
            upsert=True
        )
        return template['id']
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        return self.templates_collection.find_one({'id': template_id})
    
    def list_templates(self) -> List[Dict[str, Any]]:
        return list(self.templates_collection.find())
    
    def delete_template(self, template_id: str) -> bool:
        result = self.templates_collection.delete_one({'id': template_id})
        return result.deleted_count > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        total_tasks = self.tasks_collection.count_documents({})
        completed_tasks = self.tasks_collection.count_documents({'status': 'completed'})
        failed_tasks = self.tasks_collection.count_documents({'status': 'failed'})
        running_tasks = self.tasks_collection.count_documents({'status': 'running'})
        
        total_data = self.data_collection.count_documents({})
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'total_data_records': total_data
        }
    
    def close(self):
        self.client.close()


class RedisStorage:
    """Redis存储 - 用于任务队列和缓存"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, db: int = 0):
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.task_queue = 'task_queue'
        self.task_prefix = 'task:'
        self.status_prefix = 'status:'
    
    def enqueue_task(self, task_id: str, priority: int = 0):
        self.client.zadd(self.task_queue, {task_id: priority})
        logger.info(f"Task {task_id} enqueued with priority {priority}")
    
    def dequeue_task(self) -> Optional[str]:
        tasks = self.client.zrange(self.task_queue, 0, 0)
        if tasks:
            task_id = tasks[0]
            self.client.zrem(self.task_queue, task_id)
            return task_id
        return None
    
    def get_queue_size(self) -> int:
        return self.client.zcard(self.task_queue)
    
    def set_task_status(self, task_id: str, status: str, ttl: int = 86400):
        key = f"{self.status_prefix}{task_id}"
        self.client.setex(key, ttl, status)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        key = f"{self.status_prefix}{task_id}"
        return self.client.get(key)
    
    def set_task_data(self, task_id: str, data: Dict[str, Any], ttl: int = 86400):
        key = f"{self.task_prefix}{task_id}"
        self.client.setex(key, ttl, json.dumps(data))
    
    def get_task_data(self, task_id: str) -> Optional[Dict[str, Any]]:
        key = f"{self.task_prefix}{task_id}"
        data = self.client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def add_running_task(self, task_id: str):
        self.client.sadd('running_tasks', task_id)
    
    def remove_running_task(self, task_id: str):
        self.client.srem('running_tasks', task_id)
    
    def get_running_tasks(self) -> List[str]:
        return list(self.client.smembers('running_tasks'))
    
    def close(self):
        self.client.close()


class StorageManager:
    """存储管理器 - 统一管理MongoDB和Redis"""
    
    def __init__(self, mongo_uri: str = 'mongodb://localhost:27017', 
                 mongo_db: str = 'smart_crawler',
                 redis_host: str = 'localhost',
                 redis_port: int = 6379):
        self.mongo = MongoDBStorage(mongo_uri, mongo_db)
        self.redis = RedisStorage(redis_host, redis_port)
    
    def save_task_with_queue(self, task: Dict[str, Any], priority: int = 0):
        self.mongo.save_task(task)
        self.redis.enqueue_task(task['id'], priority)
        self.redis.set_task_status(task['id'], 'pending')
    
    def get_next_task(self) -> Optional[Dict[str, Any]]:
        task_id = self.redis.dequeue_task()
        if task_id:
            return self.mongo.get_task(task_id)
        return None
    
    def update_task_progress(self, task_id: str, status: str, progress: int = 0):
        self.mongo.update_task_status(task_id, status)
        self.redis.set_task_status(task_id, status)
        if status == 'running':
            self.redis.add_running_task(task_id)
        elif status in ['completed', 'failed']:
            self.redis.remove_running_task(task_id)
    
    def save_crawled_data_with_task(self, task_id: str, data: Dict[str, Any]):
        data['task_id'] = task_id
        self.mongo.save_crawled_data(data)
    
    def get_statistics(self) -> Dict[str, Any]:
        mongo_stats = self.mongo.get_statistics()
        queue_size = self.redis.get_queue_size()
        running_tasks = self.redis.get_running_tasks()
        
        return {
            **mongo_stats,
            'queue_size': queue_size,
            'running_tasks_count': len(running_tasks)
        }
    
    def close(self):
        self.mongo.close()
        self.redis.close()


storage_manager = StorageManager()
