#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日天气早报 - 推送到微信 (Server酱 / ServerChan)
数据源: Open-Meteo (免 API Key)
内容: 当前天气 + 未来24小时 + 穿衣指数 + 餐饮指数 (表格形式)

环境变量:
  CITY                 城市名(默认: 郑州)
  SERVERCHAN_SENDKEY  Server酱 SendKey(留空则只生成本地预览)
"""
import os
import sys
import datetime
import requests

# ---------------- 配置 ----------------
CITY = os.environ.get("CITY") or "郑州"        # 空值也回退默认城市
SENDKEY = os.environ.get("SERVERCHAN_SENDKEY", "")

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FC_URL = "https://api.open-meteo.com/v1/forecast"

# WMO 天气代码 -> 中文
WMO = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "毛毛雨(弱)", 53: "毛毛雨(中)", 55: "毛毛雨(强)",
    56: "冻雨(弱)", 57: "冻雨(强)",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨(弱)", 67: "冻雨(强)",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨(弱)", 81: "阵雨(中)", 82: "阵雨(强)",
    85: "阵雪(弱)", 86: "阵雪(强)",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷暴冰雹",
}


def wmo_text(code):
    try:
        return WMO.get(int(code), f"天气{code}")
    except (ValueError, TypeError):
        return f"天气{code}"


def geocode(city):
    """城市名 -> (纬度, 经度, 时区)"""
    r = requests.get(GEO_URL, params={
        "name": city, "count": 1, "language": "zh", "format": "json"
    }, timeout=15)
    r.raise_for_status()
    data = r.json()
    if "results" not in data or not data["results"]:
        raise ValueError(f"找不到城市: {city}")
    res = data["results"][0]
    return (res["latitude"], res["longitude"], res.get("timezone", "Asia/Shanghai"))


def fetch_forecast(lat, lon, tz):
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "forecast_days": 2,
        "timezone": tz,
    }
    r = requests.get(FC_URL, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def clothing_index(temp, has_rain):
    """根据气温(及是否降雨)给出穿衣指数"""
    if temp <= 0:
        level, advice = "严寒", "气温极低，务必穿羽绒服、厚棉衣、保暖内衣，注意防冻"
    elif temp <= 5:
        level, advice = "寒冷", "建议棉衣、毛衣、厚外套，注意保暖"
    elif temp <= 10:
        level, advice = "较冷", "建议大衣或厚夹克、针织衫"
    elif temp <= 15:
        level, advice = "凉爽", "建议夹克、风衣或薄毛衣"
    elif temp <= 20:
        level, advice = "舒适", "薄外套、长袖衬衫即可"
    elif temp <= 25:
        level, advice = "温暖", "单衣、短袖，早晚可加薄外套"
    elif temp <= 30:
        level, advice = "炎热", "短袖、短裤等清凉夏装，注意防晒"
    else:
        level, advice = "酷热", "尽量穿宽松透气衣物，避免中暑"
    if has_rain:
        advice += "；今日有降雨，建议携带雨具"
    return level, advice


def dining_index(temp, has_rain):
    """根据气温(及是否降雨)给出餐饮指数"""
    if temp <= 5:
        return "暖身", "天气寒冷，宜热汤、火锅、姜茶等暖身饮食"
    if temp <= 15:
        return "温补", "气温偏低，适合温补类菜肴与热饮"
    if temp >= 30:
        return "清淡", "天气炎热，宜清淡饮食、凉拌菜，多补水"
    if has_rain:
        return "暖胃", "有降雨，适合热汤面、粥类等暖胃食物"
    return "均衡", "气温舒适，正常均衡饮食即可"


def is_precip(code):
    w = wmo_text(code)
    return ("雨" in w) or ("雪" in w) or ("雷" in w)


def build_message(city, fc):
    now_local = fc["current"]["time"]            # "2026-08-22T06:00"
    now_hour = now_local[:13] + ":00"
    now_dt = datetime.datetime.strptime(now_local, "%Y-%m-%dT%H:%M")
    week = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now_dt.weekday()]

    cur = fc["current"]
    cur_wmo = wmo_text(cur["weather_code"])
    cur_temp = round(cur["temperature_2m"])
    cur_app = round(cur["apparent_temperature"])
    cur_hum = cur["relative_humidity_2m"]
    cur_wind = round(cur["wind_speed_10m"])

    # 未来24小时
    hourly = fc["hourly"]
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    pops = hourly["precipitation_probability"]
    codes = hourly["weather_code"]

    start = next((i for i, t in enumerate(times) if t >= now_hour), 0)
    end = min(start + 24, len(times))
    rows = []
    has_rain = False
    for i in range(start, end):
        if is_precip(codes[i]):
            has_rain = True
        if (i - start) % 3 == 0:                  # 每3小时取一行
            hh = times[i][11:16]
            w = wmo_text(codes[i])
            tp = round(temps[i])
            pop = pops[i] if pops[i] is not None else 0
            rows.append((hh, w, tp, pop))
    min24 = round(min(temps[start:end]))
    max24 = round(max(temps[start:end]))

    c_level, c_advice = clothing_index(cur_temp, has_rain)
    d_level, d_advice = dining_index(cur_temp, has_rain)

    L = []
    L.append(f"# 🌤️ {city} 今日天气早报")
    L.append(f"📅 {now_dt.strftime('%Y-%m-%d')} {week}　🌡️ 24h {min24}~{max24}°C")
    L.append("")
    L.append("## 当前天气")
    L.append("| 项目 | 数值 |")
    L.append("| --- | --- |")
    L.append(f"| 天气 | {cur_wmo} |")
    L.append(f"| 气温 | {cur_temp}°C |")
    L.append(f"| 体感温度 | {cur_app}°C |")
    L.append(f"| 相对湿度 | {cur_hum}% |")
    L.append(f"| 风速 | {cur_wind} km/h |")
    L.append(f"| 更新时间 | {now_dt.strftime('%Y-%m-%d %H:%M')} |")
    L.append("")
    L.append("## 未来24小时")
    L.append("| 时间 | 天气 | 气温 | 降水概率 |")
    L.append("| --- | --- | --- | --- |")
    for hh, w, tp, pop in rows:
        L.append(f"| {hh} | {w} | {tp}°C | {pop}% |")
    L.append("")
    L.append("## 生活指数")
    L.append("| 指数 | 等级 | 建议 |")
    L.append("| --- | --- | --- |")
    L.append(f"| 穿衣指数 | {c_level} | {c_advice} |")
    L.append(f"| 餐饮指数 | {d_level} | {d_advice} |")
    L.append("")
    L.append("> 数据来源: Open-Meteo · 穿衣/餐饮指数由脚本根据温湿度自动计算")
    return "\n".join(L)


def push_serverchan(sendkey, title, content):
    # Server酱 Turbo: SendKey 放在 URL 路径里, 不是参数
    url = f"https://sctapi.ftqq.com/{sendkey}.send"
    r = requests.post(url, data={"title": title, "desp": content}, timeout=15)
    return r.status_code, r.text


def main():
    if not SENDKEY:
        print("⚠️ 未设置 SERVERCHAN_SENDKEY，仅生成本地预览（不推送）。\n")
    try:
        lat, lon, tz = geocode(CITY)
        fc = fetch_forecast(lat, lon, tz)
        msg = build_message(CITY, fc)
    except Exception as e:
        print("获取天气失败:", e)
        sys.exit(1)

    title = f"🌤️ {CITY} 天气早报 {datetime.datetime.now().strftime('%m-%d')}"
    print(msg)

    if SENDKEY:
        code, resp = push_serverchan(SENDKEY, title, msg)
        print(f"\n推送结果: HTTP {code} {resp}")
        if code != 200:
            sys.exit(2)


if __name__ == "__main__":
    main()
