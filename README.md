# CheckmateBot
CheckmateBot

框架：<https://github.com/Polythefake/KanaBot>

基本版：<https://gitee.com/OI-Master/checkmatebot/>

**特别提示：验证码无需用户手动输入**

验证码破解器使用了[腾讯云OCR](https://cloud.tencent.com/document/product/866)

在使用前，请在目录下创建`config.json`，填写以下内容：
```json
{
  "username": "xxx",
  "password": "xxx",
  "roomID": "xxx",
  "controller": "xxx",
  "secretId": "xxx",
  "secretKey": "xxx"
}
```

### 关于控制者

为了方便远程控制，特推出控制者功能，被标记为控制者的用户可以执行高级命令。

### 命令说明

在每个命令中，```[x]``` 表示 ```x``` 是必选参数，```(x)``` 表示 ```x``` 是可选参数。

| 命令 |含义  |特殊说明|是否为高级命令|
| :----------: | :----------: | :----------: | :----------: |
|```help (command)```  |查看命令列表（或命令command的用法）  |/|否|
|```query (i)```  |查询自己（或玩家i）的用户信息  |/|否|
|```info```  |获取Rating排行榜前10名  |/| 否|
|```predict (i)```  |预测自己（或房内玩家i）下局Rating变化  |/| 否|
|```stats (i)```  |获取自己（或玩家i）的统计数据|/| 否|
|```kill```  |关闭Bot  |/|**是**|
|```enter [roomid]```  |进入roomid房间  |/|**是**|
|```setsecret```  |切换房间私密状态  |/|**是**|
|```savedata```  |保存游戏数据  |/|**是**|
|```readdata```  |读取游戏数据  |/|**是**|
|```setautosave```  |切换自动保存  |每局游戏结束后保存一次|**是**|
|```setdata [uname] [key] [x]```  |设置用户名为uname的玩家的key为x  |key可以是`Rating`、`ban`等，详见数据库|**是**|
