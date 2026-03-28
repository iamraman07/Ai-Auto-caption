import threading
import time
import uuid

class SimpleQueueManager:
    def __init__(self):
        self.active_jobs = 0
        self.max_jobs = 1       # Whisper is heavy, only 1 transcription at a time!
        self.max_queue = 5      # Maximum 5 people waiting in line
        self.queue = []         # Holds pending tasks
        self.results = {}       # Holds the output or status of jobs
        
        # Start the background worker thread that watches the queue independently
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def add_task(self, func, *args, **kwargs) -> str:
        """
        Adds a fast or heavy function to the queue. Returns the job ID.
        """
        job_id = str(uuid.uuid4())
        self.queue.append({
            "id": job_id, 
            "func": func, 
            "args": args, 
            "kwargs": kwargs
        })
        self.results[job_id] = {"status": "queued"}
        return job_id

    def get_status(self, job_id: str) -> dict:
        return self.results.get(job_id, {"status": "not_found"})

    def _worker(self):
        """
        The background process loop that executes tasks sequentially.
        """
        while True:
            # If system has capacity and the queue is not empty:
            if self.active_jobs < self.max_jobs and self.queue:
                task = self.queue.pop(0)
                self.active_jobs += 1
                job_id = task["id"]
                self.results[job_id]["status"] = "processing"
                
                try:
                    # Execute the heavy AI logic
                    result = task["func"](*task["args"], **task["kwargs"])
                    self.results[job_id]["status"] = "completed"
                    self.results[job_id]["result"] = result
                except Exception as e:
                    self.results[job_id]["status"] = "failed"
                    self.results[job_id]["error"] = str(e)
                finally:
                    # Free up the worker slots
                    self.active_jobs -= 1
                    
            time.sleep(1) # Sleep to avoid maxing out CPU in an infinite empty while-loop

# Expose a global instance
queue_manager = SimpleQueueManager()
