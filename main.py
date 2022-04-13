import getopt
import logging
import os
import platform
import sys
import re
import time
from itertools import product

def logger_config(log_path,logging_name):
    '''
    配置log
    :param log_path: 输出log路径
    :param logging_name: 记录中name，可随意
    :return:
    '''
    '''
    logger是日志对象，handler是流处理器，console是控制台输出（没有console也可以，将不会在控制台输出，会在日志文件中输出）
    '''
    # 获取logger对象,取名
    logger = logging.getLogger(logging_name)
    # 输出DEBUG及以上级别的信息，针对所有输出的第一层过滤
    logger.setLevel(level=logging.DEBUG)
    # 获取文件日志句柄并设置日志级别，第二层过滤
    handler = logging.FileHandler(log_path, encoding='UTF-8')
    handler.setLevel(logging.INFO)
    # 生成并设置文件日志格式
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    # console相当于控制台输出，handler文件输出。获取流句柄并设置日志级别，第二层过滤
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    # 为logger对象添加句柄
    logger.addHandler(handler)
    logger.addHandler(console)
    return logger

logger = logger_config(log_path='log.txt', logging_name='rename')

starts_with_rules = [
    ['[GM-Team]',
     [
         r'^\[GM-Team\]\[.*?\]\[.*?\]\[.*?\]\[.*?\]\[(.*?)\]',
     ],
     ]
]

# 需要重命名的文件后缀
COMMON_MEDIA_EXTS = [
    'flv',
    'mkv',
    'mp4',
    'avi',
    'rmvb',
    'm2ts',
    'wmv',
]

# 字幕文件
COMMON_CAPTION_EXTS = [
    'srt',
    'ass',
    'ssa',
    'sub',
    'smi',
]

# 语言文件
COMMON_LANG = [
    # 特殊命名处理
    'chs&jpn',
    'cht&jpn',
    # 一般命名
    'cn',
    'chs',
    'cht',
    'zh',
    'sc',
    'tc',
    'jp',
    'jap',
    'jpn',
    'en',
    'eng',
]

# 混合后缀
COMPOUND_EXTS = COMMON_MEDIA_EXTS + ['.'.join(x) for x in
                                     list(product(COMMON_LANG, COMMON_CAPTION_EXTS))] + COMMON_CAPTION_EXTS

# 获取入参
opts, args = getopt.getopt(sys.argv[1:], "n:l:g:f:r:d:c:z:t:i:j:k:")

# 入参定义
torrent_name = ""
classification = ""
label = ""
content_dir = ""
root_dir = ""
save_dir = ""
file_numer = ""
torrent_size = ""
tracker = ""
hash_v1 = ""
hash_v2 = ""
torrent_id = ""

for op, value in opts:
    if op == "-n":
        torrent_name = value
    elif op == "-l":
        classification = value
    elif op == "-g":
        label = value
    elif op == "-f":
        content_dir = value
    elif op == "-r":
        root_dir = value
    elif op == "-d":
        save_dir = value
    elif op == "-c":
        file_number = value
    elif op == "-z":
        torrent_size = value
    elif op == "-t":
        tracker = value
    elif op == "-i":
        hash_v1 = value
    elif op == "-j":
        hash_v2 = value
    elif op == "-k":
        torrent_id = value

# 重命名的文件移动到season目录下
move_up_to_season_folder = True
# 重命名延迟(秒) 配合qb使用的参数, 默认为15秒
rename_delay = 1

if not save_dir:
    # 没有路径参数直接退出
    sys.exit()

save_dir = save_dir.replace('\\', '/').replace('//', '/')

# 输出结果列表
file_lists = []
unknown = []

# 当前系统类型
system = platform.system()

