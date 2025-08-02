import schedule
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TaskScheduler:
    """A flexible task scheduler for running periodic jobs."""
    
    def __init__(self):
        """Initialize the task scheduler."""
        self.scheduler = schedule.Scheduler()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # Default schedule configuration
        self.default_schedule = {
            'scrape_amazon': {'interval': 3600},  # 1 hour
            'scrape_ebay': {'interval': 3600},    # 1 hour
            'scrape_walmart': {'interval': 7200}, # 2 hours
            'scrape_aliexpress': {'interval': 10800},  # 3 hours
            'analyze_opportunities': {'interval': 1800},  # 30 minutes
            'process_orders': {'interval': 300},  # 5 minutes
            'sync_inventory': {'interval': 3600}  # 1 hour
        }
        
        # Task registry
        self.tasks: Dict[str, Callable] = {}
    
    def register_task(self, name: str, task_func: Callable) -> None:
        """Register a new task with the scheduler.
        
        Args:
            name: Unique name for the task
            task_func: Callable that will be executed when the task runs
        """
        with self.lock:
            self.tasks[name] = task_func
    
    def _run_task_with_logging(self, name: str) -> None:
        """Run a task with proper error handling and logging."""
        logger.info(f"Starting task: {name}")
        start_time = time.time()
        
        try:
            self.tasks[name]()
            status = "completed"
        except Exception as e:
            logger.error(f"Error in task {name}: {str(e)}", exc_info=True)
            status = f"failed: {str(e)}"
        
        duration = time.time() - start_time
        logger.info(f"Task {name} {status} in {duration:.2f} seconds")
    
    def _schedule_task(self, name: str, interval: int) -> None:
        """Schedule a task to run at regular intervals."""
        if name not in self.tasks:
            logger.warning(f"Task {name} not found in registry")
            return
        
        # Clear any existing schedule for this task
        schedule.clear(name)
        
        # Schedule the task
        schedule.every(interval).seconds.do(
            self._run_task_with_logging, name
        ).tag(name)
        
        logger.info(f"Scheduled task {name} to run every {interval} seconds")
    
    def update_schedule(self, schedule_config: Dict[str, Dict[str, Any]]) -> None:
        """Update the schedule configuration.
        
        Args:
            schedule_config: Dictionary mapping task names to their schedule config
                            Example: {'task_name': {'interval': 3600}}
        """
        with self.lock:
            for name, config in schedule_config.items():
                if 'interval' in config:
                    self._schedule_task(name, config['interval'])
    
    def run_continuously(self, interval: int = 1) -> None:
        """Run the scheduler in a background thread.
        
        Args:
            interval: How often to check for pending tasks (in seconds)
        """
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        def run():
            try:
                while self.running:
                    schedule.run_pending()
                    time.sleep(interval)
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}", exc_info=True)
                self.running = False
        
        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        logger.info("Scheduler started")
    
    def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def get_scheduled_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all scheduled jobs."""
        jobs = {}
        for job in schedule.get_jobs():
            job_name = job.tags.pop() if job.tags else 'unknown'
            jobs[job_name] = {
                'next_run': job.next_run.isoformat() if job.next_run else None,
                'interval': job.interval.total_seconds() if job.interval else None,
                'last_run': job.last_run.isoformat() if job.last_run else None
            }
        return jobs
    
    def run_task_now(self, name: str) -> bool:
        """Run a task immediately.
        
        Args:
            name: Name of the task to run
            
        Returns:
            bool: True if the task was found and started, False otherwise
        """
        if name not in self.tasks:
            logger.warning(f"Task {name} not found")
            return False
        
        # Run the task in a separate thread to avoid blocking
        def run_task():
            self._run_task_with_logging(name)
        
        thread = threading.Thread(target=run_task, daemon=True)
        thread.start()
        return True

# Example usage
if __name__ == "__main__":
    import os
    import random
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create a scheduler instance
    scheduler = TaskScheduler()
    
    # Define some example tasks
    def scrape_amazon():
        print("Scraping Amazon...")
        time.sleep(random.uniform(1, 3))
        if random.random() < 0.1:  # 10% chance of failure
            raise Exception("Failed to scrape Amazon")
    
    def analyze_opportunities():
        print("Analyzing opportunities...")
        time.sleep(random.uniform(0.5, 2))
    
    def process_orders():
        print("Processing orders...")
        time.sleep(random.uniform(0.5, 1.5))
    
    # Register tasks
    scheduler.register_task('scrape_amazon', scrape_amazon)
    scheduler.register_task('analyze_opportunities', analyze_opportunities)
    scheduler.register_task('process_orders', process_orders)
    
    # Configure the schedule
    schedule_config = {
        'scrape_amazon': {'interval': 30},  # 30 seconds for demo
        'analyze_opportunities': {'interval': 20},  # 20 seconds for demo
        'process_orders': {'interval': 15}  # 15 seconds for demo
    }
    scheduler.update_schedule(schedule_config)
    
    # Start the scheduler
    scheduler.run_continuously()
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.stop()
        print("Scheduler stopped")
