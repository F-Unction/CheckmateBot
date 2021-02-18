# CheckmateBot
CheckmateBot

框架：<https://github.com/Polythefake/KanaBot>

**~~特别提示：验证码无需用户手动输入~~**

考虑到PaddleHub安装困难，该功能暂时停用，正在寻找替代方案

在使用前，请在目录下创建`config.json`，填写以下内容：
```json
{
  "username": "xxx",
  "password": "xxx",
  "roomID": "xxx",
  "controller": "xxx"
}
```

### 关于控制者

为了方便远程控制，特推出控制者功能，被标记为控制者的用户可以执行高级命令。

### 命令说明

在每个命令中，```[x]``` 表示 ```x``` 是必选参数，```(x)``` 表示 ```x``` 是可选参数。

| 命令 |含义  |特殊说明|花费分数|是否为高级命令|
| :----------: | :----------: | :----------: | :----------: | :----------: |
|```help (command)```  |查看命令列表（或命令command的用法）  |/ |0|否|
|```query (i)```  |查询自己（或玩家i）的Rating  |/ |0|否|
|```info```  |获取Rating排行榜  |/ |0|否|
|```kill```  |关闭Bot  |/ |/|**是**|
|```enter [roomid]```  |进入roomid房间  |/ |/|**是**|
|```setsecret```  |切换房间私密状态  |/ |/|**是**|
|```savedata```  |保存游戏数据  |目前只保存分数列表和单挑获胜次数列表 |/|**是**|
|```readdata```  |读取游戏数据  |/ |/|**是**|
|```setautosave```  |切换自动保存  |每局游戏结束后保存一次（默认值`False`） |/|**是**|
|```setrating [uname] [x]```  |设置用户名为uname的玩家Rating为x  |/ |/|**是**|
|```settime [uname] [x]```  |设置用户名为uname的玩家单挑获胜次数为x  |/ |/|**是**|