#获取季数和集数
def get_season_and_ep(file_path):
    logger.info(f"{'解析文件', file_path}")
    season = None
    ep = None

    # 文件名
    file_full_name = os.path.basename(file_path)

    # 父级文件夹
    parent_folder_path = os.path.dirname(file_path)

    # 获取文件名和后缀
    file_name, ext = get_file_name_ext(file_full_name)

    _ = get_season_cascaded(parent_folder_path)
    if not _:
        logger.info(f"{'不在season文件夹内 忽略'}")
        return None, None

    # 忽略已按规则命名的文件
    pat = 'S\d{1,4}E\d{1,4}(\.5)?'
    if re.search(pat, file_name):
        logger.info(f"{'忽略'}")
        return None, None

    # 如果文件已经有 S01EP01 或者 S01E01 直接读取
    pat = '[Ss](\d{1,4})[Ee](\d{1,4}(\.5)?)'
    res = re.findall(pat, file_name.upper())
    if res:
        season, ep = res[0][0], res[0][1]
        season = str(int(season)).zfill(2)
        ep = str(int(ep)).zfill(2)
        return season, ep
    pat = '[Ss](\d{1,4})[Ee][Pp](\d{1,4}(\.5)?)'
    res = re.findall(pat, file_name.upper())
    if res:
        season, ep = res[0][0], res[0][1]
        season = str(int(season)).zfill(2)
        ep = str(int(ep)).zfill(2)
        return season, ep

    season = get_season_cascaded(parent_folder_path)

    # 获取不到季数 退出
    if not season:
        return None, None

    # 根据文件名获取集数

    # 特殊文件名使用配置的匹配规则
    # 确定是否满足特殊规则
    use_custom_rule = False
    for starts_str, rules in starts_with_rules:
        if file_name.startswith(starts_str):
            use_custom_rule = True
            for rule in rules:
                try:
                    res = re.findall(rule, file_name)
                    if res:
                        logger.info(f"{'根据特殊规则找到了集数'}")
                        ep = res[0]
                        season = str(int(season)).zfill(2)
                        ep = str(int(ep)).zfill(2)
                        return season, ep
                except Exception as e:
                    logger.info(f'{e}')
    # 如果满足特殊规则还没找到ep 直接返回空
    if use_custom_rule and not ep:
        return None, None

    # 其它不在特殊规则的继续往下正常查找匹配

    # 常见的括号
    bracket_pairs = [
        ['\[', '\]'],
        ['\(', '\)'],
        ['【', '】'],
        # 日语括号
        ['「', '」'],
    ]
    # 内容
    patterns = [
        # 1到4位数字
        '(\d{1,4}(\.5)?)',
        # 特殊文字处理
        '第(\d{1,4}(\.5)?)集',
        '第(\d{1,4}(\.5)?)话',
        '第(\d{1,4}(\.5)?)話',
        '[Ee][Pp](\d{1,4}(\.5)?)',
        '[Ee](\d{1,4}(\.5)?)',
        # 兼容SP01等命名
        '[Ss][Pp](\d{1,4}(\.5)?)',
        # 兼容v2命名
        '(\d{1,4}(\.5)?)[Vv]?\d?',
    ]
    # 括号和内容组合起来
    pats = []
    for pattern in patterns:
        for bracket_pair in bracket_pairs:
            pats.append(bracket_pair[0] + pattern + bracket_pair[1])
    # 查找
    for pat in pats:
        res = re.search(pat, file_name)
        if res:
            ep = res.group(1)
            break

    if not ep:
        logger.info(f"{'括号内未识别, 开始寻找括号外内容'}")
        # 把括号当分隔符排除掉括号内的文字
        pat = ''
        for bracket_pair in bracket_pairs:
            pat += bracket_pair[0] + '.*?' + bracket_pair[1] + '|'
        pat = pat[:-1]
        # 兼容某些用 - 分隔的文件
        pat += '|\-'
        res = re.split(pat, file_name)
        # 过滤空字符串
        res = list(filter(None, res))
        # 从后向前查找数字, 一般集数在剧集名称后面, 防止剧集有数字导致解析出问题
        res = res[::-1]

        # logger.info(f'{res}')

        if not ep:
            # 部分资源命名
            # 找 第x集
            pat = '第(\d{1,4}(\.5)?)[集话話]'
            for y in res:
                y = y.strip()
                res_sub = re.search(pat, y)
                if res_sub:
                    ep = res_sub.group(1)
                    break
        if not ep:
            # 找 EPXX
            pat = '[Ee][Pp](\d{1,4}(\.5)?)'
            for y in res:
                y = y.strip()
                res_sub = re.search(pat, y.upper())
                if res_sub:
                    ep = res_sub.group(1)
                    break

        # 特殊命名 SExx.xx 第2季第10集 SE02.10
        if not ep:
            # logger.info(f"{'找 EXX'}")
            pat = '[Ss][Ee](\d{1,2})\.(\d{1,2})'
            for y in res:
                y = y.strip()
                res_sub = re.search(pat, y.upper())
                if res_sub:
                    season = res_sub.group(1)
                    ep = res_sub.group(2)
                    break

        # 特殊命名 Sxx.xx 第2季第10集 s02.10
        if not ep:
            # logger.info(f"{'找 EXX'}")
            pat = '[Ss](\d{1,2})\.(\d{1,2})'
            for y in res:
                y = y.strip()
                res_sub = re.search(pat, y.upper())
                if res_sub:
                    season = res_sub.group(1)
                    ep = res_sub.group(2)
                    break

        # 匹配顺序调整
        if not ep:
            # logger.info(f"{'找 EXX'}")
            pat = '[Ee](\d{1,4}(\.5)?)'
            for y in res:
                y = y.strip()
                res_sub = re.search(pat, y.upper())
                if res_sub:
                    ep = res_sub.group(1)
                    break

        def extract_ending_ep(s):
            logger.info(f"{'找末尾是数字的子字符串'}")
            s = s.strip()
            # logger.info(f'{s}')
            ep = None

            # 兼容v2和.5格式 不兼容 9.33 格式
            # 12.5
            # 13.5
            # 10v2
            # 10.5v2
            pat = '(\d{1,4}(\.5)?)[Vv]?\d?'
            ep = None
            res_sub = re.search(pat, s)
            if res_sub:
                logger.info(f'{res_sub}')
                ep = res_sub.group(1)
                return ep

            pat = '\d{1,4}(\.5)?$'
            res_sub = re.search(pat, s)
            if res_sub:
                logger.info(f'{res_sub}')
                ep = res_sub.group(0)
                return ep
            return ep

        if not ep:
            for s in res:
                ep = extract_ending_ep(s)
                if ep:
                    break

    season = zero_fix(season)
    ep = zero_fix(ep)

    return season, ep


