import utils
import offset_fucker
import os.path
import os
import json
import requests
import shutil
import re
import tarfile
import time

from pypdl import Pypdl
from flask import Flask, request
from ar import Archive

library_manager = utils.LibraryManager()
app_info = ""
version = ""
full_version = ""
app = Flask("SignerServer")

@app.route("/", methods=["GET"])
def index():
    # 302 to url
    return "", 302, {"Location": "https://t.me/+6HNTeJO0JqtlNmRl"}

@app.route("/s", methods=["GET", "POST"])
@app.route("/sign", methods=["GET", "POST"])
def sign():
    cmd = ""
    seq = 0
    src = b""
    if request.method == "GET":
        cmd = request.args.get("cmd", "wtlogin.login")
        seq_str = request.args.get("seq", "281")
        try:
            seq = int(seq_str)
        except:
            return {"error": "seq is not int"}, 400
        src_hex = request.args.get("src", "0101")
        try:
            src = bytes.fromhex(src_hex)
        except:
            return {"error": "failed to parse src"}, 400
    else:
        post_json = request.get_json()
        if "cmd" not in post_json:
            return {"error": "cmd is missing"}, 400
        if "seq" not in post_json:
            return {"error": "seq is missing"}, 400
        if "src" not in post_json:
            return {"error": "src is missing"}, 400
        
        cmd = str(post_json["cmd"])
        
        try:
            seq = int(post_json["seq"])
        except:
            return {"error": "failed to parse seq"}, 400
        
        try:
            src = bytes.fromhex(post_json["src"])
        except:
            return {"error": "failed to parse src"}, 400
    
    try:
        start_time = time.time()
        ret, sign, token, extra = library_manager.sign(cmd, seq, src)
        end_time = time.time()
    except Exception as e:
        print(f"call sign func failed: {e}")
        return {"error": "failed to call sign func"}, 400
    
    return {
        "value": {
            "sign": sign,
            "token": token,
            "extra": extra
        },
        "platform": "linux",
        "version": full_version,
        "debug": {
            "ret": ret,
            "time": int((end_time - start_time) * 1000)
        }
    }

@app.route("/appinfo", methods=["GET"])
@app.route("/s/appinfo", methods=["GET"])
@app.route("/sign/appinfo", methods=["GET"])
def get_appinfo():
    return app_info

def extract_strings(filename, min_length=4, encoding='utf-8'):
    try:
        with open(filename, 'rb') as file:
            data = file.read()
    except IOError as e:
        print(f"Error opening file: {e}")
        return
    
    strings = []
    current_string = []
    
    for byte in data:
        if 32 <= byte <= 126:
            current_string.append(chr(byte))
        else:
            if len(current_string) >= min_length:
                strings.append(''.join(current_string))
            current_string = []
    
    if len(current_string) >= min_length:
        strings.append(''.join(current_string))
    
    return strings

def load_config():
    with open("config.json", "r") as f:
        conf = json.loads(f.read())
        return conf.get("ip", "0.0.0.0"), conf.get("port", 20392), conf.get("version", None), conf.get("offset", 0), conf.get("app_info", "")

def save_config(ip="0.0.0.0", port=29392, version=None, offset=0, app_info=""):
    with open("config.json", "w") as f:
        f.write(json.dumps({"ip": ip, "port": port, "version": version, "offset": offset, "app_info": app_info}))

