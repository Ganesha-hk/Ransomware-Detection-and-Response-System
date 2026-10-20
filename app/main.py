import argparse
import uvicorn
from app.api.main import create_app
from app.core.config import load


def main():
    parser = argparse.ArgumentParser(description="Local RDRS educational detector")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--watch")
    args = parser.parse_args()
    config = load(args.config)
    uvicorn.run(
        create_app(args.config, args.watch), host=config.app.host, port=config.app.port, workers=1
    )


if __name__ == "__main__":
    main()
