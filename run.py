# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()
from line_bot.app import app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
