import os
from .app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5050"))
    # bind all interfaces for sharing on local network
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
