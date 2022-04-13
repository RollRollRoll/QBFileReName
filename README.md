# QBFileReName

Qbittorrent 外部脚本程序 用于下载后自动重命名文件为「动漫名(年份) - SXXEXX - 文件原始名称」

Windows系统中Qbittorrent必须带上python的完整路径 C:\Users\Administrator\AppData\Local\Programs\Python\Python310\python C:\Tool\rename\rename.py -l %L -f "%F" -r "%R" -d "%D"

会自动删除重命名后文件夹为空的content_dir
