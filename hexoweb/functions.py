import os
from core.QexoSettings import ALL_SETTINGS
import requests
from django.template.defaulttags import register
from core.QexoSettings import QEXO_VERSION
from .models import Cache, SettingModel, FriendModel, NotificationModel, CustomModel, StatisticUV, StatisticPV, ImageModel
import github
import json
from urllib.parse import quote, unquote
from datetime import timezone, timedelta, date, datetime
from time import time
from hashlib import md5
from urllib3 import disable_warnings
from markdown import markdown
from zlib import crc32 as zlib_crc32
from urllib.parse import quote
from time import strftime, localtime
import tarfile
import html2text as ht
from hexoweb.libs.onepush import notify, get_notifier
from hexoweb.libs.onepush import all_providers as onepush_providers
from hexoweb.libs.platforms import get_provider, all_providers, get_params
from hexoweb.libs.image import get_image_host
from hexoweb.libs.image import get_params as get_image_params
from hexoweb.libs.image import all_providers as all_image_providers
import yaml
import re
import shutil
from bs4 import BeautifulSoup

disable_warnings()


def get_setting(name):
    try:
        return SettingModel.objects.get(name=name).content
    except:
        return ""


def update_provider():
    global _Provider
    _provider = json.loads(get_setting("PROVIDER"))
    _Provider = get_provider(_provider["provider"], **_provider["params"])
    return _Provider


try:
    _Provider = update_provider()
except:
    print("Provider初始化失败, 跳过")
    pass


def Provider():
    try:
        return _Provider
    except:
        print("Provider获取错误, 重新初始化")
        return update_provider()


@register.filter  # 在模板中使用range()
def get_range(value):
    return range(1, value + 1)


@register.filter
def div(value, div):  # 保留两位小数的除法
    return round((value / div), 2)


def get_cdn():
    cdn_prev = get_setting("CDN_PREV")
    if not cdn_prev:
        save_setting("CDN_PREV", "https://unpkg.com/")
        cdn_prev = "https://unpkg.com/"
    return cdn_prev


def get_cdnjs():
    cdnjs = get_setting("CDNJS")
    if not cdnjs:
        save_setting("CDNJS", "https://cdn.staticfile.org/")
        cdnjs = "https://cdn.staticfile.org/"
    return cdnjs


def get_post(post):
    return Provider().get_post(post)


# 获取用户自定义的样式配置
def get_custom_config():
    context = {"cdn_prev": get_cdn(), "cdnjs": get_cdnjs(), "QEXO_NAME": get_setting("QEXO_NAME")}
    if not context["QEXO_NAME"]:
        save_setting('QEXO_NAME', 'Hexo管理面板')
        context["QEXO_NAME"] = get_setting("QEXO_NAME")
    context["QEXO_SPLIT"] = get_setting("QEXO_SPLIT")
    if not context["QEXO_SPLIT"]:
        save_setting('QEXO_SPLIT', ' - ')
        context["QEXO_SPLIT"] = get_setting("QEXO_SPLIT")
    context["QEXO_LOGO"] = get_setting("QEXO_LOGO")
    if not context["QEXO_LOGO"]:
        save_setting('QEXO_LOGO',
                     'https://unpkg.com/qexo-static@1.4.0/assets' +
                     '/img/brand/qexo.png')
        context["QEXO_LOGO"] = get_setting("QEXO_LOGO")
    context["QEXO_ICON"] = get_setting("QEXO_ICON")
    if not context["QEXO_ICON"]:
        save_setting('QEXO_ICON',
                     'https://unpkg.com/qexo-static@1.4.0/assets' +
                     '/img/brand/favicon.ico')
        context["QEXO_ICON"] = get_setting("QEXO_ICON")
    return context


# 更新缓存
def update_caches(name, content, _type="json"):
    caches = Cache.objects.filter(name=name)
    if caches.count():
        caches.delete()
    posts_cache = Cache()
    posts_cache.name = name
    if _type == "json":
        posts_cache.content = json.dumps(content)
    else:
        posts_cache.content = content
    posts_cache.save()
    print("重建{}缓存成功".format(name))


