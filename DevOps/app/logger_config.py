import logging
import os

def setup_logger(app=None):
    """Setup logging for the application."""
    # Create absolute path for logs
    log_dir = "/logs"
    log_file = os.path.join(log_dir, 'app.log')
    
    # Create the directory if it doesn't exist
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Clear the log file by opening it in write mode and immediately closing it
    # This effectively erases the existing content
    with open(log_file, 'w') as f:
        pass
    
    # Use absolute path for log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)  # Log INFO and above to file

    # Create a console handler to log to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Log INFO and above to console

    # Set log format
    log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(log_format)
    console_handler.setFormatter(log_format)

    if app:
        # Only configure the app's logger, not the root logger
        app.logger.handlers.clear()  # Clear existing handlers
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.DEBUG)
        app.logger.propagate = False  # Prevent propagation to root logger
    else:
        # Configure the root logger if no app is provided
        logger = logging.getLogger()
        logger.handlers.clear()  # Clear existing handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.DEBUG)

    return app.logger if app else logging.getLogger()