# 获取season目录
def get_season_path(file_path):
    b = os.path.dirname(file_path.replace('\\', '/'))
    season_path = None
    while (b):
        if not '/' in b:
            break
        b, fo = b.rsplit('/', 1)
        offset = None
        if get_season(fo):
            season_path = b + '/' + fo
    return season_path


# 多季集数修正
# def ep_offset_patch(file_path, ep):
#     b = os.path.dirname(file_path.replace('\\', '/'))
#     offset = None
#     while (b):
#         if offset:
#             break
#         if not '/' in b:
#             break
#         b, fo = b.rsplit('/', 1)
#         offset = None
#         if get_season(fo):
#             try:
#                 for fn in os.listdir(b + '/' + fo):
#                     if fn.lower() != 'all.txt':
#                         continue
#                     with open(b + '/' + fo + '/' + fn, encoding='utf-8') as f:
#                         offset = int(f.read().strip())
#                         break
#             except Exception as e:
#                 logger.info(f"{'集数修正报错了', e}")
#                 return ep
#     # 没有找到all.txt 尝试寻找qb-rss-manager的配置文件
#     # 1. config_ern.json 配置
#     # 2. 这两个exe在同一个目录下, 直接读取配置
#     if not offset:
#         qrm_config = None
#         config_ern_path_tmp = os.path.join(application_path, 'config_ern.json')
#         config_path_tmp = os.path.join(application_path, 'config.json')
#         if os.path.exists(config_ern_path_tmp):
#             try:
#                 with open(config_ern_path_tmp, encoding='utf-8') as f:
#                     qrm_config_file = json.loads(f.read())['qrm_config_file']
#                 with open(qrm_config_file, encoding='utf-8') as f:
#                     qrm_config = json.loads(f.read())
#             except Exception as e:
#                 logger.info(f"{'config_ern.json 读取错误', e}")
#         elif os.path.exists(config_path_tmp):
#
#             try:
#                 with open(config_path_tmp, encoding='utf-8') as f:
#                     qrm_config = json.loads(f.read())
#             except Exception as e:
#                 logger.info(f'{e}')
#         if qrm_config:
#             # logger.info(f"{'qrm_config', qrm_config}")
#             # logger.info(f"{'file_path', file_path}")
#             season_path = get_season_path(file_path)
#             # logger.info(f"{'season_path', season_path}")
#             for x in qrm_config['data_list']:
#                 if format_path(x[5]) == format_path(season_path):
#                     if x[4]:
#                         try:
#                             offset = int(x[4])
#                             logger.info(f"{'QRM获取到offset', offset}")
#                         except:
#                             pass
#
#     if offset:
#         if '.' in ep:
#             ep_int, ep_tail = ep.split('.')
#             ep_int = int(ep_int)
#             if int(ep_int) >= offset:
#                 ep_int = ep_int - offset
#                 ep = str(ep_int) + '.' + ep_tail
#         else:
#             ep_int = int(ep)
#             if ep_int >= offset:
#                 ep = str(ep_int - offset)
#
#     return zero_fix(ep)