def update_posts_cache(s=None):
    if s:
        old_cache = Cache.objects.filter(name="posts")
        if old_cache.count():
            posts = json.loads(old_cache.first().content)
            i = 0
            while i < len(posts):
                if s.upper() not in posts[i]["name"].upper():
                    del posts[i]
                    i -= 1
                i += 1
            cache_name = "posts." + str(s)
            update_caches(cache_name, posts)
            return posts
    else:
        old_cache = False
    posts = Provider().get_posts()
    if s:
        if not old_cache.count():
            update_caches("posts", posts)
        i = 0
        while i < len(posts):
            if s.upper() not in posts[i]["name"].upper():
                del posts[i]
                i -= 1
            i += 1
    if s:
        cache_name = "posts." + str(s)
    else:
        cache_name = "posts"
    update_caches(cache_name, posts)
    return posts


def update_pages_cache(s=None):
    if s:
        old_cache = Cache.objects.filter(name="pages")
        if old_cache.count():
            posts = json.loads(old_cache.first().content)
            i = 0
            while i < len(posts):
                if s.upper() not in posts[i]["name"].upper():
                    del posts[i]
                    i -= 1
                i += 1
            cache_name = "pages." + str(s)
            update_caches(cache_name, posts)
            return posts
    results = Provider().get_pages()
    update_caches("pages", results)
    if not s:
        return results
    i = 0
    while i < len(results):
        if s.upper() not in results[i]["name"].upper():
            del results[i]
            i -= 1
        i += 1
    update_caches("pages." + str(s), results)
    return results


def update_configs_cache(s=None):
    if s:
        old_cache = Cache.objects.filter(name="configs")
        if old_cache.count():
            posts = json.loads(old_cache.first().content)
            i = 0
            while i < len(posts):
                if s.upper() not in posts[i]["name"].upper():
                    del posts[i]
                    i -= 1
                i += 1
            cache_name = "configs." + str(s)
            update_caches(cache_name, posts)
            return posts
    results = Provider().get_configs()
    update_caches("configs", results)
    if not s:
        return results
    i = 0
    while i < len(results):
        if s.upper() not in results[i]["name"].upper():
            del results[i]
            i -= 1
        i += 1
    update_caches("configs." + str(s), results)
    return results


def delete_all_caches():
    caches = Cache.objects.all()
    for cache in caches:
        if cache.name != "update":
            cache.delete()
    print("清除全部缓存成功")


def delete_posts_caches():
    caches = Cache.objects.all()
    for cache in caches:
        if cache.name[:5] == "posts":
            cache.delete()
    print("清除文章缓存成功")


def delete_pages_caches():
    caches = Cache.objects.all()
    for cache in caches:
        try:
            name = cache.name[:5]
        except:
            name = ""
        if name == "pages":
            cache.delete()
    print("清除页面缓存成功")


def save_setting(name, content):
    obj = SettingModel.objects.filter(name=name)
    if obj.count() == 1:
        obj.delete()
    if obj.count() > 1:
        for i in obj:
            i.delete()
    new_set = SettingModel()
    new_set.name = str(name)
    if content is not None:
        new_set.content = str(content)
    else:
        new_set.content = ""
    new_set.save()
    print("保存设置{} => {}".format(name, content))
    return new_set


def save_custom(name, content):
    obj = CustomModel.objects.filter(name=name)
    if obj.count() == 1:
        obj.delete()
    if obj.count() > 1:
        for i in obj:
            i.delete()
    new_set = CustomModel()
    new_set.name = str(name)
    if content is not None:
        new_set.content = str(content)
    else:
        new_set.content = ""
    new_set.save()
    print("保存自定义字段{} => {}".format(name, content))
    return new_set


def get_latest_version():
    context = dict()
    try:
        provider = json.loads(get_setting("PROVIDER"))
        if provider["provider"] == "github":
            user = github.Github(provider["params"]["token"])
            latest = user.get_repo("am-abudu/Qexo").get_latest_release()
            if latest.tag_name and (latest.tag_name != QEXO_VERSION):
                context["hasNew"] = True
            else:
                context["hasNew"] = False
            context["newer"] = latest.tag_name
            context["newer_link"] = latest.html_url
            context["newer_time"] = latest.created_at.astimezone(
                timezone(timedelta(hours=16))).strftime(
                "%Y-%m-%d %H:%M:%S")
            context["newer_text"] = markdown(latest.body).replace("<p>", "<p class=\"text-sm mb-0\">")
            context["status"] = True
        else:
            context["status"] = False
    except Exception as e:
        print("获取更新错误: " + repr(e))
        context["status"] = False
    return context


def check_if_api_auth(request):
    if request.POST.get("token") == get_setting("WEBHOOK_APIKEY"):
        return True
    if request.GET.get("token") == get_setting("WEBHOOK_APIKEY"):
        return True
    print(request.path + ": API鉴权失败 访问IP " + (request.META['HTTP_X_FORWARDED_FOR'] if 'HTTP_X_FORWARDED_FOR' in request.META.keys() else
                                              request.META['REMOTE_ADDR']))
    return False


