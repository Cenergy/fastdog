import os
import sys
from pathlib import Path

os.environ["ADMIN_USER_MODEL"] = "User"
os.environ["ADMIN_USER_MODEL_USERNAME_FIELD"] = "username"
os.environ["ADMIN_SECRET_KEY"] = "secret"
os.environ["ADMIN_DISABLE_CROP_IMAGE"] = "True"


sys.path.append(str(Path(__file__).resolve().parent))