# 统一补0
def zero_fix(s):
    if not s:
        return s
    # 删0
    s = s.lstrip('0')
    # 补0
    s = s.zfill(2)
    if '.' in s and s.index('.') == 1:
        s = '0' + s
    return s


# 逐级向上解析目录季数
def get_season_cascaded(full_path):
    full_path = os.path.abspath(full_path).replace('\\', '/').replace('//', '/')
    parent_folder_names = full_path.split('/')[::-1]
    season = None
    for parent_folder_name in parent_folder_names:
        season = get_season(parent_folder_name)
        if season:
            break
    return season

    # 获取季数


# 兼容
# 'Season 2'
# 'Season2'
# 's2'
# 'S2'
def get_season(parent_folder_name):
    season = None

    if parent_folder_name == 'Specials':
        # 兼容SP
        return '0'

    try:
        if 'season ' in parent_folder_name.lower():
            s = str(int(parent_folder_name.lower().replace('season ', '').strip()))
            season = s.zfill(2)
        elif 'season' in parent_folder_name.lower():
            s = str(int(parent_folder_name.lower().replace('season', '').strip()))
            season = s.zfill(2)
        elif parent_folder_name.lower()[0] == 's':
            season = str(int(parent_folder_name[1:])).strip().zfill(2)
    except:
        pass

    return season


# 获取文件名和后缀
def get_file_name_ext(file_full_name):
    file_name = None
    ext = None

    for x in COMPOUND_EXTS:
        if file_full_name.lower().endswith(x):
            ext = x
            file_name = file_full_name[:-(len(x) + 1)]
            break
    if not ext:
        file_name, ext = file_full_name.rsplit('.', 1)

    return file_name, ext


# 文件扩展名修正
# 1.统一小写
# 2.字幕文件 把sc替换成chs, tc替换成cht, jap替换成jpn
def fix_ext(ext):
    new_ext = ext.lower()

    # 双重生成器
    ori_list = [f'{y}.{x}' for x in COMMON_CAPTION_EXTS for y in ['sc', 'tc', 'jap']]
    new_list = [f'{y}.{x}' for x in COMMON_CAPTION_EXTS for y in ['chs', 'cht', 'jpn']]

    for i, x in enumerate(ori_list):
        if new_ext == x:
            new_ext = new_list[i]
            break

    return new_ext


# 修正路径斜杠
def format_path(file_path):
    if system == 'Windows':
        return file_path.replace('//', '/').replace('/', '\\')
    return file_path.replace('\\', '/').replace('//', '/')