def check_if_vercel():
    return True if os.environ.get("VERCEL") else False


def get_crc16(x, _hex=False):
    x = str(x)
    a = 0xFFFF
    b = 0xA001
    for byte in x:
        a ^= ord(byte)
        for i in range(8):
            last = a % 2
            a >>= 1
            if last == 1:
                a ^= b
    s = hex(a)
    return str(int(s[2:4] + s[4:6], 16)) if _hex is False else (s[2:4] + s[4:6])


def get_crc32(x, _hex=False):
    return str(zlib_crc32(x.encode("utf8"))) if _hex is False else hex(
        zlib_crc32(x.encode("utf8")))[2:]


def get_crc_by_time(_strtime, alg, rep):
    if rep == "hex":
        use_hex = True
    else:
        use_hex = False
    if alg != "crc16" and alg != "crc32":
        return ""
    return get_crc16(_strtime.replace(".", "0"), _hex=use_hex) if alg == "crc16" else get_crc32(
        _strtime.replace(".", "0"), _hex=use_hex)


def fix_all(all_settings=ALL_SETTINGS):
    counter = 0
    already = list()
    deleted = list()
    additions = list()
    settings = SettingModel.objects.all()
    for query in settings:
        if query.name not in already:
            already.append(query.name)
        else:
            deleted.append(query.name)
            query.delete()
            counter += 1
    for setting in all_settings:
        if (setting[0] not in already) or (setting[2]):
            additions.append(setting[0])
            save_setting(setting[0], setting[1])
            counter += 1
    print("已修复{}个设置".format(counter))
    print("删除字段" + str(deleted))
    print("修正字段" + str(additions))
    return counter


def get_project_detail():
    return {"token": get_setting("VERCEL_TOKEN"),
            "id": get_setting("PROJECT_ID")}


def checkBuilding(projectId, token):
    r = 0
    url = "https://api.vercel.com/v6/deployments/?projectId=" + projectId
    header = dict()
    header["Authorization"] = "Bearer " + token
    header["Content-Type"] = "application/json"
    response = requests.get(url, headers=header).json()
    result = response["deployments"]
    for deployment in result:
        if deployment['state'] == "BUILDING" or deployment['state'] == "INITIALIZING":
            r += 1
    return r


def file_get_contents(file):
    with open(file, 'r', encoding="utf8") as f:
        content = f.read()
    return content


def getEachFiles(base, path=""):
    file = list()
    handler = os.listdir(base + "/" + path)
    for item in handler:
        if item != '.git':
            fromfile = base + "/" + path + "/" + item
            if os.path.isdir(fromfile):
                file += getEachFiles(base, path + "/" + item)
            else:
                file.append({"file": path + "/" + item,
                             "data": file_get_contents(fromfile)})
    return file


def getIndexFile(base, path=""):
    index = ""
    handler = os.listdir(base + "/" + path)
    for item in handler:
        if item != 'manage.py':
            fromfile = base + "/" + path + "/" + item
            if os.path.isdir(fromfile):
                tmp = getIndexFile(base, path + "/" + item)
                if tmp:
                    index = tmp
        else:
            index = path
            break
    return index


def VercelUpdate(appId, token, sourcePath=""):
    if checkBuilding(appId, token):
        print("更新失败: 当前有部署正在进行")
        return {"status": False, "msg": "更新失败, 当前有部署正在进行"}
    url = "https://api.vercel.com/v13/deployments"
    header = dict()
    data = dict()
    header["Authorization"] = "Bearer " + token
    header["Content-Type"] = "application/json"
    data["name"] = "qexo"
    data["project"] = appId
    data["target"] = "production"
    if sourcePath == "":
        sourcePath = os.path.abspath("")
    data["files"] = getEachFiles(sourcePath)
    response = requests.post(url, data=json.dumps(data), headers=header)
    print("更新完成: " + response.text)
    return {"status": True, "msg": response.json()}


