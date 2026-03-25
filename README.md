# Weather-Query-System
This is a weather web for PM Accelerator Technical Assessment.

---


### How to use it

1.clone the project to your local.
```bash

git clone https://github.com/Vapor34/Weather-Query-System.git
```


2.Open it in PyCharm and create a virtual environment. 
Download relative python packages
```bash
pip install -r requirements.txt
```
3.In app/ai.py, you will find code like this:
```commandline
W_API_KEY = "create you own API key: https://openweathermap.org/"
LLM_API_KEY = "create you own API key: https://console.groq.com"
MW_API_KEY = "create you own API key: https://openweathermap.org/"
```
Get you own API key and fill in the quote. 

4.Create a database
```bash
flask shell
```

In flask shell:
```bash
from app import db
db.create_all()
exit()
```

Back to terminal
```bash
flask run
```

Finally, open the url and you'll get there.

---

### Functionalities
- User Authenticaiton System
  - Check if the username is unique and password is valid.
- Check current weather in a particular area, or check weather in a period of time. Record data into the database according to the input.
  - Input ambiguous text to find results, such as Zip Code/Postal Code, GPS Coordinates,
Landmarks, Town, City, etc. 
  - An input error message will come out if the input is invalid, or the place cannot be found.
- Manage users' own produced data
  - users can change minimum temp/maximum temp/wind speed/cloudiness/status value of a certain data
  - users can delete any data they created.
- Examine all the data whoever created.
- Export json file containing all the query data.
- Handle all kinds of errors.
  - When location is not found.
  - When API encounters some problems.
  - When user's date input is wrong.
- API Usage
  - Groq API to convert various user input into coordinates of that place.
  - OpenWeather API to fetch weather info.