def main():
    global app_info, version, full_version
    ip = "0.0.0.0"
    port = 29392
    offset = 0
    if not os.path.isfile("config.json"):
        save_config()
    else:
        ip, port, version, offset, app_info = load_config()
    
    print("check update")
    linux_cfg_js = requests.get("https://cdn-go.cn/qq-web/im.qq.com_new/latest/rainbow/linuxConfig.js").text
    params_pattern = r'var params=\s*({.*?});'
    params_match = re.search(params_pattern, linux_cfg_js, re.DOTALL)
    
    if not params_match:
        print("cannot resolve download link")
        return
    json_str = params_match.group(1)
    data = json.loads(json_str)
    
    net_version = data['version']
    deb_url = data['x64DownloadUrl']['deb']
    
    if not version:
        print("try update")
        if os.path.exists("./libs"):
            shutil.rmtree("./libs")
        os.mkdir("./libs")
        dl = Pypdl()
        if os.path.exists("./tmp"):
            shutil.rmtree("./tmp")
        os.mkdir("./tmp")
        dl.start(url=deb_url, file_path="./tmp/qq.deb")
        deb_f = open("./tmp/qq.deb", "rb")
        ara = Archive(deb_f)
        found_data = False
        data_file_path = ""
        print("extract data from deb... ", end="")
        for entry in ara:
            if not entry.name.startswith("data.tar"):
                continue
            with open("./tmp/" + entry.name, "wb") as f:
                f.write(ara.open(entry, "rb").read())
                found_data = True
                data_file_path = "./tmp/" + entry.name
                break
        deb_f.close()
        if not found_data:
            print("cannot find data in deb file, exit")
            return
        print("done\nextract file from data... ", end="")
        with tarfile.open(data_file_path, "r") as tar_f:
            tar_f.extractall("./tmp", filter="data")
        # then, try to find ./tmp/opt/QQ/resources/app/major.node
        if not os.path.exists("./tmp/opt/QQ/resources/app/major.node"):
            print("file seems to be wrong, exit.")
            return
        print("done")
        # copy to libs
        # shutil.copytree("./tmp/opt/QQ/resources/app/", "./libs", dirs_exist_ok=True)
        shutil.copy("./tmp/opt/QQ/resources/app/sharp-lib/libvips-cpp.so.42", "./libs/libvips-cpp.so.42")
        shutil.copy("./tmp/opt/QQ/resources/app/wrapper.node", "./libs/wrapper.node")
        shutil.copy("./tmp/opt/QQ/resources/app/package.json", "./libs/package.json")
        shutil.copy("./tmp/opt/QQ/resources/app/major.node", "./libs/major.node")
        shutil.rmtree("./tmp")
        # if os.path.exists("./libs/sharp-lib/libvips-cpp.so.42") and not os.path.exists("./libs/libvips-cpp.so.42"):
            # shutil.copy("./libs/sharp-lib/libvips-cpp.so.42", "./libs/libvips-cpp.so.42")
        # if os.path.exists("./libs/resource"):
            # shutil.rmtree("./libs/resource")
        print("extract libsymbols.so")
        with open("./libs/libsymbols.so", "wb") as sf:
            sf.write(utils.get_symbols())
        version = net_version
    
    if os.path.exists("./libs/major.node"):
        print("patch library")
        os.system(" ".join(["patchelf", "--remove-needed", "libbugly.so", "./libs/wrapper.node"]))
        pkg_json = {}
        with open("./libs/package.json", "r") as pkg_f:
            pkg_json = json.loads(pkg_f.read())
        print("version:", pkg_json["version"])
        sappid = 0
        print(f"try generate appinfo")
        str_pool = extract_strings("./libs/major.node")
        for st in str_pool:
            if st.strip().find("AppId/") != -1:
                sappid = int(st.strip().split("/")[-1])
        print("subappid:", sappid)
        app_info = json.dumps({
            "Os": "Linux",
            "Kernel": "Linux",
            "VendorOs": "linux",
            "CurrentVersion": pkg_json["version"],
            "MiscBitmap": 32764,
            "PtVersion": "2.0.0",
            "SsoVersion": 19,
            "PackageName": "com.tencent.qq",
            "WtLoginSdk": "nt.wtlogin.0.0.1",
            "AppId": 1600001615,
            "SubAppId": sappid,
            "AppIdQrCode": sappid,
            "AppClientVersion": int(pkg_json["buildVersion"]),
            "MainSigMap": 169742560,
            "SubSigMap": 0,
            "NTLoginType": 1,
        })
        offset = int(offset_fucker.analyze_node_file_optimized("./libs/wrapper.node"), 16)
        save_config(ip, port, version, offset, app_info)
        print("clean up")
        os.remove("./libs/major.node")
        
    print("init server...")
    os.chdir("./libs")
    with open("./package.json", "r") as pkg_f:
        pkg_json = json.loads(pkg_f.read())
        full_version = pkg_json['version']
    library_manager.preload_libraries()
    if not library_manager.load_module_and_function("./wrapper.node", offset):
        print("failed to load module, exit")
        return
    os.chdir("../")
    
    print("launching http listener...")
    app.run(host=ip, port=port)

if __name__ == "__main__":
    main()