def VercelOnekeyUpdate(auth='am-abudu', project='Qexo', branch='master'):
    print("开始更新, 使用Vercel方案")
    vercel_config = get_project_detail()
    tmpPath = '/tmp'
    # 从github下载对应tar.gz，并解压
    url = 'https://github.com/' + auth + '/' + project + '/tarball/' + quote(branch) + '/'
    # print("download from " + url)
    _tarfile = tmpPath + '/github.tar.gz'
    with open(_tarfile, "wb") as file:
        file.write(requests.get(url).content)
    print("下载更新完成, 开始解压")
    # print("ext files")
    t = tarfile.open(_tarfile)
    t.extractall(path=tmpPath)
    t.close()
    os.remove(_tarfile)
    print("解压完成, 寻找Index目录")
    outPath = os.path.abspath(tmpPath + getIndexFile(tmpPath))
    # print("outPath: " + outPath)
    if outPath == '':
        return {"status": False, "msg": '更新失败: 未找到Index目录'}
    print("找到Index目录: " + outPath)
    return VercelUpdate(vercel_config["id"], vercel_config["token"], outPath)


def copy_all_files(src_dir, dst_dir):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    if os.path.exists(src_dir):
        for file in os.listdir(src_dir):
            file_path = os.path.join(src_dir, file)
            dst_path = os.path.join(dst_dir, file)
            if os.path.isfile(os.path.join(src_dir, file)):
                shutil.copyfile(file_path, dst_path)
            else:
                shutil.copytree(file_path, dst_path)


def LocalOnekeyUpdate(auth='am-abudu', project='Qexo', branch='master'):
    print("开始更新, 使用本地方案, 准备临时目录")
    Path = os.path.abspath("")
    tmpPath = os.path.abspath("./_tmp")
    if not os.path.exists(tmpPath):
        os.mkdir(tmpPath)
    _tarfile = tmpPath + '/github.tar.gz'
    try:
        url = 'https://github.com/' + auth + '/' + project + '/tarball/' + quote(branch) + '/'
        with open(_tarfile, "wb") as file:
            file.write(requests.get(url).content)
    except:
        print("下载更新失败, 尝试使用镜像服务器")
        url = 'https://hub.fastgit.xyz/' + auth + '/' + project + '/tarball/' + quote(branch) + '/'
        with open(_tarfile, "wb") as file:
            file.write(requests.get(url).content)
    print("下载更新完成, 正在解压缩...")
    t = tarfile.open(_tarfile)
    t.extractall(path=tmpPath)
    t.close()
    os.remove(_tarfile)
    outPath = os.path.abspath(tmpPath + getIndexFile(tmpPath))
    print("找到Index目录: " + outPath)
    filelist = os.listdir(Path)
    print("开始删除旧文件...")
    for filename in filelist:  # delete all files except tmp
        if not filename in ["_tmp", "configs.py", "db"]:
            if os.path.isfile(filename):
                os.remove(filename)
            elif os.path.isdir(filename):
                shutil.rmtree(filename)
            else:
                pass
    print("删除完成, 正在拷贝文件...")
    copy_all_files(outPath, Path)
    print("删除临时目录")
    shutil.rmtree(tmpPath)
    print("更新完成")
    return {"status": True, "msg": "更新成功!"}


def CreateNotification(label, content, now):
    N = NotificationModel()
    N.label = label
    N.content = content
    N.time = str(float(now))
    N.save()
    try:
        notify_me(label, content)
    except:
        pass
    return N


def GetNotifications():
    N = NotificationModel.objects.all()
    result = list()
    for notification in N:
        result.append(dict(
            label=notification.label,
            content=notification.content.replace("\n", "<br>"),
            timestamp=notification.time,
            time=strftime("%Y-%m-%d %H:%M:%S", localtime(float(notification.time)))
        ))
    return result


def DelNotification(_time):
    N = NotificationModel.objects.get(time=_time)
    N.delete()
    return N


def notify_me(title, content):
    config = get_setting("ONEPUSH")
    if config:
        config = json.loads(config)
    else:
        return False
    if config.get("markdown") == "true":
        text_maker = ht.HTML2Text()
        text_maker.bypass_tables = False
        content = text_maker.handle(content)
    ntfy = notify(config["notifier"], **config["params"], title="Qexo消息: " + title, content=content)
    try:
        return ntfy.text
    except:
        print("通知类型无输出信息, 使用OK缺省")
        return "OK"


def get_domain(domain):
    return domain.split("/")[2].split(":")[0] if domain[:4] == "http" else domain.split(":")[0]