if classification == "Anime":
    if os.path.isdir(content_dir):
        logger.info(f"{'文件夹处理'}")
        logger.info(f'{content_dir}')
        # 删除多余文件
        for root, dirs, files in os.walk(content_dir, False):
            for name in files:
                file_path = os.path.join(root, name).replace('\\', '/')
                file_path = os.path.abspath(file_path)
                # 不在 Season 目录下不处理
                # 父级文件夹
                parent_folder_path = os.path.dirname(file_path)

                _ = get_season_cascaded(parent_folder_path)
                if not _:
                    # logger.info(f"{'不在season文件夹内 忽略'}")
                    continue

                # 忽略部分文件
                if name.lower() in ['season.nfo', 'all.txt']:
                    continue
                file_name, ext = get_file_name_ext(name)

                # 只处理特定后缀
                if not ext.lower() in ['jpg', 'png', 'nfo', 'torrent']:
                    continue

                res = re.findall('^S(\d{1,4})E(\d{1,4}(\.5)?)', file_name.upper())
                if res:
                    continue
                else:
                    logger.info(f'{file_path}')
                    os.remove(file_path)

        # 遍历文件夹
        for root, dirs, files in os.walk(content_dir, False):
            for name in files:

                # 只处理媒体文件
                file_name, ext = get_file_name_ext(name)
                if not ext.lower() in COMPOUND_EXTS:
                    continue

                # 完整文件路径
                file_path = os.path.join(root, name).replace('\\', '/')
                file_path = os.path.abspath(file_path)
                parent_folder_path = os.path.dirname(file_path)
                season, ep = get_season_and_ep(file_path)
                logger.info(f'{season, ep}')
                # 重命名
                if season and ep:
                    # 修正集数
                    # ep = ep_offset_patch(file_path, ep)
                    new_name = os.path.basename(os.path.dirname(save_dir)) + " - " 'S' + season + 'E' + ep + " - " + file_name + '.' + fix_ext(ext)
                    logger.info(f'{new_name}')
                    if move_up_to_season_folder:
                        new_path = get_season_path(file_path) + '/' + new_name
                    else:
                        new_path = parent_folder_path + '/' + new_name
                    file_lists.append([format_path(file_path), format_path(new_path)])
                else:
                    logger.info(f"{'未能识别'}")
                    unknown.append(file_path)

    else:
        logger.info(f"{'单文件处理'}")
        logger.info(f'{content_dir}')
        file_path = os.path.abspath(content_dir.replace('\\', '/'))
        file_name, ext = get_file_name_ext(os.path.basename(file_path))
        parent_folder_path = os.path.dirname(file_path)
        if ext.lower() in COMPOUND_EXTS:
            season, ep = get_season_and_ep(file_path)
            if season and ep:
                # 修正集数
                # ep = ep_offset_patch(file_path, ep)
                new_name = os.path.basename(os.path.dirname(save_dir)) + " - " 'S' + season + 'E' + ep + " - " + file_name + '.' + fix_ext(ext)
                logger.info(f'{new_name}')
                if move_up_to_season_folder:
                    new_path = get_season_path(file_path) + '/' + new_name
                else:
                    new_path = parent_folder_path + '/' + new_name

                file_lists.append([file_path, new_path])
            else:
                logger.info(f"{'未能识别'}")
                unknown.append(file_path)

if unknown:
    logger.info(f"{'----- 未识别文件 -----'}")
    for x in unknown:
        logger.info(f'{x}')

if rename_delay:
    # 自动运行改名
    logger.info(f"{'重命名延迟等待中...'}")
    # 程序运行太快 会导致重命名失败 估计是文件被锁了 这里故意加个延迟(秒)
    time.sleep(rename_delay)

logger.info(f"{'file_lists', file_lists}")

for old, new in file_lists:
    try:
        # 检测文件能否重命名 报错直接忽略
        tmp_name = new + '.new'
        os.rename(old, tmp_name)

        # 目标文件已存在, 先删除
        if os.path.exists(new):
            os.remove(new)

        # 临时文件重命名
        os.rename(tmp_name, new)

        if not os.listdir(content_dir):
            os.removedirs(content_dir)

    except:
        pass

logger.info(f"{'运行完毕'}")
