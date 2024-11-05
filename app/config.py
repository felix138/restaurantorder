class Config:
    # ... 其他配置项 ...
    
    # 收银机接口配置
    POS_ENABLED = False  # 默认不启用收银机接口
    POS_TYPE = 'none'    # 收银机类型：none, standard, custom
    POS_API_URL = ''     # 收银机API地址
    POS_API_KEY = ''     # 收银机API密钥 