def verify_provider(provider):
    try:
        provider = get_provider(provider["provider"], **provider["params"])
        home = provider.get_path("")
        hexo = 0
        indexhtml = 0
        source = 0
        pack = 0
        theme = 0
        theme_dir = 0
        config_hexo = 0
        config_theme = 0
        status = 0
        # 校验根目录文件
        for file in home["data"]:
            if file["name"] == "index.html" and file["type"] == "file":
                indexhtml = 1
            if file["name"] == "source" and file["type"] == "dir":
                source = 1
            if file["name"] == "themes" and file["type"] == "dir":
                theme_dir = 1
            if file["name"] == "package.json" and file["type"] == "file":
                pack = "package.json"
            if file["name"] == "_config.yml" and file["type"] == "file":
                config_hexo = "_config.yml"
        # 读取主题 校验主题配置
        try:
            if config_hexo:
                res = provider.get_content("_config.yml")
                content = yaml.load(res, Loader=yaml.SafeLoader)
                if content.get("theme"):
                    theme = content.get("theme")
                    for file in home["data"]:
                        if file["name"] == "_config.{}.yml".format(theme) and file["type"] == "file":
                            config_theme = "_config.{}.yml".format(theme)
                            break
                    if (not config_theme) and theme_dir:
                        theme_path = provider.get_path("themes/" + theme)
                        for file in theme_path["data"]:
                            if file["name"] == "_config.yml" and file["type"] == "file":
                                config_theme = "themes/" + theme + "_config.yml"
                                break
        except:
            pass
        # 校验 Package.json 及 Hexo
        if pack:
            try:
                content = json.loads(provider.get_content("package.json"))
                if content:
                    if content.get("hexo"):
                        if content["hexo"].get("version"):
                            hexo = content["hexo"].get("version")
                    if content.get("dependencies"):
                        if content["dependencies"].get("hexo"):
                            hexo = content["dependencies"].get("hexo")
            except:
                pass
        # 总结校验
        if hexo and config_hexo and (not indexhtml) and source and theme and pack and config_theme:
            status = 1
        return {
            "status": status,
            "hexo": hexo,
            "config_theme": config_theme,
            "config_hexo": config_hexo,
            "indexhtml": indexhtml,
            "source": source,
            "theme": theme,
            "theme_dir": theme_dir,
            "package": pack,
        }
    except:
        return {"status": -1}


def get_post_details(article, safe=True):
    front_matter = yaml.safe_load(
        re.search(r"---([\s\S]*?)---", article, flags=0).group()[3:-4].replace("{{ date }}",
                                                                               strftime("%Y-%m-%d %H:%M:%S", localtime(time()))).replace(
            "{{ abbrlink }}", get_crc_by_time(str(time()), get_setting("ABBRLINK_ALG"), get_setting("ABBRLINK_REP"))).replace("{",
                                                                                                                              "").replace(
            "}", "")) if article[:3] == "---" else json.loads(
        "{{{}}}".format(re.search(r";;;([\s\S]*?);;;", article, flags=0).group()[3:-4].replace("{{ date }}",
                                                                                               strftime("%Y-%m-%d %H:%M:%S",
                                                                                                        localtime(time()))).replace(
            "{{ abbrlink }}", get_crc_by_time(str(time()), get_setting("ABBRLINK_ALG"), get_setting("ABBRLINK_REP")))))
    for key in front_matter.keys():
        if type(front_matter.get(key)) == datetime:
            front_matter[key] = front_matter[key].strftime("%Y-%m-%d %H:%M:%S")
    if safe:
        passage = repr(re.search(r"[;-][;-][;-]([\s\S]*)", article[3:], flags=0).group()[3:]).replace("<", "\\<").replace(">",
                                                                                                                          "\\>").replace(
            "!", "\\!")
    else:
        passage = re.search(r"[;-][;-][;-]([\s\S]*)", article[3:], flags=0).group()[3:]
    return front_matter, passage


def export_settings():
    all_settings = SettingModel.objects.all()
    settings = list()
    for setting in all_settings:
        settings.append({"name": setting.name, "content": setting.content})
    return settings


def export_images():
    all_settings = ImageModel.objects.all()
    settings = list()
    for setting in all_settings:
        settings.append({"name": setting.name, "url": setting.url, "size": setting.size, "date": setting.date, "type": setting.type})
    return settings


def export_friends():
    all_ = FriendModel.objects.all()
    ss = list()
    for s in all_:
        ss.append({"name": s.name, "url": s.url, "imageUrl": s.imageUrl, "time": s.time, "description": s.description, "status": s.status})
    return ss


def export_notifications():
    all_ = NotificationModel.objects.all()
    ss = list()
    for s in all_:
        ss.append({"time": s.time, "label": s.label, "content": s.content})
    return ss


