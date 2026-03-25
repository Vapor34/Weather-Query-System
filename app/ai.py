import requests
import re
from urllib.parse import quote
import json
from groq import Groq
import logging
from datetime import datetime, timedelta

# 在文件开头配置日志（可选，便于调试）
logging.basicConfig(level=logging.INFO)

W_API_KEY = "7195d26d5cd2c53c4c9405470f02d32e"
LLM_API_KEY = "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"
MW_API_KEY = "270bdac40b9a7c78f2781395aaef907b"
def get_weather(loc_data):
    # OpenWeatherMap 的地理编码 API（将城市名转为经纬度）
    weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={loc_data['lat']}&lon={loc_data['lon']}&appid={W_API_KEY}&units=metric"

    try:

        w_result = requests.get(weather_url).json()

        return {
            "address": w_result['name'],
            "temp": w_result['main']['temp'],
            "min_temp": w_result['main']['temp_min'],
            "max_temp": w_result['main']['temp_max'],
            "desc": w_result['weather'][0]['description'],
            "humidity": w_result['main']['humidity'],
            "wind_speed": w_result['wind']['speed'],
            "clouds": w_result['clouds']['all'],
            "lat": loc_data['lat'],
            "lon": loc_data['lon']
        }, None

    except Exception as e:
        return None, f"API request failed: {str(e)}"  # 符合错误处理要求


def resolve_location(location_input):
    """
    使用 LLM 智能解析用户意图，并结合 OpenWeather 进行坐标转换
    """
    try:
        client = Groq(api_key=LLM_API_KEY)
        clean_input = location_input.strip()

        system_prompt = (
            "You are a geography expert. Honestly judge the user input. Convert user input (landmarks, city names, postcodes, abbreviations) "
            "into the exact geographic coordinates (latitude and longitude) of that place if the input text is valid. "
            "Return ONLY a dictionary format with the keys \"lat\" and \"lon\" as float values and DO NOT include any other text or explanation."
            "But if you cannot find the place regarding the user input, return messages that tells the user the place doesn't exist."
        )


        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": location_input}
            ]
        )

        llm_res = completion.choices[0].message.content
        print("Raw AI response:", llm_res)


        if 'lat' in llm_res and 'lon' in llm_res:
            loc_data = json.loads(llm_res)
            print(f"Success! Lat: {loc_data['lat']}, Lon: {loc_data['lon']}")
            return loc_data
        else:
            raise ValueError("Cannot find such a place.")


    except Exception as e:
        print(f"LLM Parsing failed: {e}")
        # 降级处理：如果 AI 失败，设为默认值或返回错误信息，引导用户重新输入


def get_historical_weather(lat, lon, target_date):
    """
    获取指定日期正午12点的历史天气数据
    :param lat: 纬度
    :param lon: 经度
    :param target_date: datetime.date 对象
    :return: (weather_info_dict, error_message) 元组
    """
    # 将 target_date 的 12:00:00 UTC 转换为 Unix 时间戳
    dt = datetime(target_date.year, target_date.month, target_date.day, 12, 0, 0)
    start_ts = int(dt.timestamp())

    # 构建 API 请求 URL (使用 cnt=1 只获取这一小时的数据)
    url = "https://history.openweathermap.org/data/2.5/history/city"
    params = {
        'lat': lat,
        'lon': lon,
        'type': 'hour',
        'start': start_ts,
        'cnt': 1,               # 只返回一条记录（即正午12点）
        'units': 'metric',      # 使用摄氏度，与当前天气一致
        'appid': MW_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get('cod') != "200":
            return None, f"API error: {data.get('message', 'unknown error')}"

        hourly_list = data.get('list', [])
        if not hourly_list:
            return None, f"No data for {target_date} 12:00"

        # 取第一条（也是唯一一条）数据
        hour_data = hourly_list[0]
        main = hour_data.get('main', {})
        wind = hour_data.get('wind', {})
        clouds = hour_data.get('clouds', {})

        temp = main.get('temp')
        if temp is None:
            return None, f"No temperature data for {target_date} 12:00"

        # 构造返回格式（与当前天气保持一致）
        weather_info = {
            'temp': temp,
            'min_temp': temp,                # 历史单点数据，min/max 都使用该温度
            'max_temp': temp,
            'desc': 'Historical data (12:00 UTC)',
            'humidity': main.get('humidity'),
            'wind_speed': wind.get('speed'),
            'clouds': clouds.get('all'),
            'address': None,
            'date': target_date
        }
        print("Successfully return historical value!")
        return weather_info, None

    except requests.exceptions.RequestException as e:
        logging.error(f"History API request failed: {e}")
        return None, f"Network request failed: {str(e)}"
    except Exception as e:
        logging.error(f"Error processing historical data: {e}")
        return None, f"Data processing failed: {str(e)}"