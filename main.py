from app import app
from config import config_init

import commands.user

if __name__ == '__main__':
    config_init()
    app.run()