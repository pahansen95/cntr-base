from OAIGateway import *

# Load configuration from environment variables with sensible defaults
AZUREOAI_URL = os.environ.get("AZUREOAI_URL", "http://127.0.0.1:9000")
CERT_PATH = os.environ.get("CERT_PATH", "cert.pem")
KEY_PATH = os.environ.get("KEY_PATH", "key.pem")
LISTEN_HOST = os.environ.get("LISTEN_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "50443"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# ------------------- Logging Setup -------------------
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

if __name__ == "__main__":
    logger.info(f"Starting OpenAI API Gateway on https://{LISTEN_HOST}:{LISTEN_PORT}")
    logger.info(f"Proxying to backend at {AZUREOAI_URL}")
    
    try:
        # Verify TLS files exist before starting
        verify_tls_files()
        
        # Start the server
        uvicorn.run(
            "gateway:app",
            host=LISTEN_HOST,
            port=LISTEN_PORT,
            ssl_keyfile=KEY_PATH,
            ssl_certfile=CERT_PATH,
            log_level=LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        logger.info("Gateway shutdown requested via keyboard interrupt")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Error starting server: {e}")
        sys.exit(1)