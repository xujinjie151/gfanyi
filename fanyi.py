import requests
import re
import execjs
import json
import logging
import html
import time


js = '''
    function b(a, b) {
        for (var d = 0; d < b.length - 2; d += 3) {
            var c = b.charAt(d + 2),
                c = "a" <= c ? c.charCodeAt(0) - 87 : Number(c),
                c = "+" == b.charAt(d + 1) ? a >>> c : a << c;
            a = "+" == b.charAt(d) ? a + c & 4294967295 : a ^ c
        }
        return a
    }
    function tk(a,TKK) {
        for (var e = TKK.split("."), h = Number(e[0]) || 0, g = [], d = 0, f = 0; f < a.length; f++) {
            var c = a.charCodeAt(f);
            128 > c ? g[d++] = c : (2048 > c ? g[d++] = c >> 6 | 192 : (55296 == (c & 64512) && f + 1 < a.length && 56320 == (a.charCodeAt(f + 1) & 64512) ? (c = 65536 + ((c & 1023) << 10) + (a.charCodeAt(++f) & 1023), g[d++] = c >> 18 | 240, g[d++] = c >> 12 & 63 | 128) : g[d++] = c >> 12 | 224, g[d++] = c >> 6 & 63 | 128), g[d++] = c & 63 | 128)
        }
        a = h;
        for (d = 0; d < g.length; d++) a += g[d], a = b(a, "+-a^+6");
        a = b(a, "+-3^+b+-f");
        a ^= Number(e[1]) || 0;
        0 > a && (a = (a & 2147483647) + 2147483648);
        a %= 1E6;
        return a.toString() + "." + (a ^ h)
    }
    '''
tk_calculator = execjs.compile(js)  # use to compute the token for translating request


def get_TKK(get_proxies_fun=None):
    '''
    to get a value for calculating the token for constructing translating request
    :return: TKK
    '''
    url = "https://translate.google.cn"
    logging.warning("start getting tkk...")

    if get_proxies_fun:
        px = get_proxies_fun()
        res = requests.get(url,proxies=px)
    else:
        res = requests.get(url)

    TKK = re.search("tkk:'(.*?)'", res.text).group(1)
    return TKK


def trans_req(ori_text, sl="auto", tl="en", get_proxies_fun=None):
    '''
    construct translating request
    :param ori_text:
    :param sl:
    :param tl:
    :return:
    '''
    ori_text = html.unescape(ori_text)  # unescape the html
    res = None

    while True:
        try:
            tk = tk_calculator.call("tk", ori_text, get_TKK(get_proxies_fun))

            url_trans = "https://translate.google.cn/translate_a/single"

            payload = {
                "client": "t",
                "sl": sl,
                "tl": tl,
                "dt": "t",
                "ie": "UTF-8",
                "oe": "UTF-8",
                "otf": "1",
                "ssel": "0",
                "tsel": "0",
                "kc": "1",
                "tk": tk,
                "q": ori_text,
            }

            # res = req_t_death("POST", url_trans, payload)
            if get_proxies_fun:
                px = get_proxies_fun()
                res = requests.post(url_trans, data=payload,proxies=px)
            else:
                res = requests.post(url_trans, data=payload)
        except Exception as e:
            logging.warning(e)
            logging.warning("error, waiting and try again...")
            # logging.warning("text: %s " % ori_text)
            time.sleep(1)
            continue

        if res.status_code == 200:
            break

    js = None
    try:
        js = json.loads(res.text)
    except Exception as e:
        logging.warning(e)
        return []

    return js


def get_language_type(ori_text, get_proxies_fun=None):
    '''
    identify which language it is
    :param ori_text:
    :return:
    '''
    info = ori_text[:30] if len(ori_text) > 30 else ori_text
    logging.warning("start identifying: {}...".format(info))
    js = trans_req(ori_text, get_proxies_fun)
    return js[2]


def trans(ori_text, sl="auto", tl="en", get_proxies_fun=None):
    """
    translate text of which the length is less than 5000
    :param ori_text:
    :param sl:
    :param tl:
    :return:
    """
    info = ori_text[:30] if len(ori_text) > 30 else ori_text
    logging.warning("start translating: {}...".format(info))

    js = trans_req(ori_text, sl, tl, get_proxies_fun)
    trans_text = ""
    if js[2] == "en":
        trans_text = js[0][0][0]
    else:
        for pas in js[0]:
            trans_text += pas[0]

    return trans_text


def trans_long(ori_text, sl="auto", tl="en", get_proxies_fun=None):
    '''
    split the long text into pieces and translate
    :param ori_text: text whose len > 5000
    :param sl: source language
    :param tl: target language
    :return:
    '''
    stop_char = ["。", ".", ]
    start_flag = 0
    split_marks = []

    pointor = start_flag + 5000 + 1

    while True:
        while ori_text[pointor] not in stop_char:
            pointor -= 1
        split_marks.append(pointor)
        pointor += 5000
        if pointor >= len(ori_text):
            break

    snippets = []
    start_flag = 0
    for m in split_marks:
        snippets.append(ori_text[start_flag:(m + 1)])
        start_flag = m + 1

    if split_marks[-1] != len(ori_text) - 1:
        snippets.append(ori_text[start_flag:len(ori_text)])

    if get_language_type(snippets[0]) == tl:
        return ori_text

    en_text = ""
    for sni in snippets:
        en_text += trans(sni, sl, tl, get_proxies_fun)

    return en_text


if __name__ == "__main__":
    # 无忧免费代理
    def get_proxy():
        proxy_str = requests.get(
            "http://api.ip.data5u.com/dynamic/get.html?order=53b3de376027aa3f699dc335d2bc0674&sep=3").text.strip()
        proxies = {"http": "http://%s" % proxy_str,
                   "https": "http://%s" % proxy_str, }
        return proxies

    # 自定义代理
    def get_proxy_2():
        # 代理服务器
        proxyHost = "http-dyn.abuyun.com"
        proxyPort = "9020"

        # 代理隧道验证信息
        proxyUser = "*"
        proxyPass = "*"

        proxyMeta = "http://%(user)s:%(pass)s@%(host)s:%(port)s" % {
            "host": proxyHost,
            "port": proxyPort,
            "user": proxyUser,
            "pass": proxyPass,
        }

        proxies = {
            "http": proxyMeta,
            "https": proxyMeta,
        }
        return proxies

    res = trans("python", tl='zh-CN')
    print(res)
