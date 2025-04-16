import logging
from app import app
from scheduler import scheduler

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize and start the backup scheduler
scheduler.init_app(app)
if app.config.get("MONITOR_ENABLED", True):
    scheduler.start()
    logger.info("Started backup scheduler")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
