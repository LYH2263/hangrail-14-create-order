import os
import tempfile

# 必须在导入 app.* 之前设置：让应用自身的 engine 也指向临时 sqlite，
# lifespan 中的 create_all 不会去连 Postgres；测试本身另外用 StaticPool 内存库。
_fd, _path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_path}"
os.environ["SEED_ON_EMPTY"] = "false"
