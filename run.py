import os
import uvicorn
from uvicorn.config import LOGGING_CONFIG
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

if __name__ == "__main__":
    # 修改默认日志配置
    LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s - %(levelname)s - %(message)s"
    LOGGING_CONFIG["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
    LOGGING_CONFIG["formatters"]["access"][
        "fmt"
    ] = '%(asctime)s - %(levelname)s - %(client_addr)s - "%(request_line)s" %(status_code)s'
    LOGGING_CONFIG["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"

    # 从环境变量获取主机和端口配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9999"))

    uvicorn.run(
        "app:app", 
        host=host, 
        port=port, 
        reload=True, 
        log_config=LOGGING_CONFIG
    )
