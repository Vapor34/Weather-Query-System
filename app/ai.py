import requests
import re
from urllib.parse import quote
import json
from groq import Groq
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

W_API_KEY = "create you own API key: https://openweathermap.org/"
LLM_API_KEY = "create you own API key: https://console.groq.com"
MW_API_KEY = "create you own API key: https://openweathermap.org/"
def get_weather(loc_data):
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
        return None, f"API request failed: {str(e)}"


def resolve_location(location_input):

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

def get_historical_weather(lat, lon, target_date):

    dt = datetime(target_date.year, target_date.month, target_date.day, 12, 0, 0)
    start_ts = int(dt.timestamp())

    url = "https://history.openweathermap.org/data/2.5/history/city"
    params = {
        'lat': lat,
        'lon': lon,
        'type': 'hour',
        'start': start_ts,
        'cnt': 1,
        'units': 'metric',
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

        hour_data = hourly_list[0]
        main = hour_data.get('main', {})
        wind = hour_data.get('wind', {})
        clouds = hour_data.get('clouds', {})

        temp = main.get('temp')
        if temp is None:
            return None, f"No temperature data for {target_date} 12:00"

        weather_info = {
            'temp': temp,
            'min_temp': temp,
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