def export_customs():
    all_ = CustomModel.objects.all()
    ss = list()
    for s in all_:
        ss.append({"name": s.name, "content": s.content})
    return ss


def export_uv():
    all_ = StatisticUV.objects.all()
    ss = list()
    for s in all_:
        ss.append({"ip": s.ip})
    return ss


def export_pv():
    all_ = StatisticPV.objects.all()
    ss = list()
    for s in all_:
        ss.append({"url": s.url, "number": s.number})
    return ss


def import_settings(ss):
    for s in ss:
        save_setting(s["name"], s["content"])
    return True


def import_images(ss):
    _all = ImageModel.objects.all()
    for i in _all:
        i.delete()
    for s in ss:
        image = ImageModel()
        image.name = s["name"]
        image.url = s["url"]
        image.size = s["size"]
        image.date = s["date"]
        image.type = s["type"]
        image.save()
    return True


def import_friends(ss):
    _all = FriendModel.objects.all()
    for i in _all:
        i.delete()
    for s in ss:
        friend = FriendModel()
        friend.name = s["name"]
        friend.url = s["url"]
        friend.imageUrl = s["imageUrl"]
        friend.time = s["time"]
        friend.description = s["description"]
        friend.status = s["status"]
        friend.save()
    return True


def import_notifications(ss):
    _all = NotificationModel.objects.all()
    for i in _all:
        i.delete()
    for s in ss:
        notification = NotificationModel()
        notification.time = s["time"]
        notification.label = s["label"]
        notification.content = s["content"]
        notification.save()
    return True


def import_custom(ss):
    _all = CustomModel.objects.all()
    for i in _all:
        i.delete()
    for s in ss:
        custom = CustomModel()
        custom.name = s["name"]
        custom.content = s["content"]
        custom.save()
    return True


def import_uv(ss):
    _all = StatisticUV.objects.all()
    for i in _all:
        i.delete()
    for s in ss:
        uv = StatisticUV()
        uv.ip = s["ip"]
        uv.save()
    return True


def import_pv(ss):
    _all = StatisticPV.objects.all()
    for i in _all:
        i.delete()
    for s in ss:
        pv = StatisticPV()
        pv.url = s["url"]
        pv.number = s["number"]
        pv.save()
    return True


def excerpt_post(content, length):
    result = ""
    content = markdown(content)
    soup = BeautifulSoup(content, 'html.parser')
    for dom in soup:
        if dom.name and dom.name not in ["script", "style"]:
            result += re.sub("{(.*?)}", '', dom.get_text()).replace("\n", " ")
            result += " " if result[-1] != " " else ""
    return result[:int(length)] + "..."


# print(" ......................阿弥陀佛......................\n" +
#       "                       _oo0oo_                      \n" +
#       "                      o8888888o                     \n" +
#       "                      88\" . \"88                     \n" +
#       "                      (| -_- |)                     \n" +
#       "                      0\\  =  /0                     \n" +
#       "                   ___/‘---’\\___                   \n" +
#       "                  .' \\|       |/ '.                 \n" +
#       "                 / \\\\|||  :  |||// \\                \n" +
#       "                / _||||| -卍-|||||_ \\               \n" +
#       "               |   | \\\\\\  -  /// |   |              \n" +
#       "               | \\_|  ''\\---/''  |_/ |              \n" +
#       "               \\  .-\\__  '-'  ___/-. /              \n" +
#       "             ___'. .'  /--.--\\  '. .'___            \n" +
#       "         .\"\" ‘<  ‘.___\\_<|>_/___.’>’ \"\".          \n" +
#       "       | | :  ‘- \\‘.;‘\\ _ /’;.’/ - ’ : | |        \n" +
#       "         \\  \\ ‘_.   \\_ __\\ /__ _/   .-’ /  /        \n" +
#       "    =====‘-.____‘.___ \\_____/___.-’___.-’=====     \n" +
#       "                       ‘=---=’                      \n" +
#       "                                                    \n" +
#       "....................佛祖保佑 ,永无BUG...................")

print("           _               _ \n" +
      "     /\\   | |             | |\n" +
      "    /  \\  | |__  _   _  __| |_   _ \n" +
      "   / /\\ \\ | |_ \\| | | |/ _| | | | |\n" +
      "  / ____ \\| |_) | |_| | (_| | |_| |\n" +
      " /_/    \\_\\____/ \\____|\\____|\\____|")

print("当前环境: " + ("Vercel" if check_if_vercel() else "本地"))
