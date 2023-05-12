import datetime as dt
import json
import os
import pickle
import requests
import pandas as pd
from PIL import Image
from flask import Flask, render_template, session, redirect, url_for, flash, jsonify, request
from flask_login import logout_user, LoginManager, login_user, login_required, UserMixin, current_user
from werkzeug.utils import secure_filename

from database import link_sql, check_user_exist
from search import generate_sql_query

with open('setting.json', 'r') as f:
    settings = json.load(f)

app = Flask(__name__, template_folder='./templates')

app.secret_key = settings['AppSecretKey']
app.config['UPLOAD_POST_IMAGE_FOLDER'] = "static/images/post/"

login_manager = LoginManager()
login_manager.init_app(app)

GOOGLE_API_KEY = settings['GoogleApiKey']
OPENAI_API_KEY = settings['OpenAIKey']


class User(UserMixin):
    def __init__(self, user_id, email, permission):
        self.id = user_id
        self.email = email
        self.permission = permission

    def __repr__(self):
        return f'<User {self.email}>'

    def get_id(self):
        return self.id


def handle_datetime(obj):
    if isinstance(obj, dt.datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    else:
        raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


# 使用正則表達式找出字串中的所有時間
def time_diff_string(input_datetime):
    if input_datetime is None:
        return None
    time_diff = dt.datetime.now() - input_datetime
    if time_diff < dt.timedelta(hours=1):
        minutes = int(time_diff.total_seconds() / 60)
        result_str = str(minutes) + ' 分鐘前'
    elif time_diff < dt.timedelta(days=1):
        # 不足1天，顯示小時前
        hours = int(time_diff.total_seconds() / 3600)
        result_str = str(hours) + ' 小時前'
    else:
        # 超過1天，顯示天前
        days = int(time_diff.total_seconds() / 86400)
        result_str = str(days) + ' 天前'
    return result_str


def get_post_data(sql):
    db, cursor = link_sql()
    cursor.execute(sql)
    results = cursor.fetchall()

    db.close()

    for post in results:
        post["reviseDateTime"] = time_diff_string(post["reviseDateTime"])

    return results


def get_dataframe(location, attr, year):
    df = pd.read_csv(location)
    df = df[attr]
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] > dt.datetime(int(year), 1, 1)]

    df['year'] = df['date'].astype(str).str[0:4]
    df['month'] = df['date'].astype(str).str[5:7]
    df['city'] = df['address'].astype(str).str[0:3]

    df = df.drop(['date', 'address'], axis=1)

    return df


def get_coordination(address):
    # 要轉換的地址

    # Google Maps API的網址
    url = 'https://maps.googleapis.com/maps/api/geocode/json'

    # 請求參數
    params = {'address': address, 'key': GOOGLE_API_KEY}

    # 發送請求
    response = requests.get(url, params=params)

    # 解析JSON數據
    result = response.json()

    # 獲取經緯度
    location = result['results'][0]['geometry']['location']
    latitude = location['lat']
    longitude = location['lng']

    return (latitude, longitude)


def predict_sell_price(data):
    columns = ['year', 'month', 'total_seconds', 'latitude', 'longitude',
                'floor','twPing','bedRoom', 'livingRoom', 'restRoom',
                'balcony', 'age', 'city_南投縣', 'city_嘉義市', 'city_嘉義縣',
                'city_基隆市', 'city_宜蘭縣', 'city_屏東縣', 'city_彰化縣', 'city_新北市', 
                'city_新竹市', 'city_新竹縣', 'city_桃園市', 'city_澎湖縣', 'city_臺中市', 
                'city_臺北市', 'city_臺南市', 'city_臺東縣', 'city_花蓮縣', 'city_苗栗縣',
                'city_金門縣', 'city_雲林縣', 'city_高雄市', 'houseType_公寓', 'houseType_華廈',
                'houseType_透天', 'houseType_電梯大樓']
    df = pd.DataFrame(data,columns = columns)

    with open('./pricePredictor/sell.pkl', 'rb') as f:
        model = pickle.load(f)
    predictions = model.predict(df)
    return predictions

def predict_rent_price(data):
    columns = ['year', 'month', 'total_seconds', 'latitude', 'longitude', 
               'floor', 'twPing', 'bedRoom', 'livingRoom', 'restRoom', 
               'parkingSpace', 'elevator', 'funiture', 'city_南投縣', 
               'city_嘉義市', 'city_嘉義縣', 'city_基隆市', 'city_宜蘭縣', 
               'city_屏東縣', 'city_彰化縣', 'city_新北市', 'city_新竹市', 
               'city_新竹縣', 'city_桃園市', 'city_臺中市', 'city_臺北市', 
               'city_臺南市', 'city_花蓮縣', 'city_苗栗縣', 'city_雲林縣', 
               'city_高雄市', 'type_住宅', 'type_套房']
    df = pd.DataFrame(data,columns=columns)
    
    with open('./pricePredictor/rent.pkl', 'rb') as f:
        model = pickle.load(f)
    predictions = model.predict(df)
    return predictions

@login_manager.user_loader
def load_user(user_id):
    db, cursor = link_sql()

    cursor.execute(f"SELECT * FROM `user` WHERE `uId` = {user_id}")
    user = cursor.fetchone()
    cursor.close()
    db.close()

    if not user:
        return None

    user = User(user['uId'], user['email'], user['permission'])
    return user


@app.route('/')
@app.route('/home')
def index():
    selected_region = session.get('selected_region', '台北市')
    db, cursor = link_sql()

    results = {}

    # For recommend.html
    sql = f"SELECT `pId`, `address`, `district`, " \
          f"       `type`, `twPing`, `image`," \
          f"       `housesell`.`price` as `sellPrice`, " \
          f"       `houserent`.`price` as `rentPrice` " \
          f"FROM `post` " \
          f"NATURAL JOIN `payment` " \
          f"NATURAL JOIN `house` " \
          f"NATURAL JOIN `image` " \
          f"LEFT OUTER JOIN `housesell` " \
          f"             ON `house`.`hId` = `housesell`.`hid`" \
          f"LEFT OUTER JOIN `houserent` " \
          f"             ON `house`.`hId` = `houserent`.`hid`" \
          f"WHERE `city` = '{selected_region}' " \
          f"ORDER BY `class` DESC " \
          f"LIMIT 8 "

    cursor.execute(sql)

    results[0] = cursor.fetchall()

    # For family.html
    sql = f"SELECT `pId`, `address`, `district`, " \
          f"       `type`, `twPing`, `image`," \
          f"       `housesell`.`price` as `sellPrice` " \
          f"FROM `post` " \
          f"NATURAL JOIN `payment` " \
          f"NATURAL JOIN `house` " \
          f"NATURAL JOIN `image` " \
          f"NATURAL JOIN `housesell` " \
          f"WHERE `city` = '{selected_region}' " \
          f"ORDER BY `class` DESC " \
          f"LIMIT 8 "

    cursor.execute(sql)

    results[1] = cursor.fetchall()

    # For suite.html
    sql = f"SELECT `pId`, `address`, `district`, " \
          f"       `type`, `twPing`, `image`," \
          f"       `houserent`.`price` as `rentPrice` " \
          f"FROM `post` " \
          f"NATURAL JOIN `payment` " \
          f"NATURAL JOIN `house` " \
          f"NATURAL JOIN `image` " \
          f"NATURAL JOIN `houserent` " \
          f"WHERE `city` = '{selected_region}' AND" \
          f"      `type` = '獨立套房'" \
          f"ORDER BY `class` DESC " \
          f"LIMIT 8 "

    cursor.execute(sql)

    results[2] = cursor.fetchall()

    # For suite.html
    sql = f"SELECT `pId`, `address`, `district`, " \
          f"       `type`, `twPing`, `image`," \
          f"       `houserent`.`price` as `rentPrice` " \
          f"FROM `post` " \
          f"NATURAL JOIN `payment` " \
          f"NATURAL JOIN `house` " \
          f"NATURAL JOIN `image` " \
          f"NATURAL JOIN `houserent` " \
          f"WHERE `city` = '{selected_region}' AND" \
          f"      `type` IN ('分租套房', '雅房')" \
          f"ORDER BY `class` DESC " \
          f"LIMIT 8 "

    cursor.execute(sql)

    results[3] = cursor.fetchall()

    sql = "SELECT pId FROM houseSell,house WHERE house.hId = housesell.hId"
    cursor.execute(sql)
    temp_results4 = cursor.fetchall()
    results4 = []
    for result in temp_results4:
        results4.append(result["pId"])

    results[4] = results4
    db.close()

    return render_template(
        'index.html',
        selected_region=selected_region,
        recommend_post=results[0],
        family_post=results[1],
        suite_post=results[2],
        shared_post=results[3],
        sell_post_list=results[4]
    )


@app.route('/sell.html')
def sell():
    selected_region = session.get('selected_region', '台北市')
    selected_pattern = session.get('selected_pattern', '>=0')
    selected_house_type = session.get('selected_houseType', "All")
    selected_price = session.get('selected_price', ">=0")
    selected_tw_ping = session.get('selected_twPing', ">=0")
    selected_age = session.get('selected_age', ">=0")
    selected_my_post = session.get('selected_myPost', "All")
    selected_order = session.get('selected_order', " ORDER BY PRICE DESC")
    u_id = current_user.get_id() if current_user.get_id() else 0

    sql = f"SELECT *FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
          f"INNER JOIN `image` ON image.pId = post.pId) " \
          f"INNER JOIN `housesell` ON house.hId = housesell.hId " \
          f"INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click " \
          f"FROM post LEFT OUTER JOIN `browses` ON browses.pId = post.pId" \
          f" GROUP BY post.pId) AS click  ON post.pId = click.pId " \
          f"WHERE `city` = '{selected_region}' AND type = '住宅' "

    house_type_sql = "" if str(selected_house_type) == "All" else f" AND `houseType` = '{selected_house_type}'"
    pattern_sql = f" AND `bedRoom` {selected_pattern}"
    price_sql = f" AND `price` {selected_price}"
    tw_ping_sql = f" AND `twPing` {selected_tw_ping}"
    age_sql = f" AND  `age` {selected_age}"

    if selected_my_post == "1":
        my_post_sql = f" AND `uId` = {u_id}"
    elif selected_my_post == "0":
        my_post_sql = f" AND `uId` != {u_id}"
    else:
        my_post_sql = ""

    sql = sql + house_type_sql + pattern_sql + price_sql + tw_ping_sql + age_sql + my_post_sql + selected_order
    results = get_post_data(sql)

    return render_template(
        'sell.html',
        selected_region=selected_region,
        post_results=results
    )


@app.route('/rentals.html')
def rentals():
    selected_region = session.get('selected_region', '台北市')
    selected_pattern = session.get('selected_pattern', '>=0')
    selected_type = session.get('selected_type', "All")
    selected_price = session.get('selected_price', ">=0")
    selected_tw_ping = session.get('selected_twPing', ">=0")
    selected_my_post = session.get('selected_myPost', "All")
    selected_order = session.get('selected_order', " ORDER BY PRICE DESC")
    u_id = current_user.get_id() if current_user.get_id() else 0

    if selected_my_post == "1":
        my_post_sql = f" AND `uId` = {u_id}"
    elif selected_my_post == "0":
        my_post_sql = f" AND `uId` != {u_id}"
    else:
        my_post_sql = ""

    sql = f"SELECT * " \
          f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
          f"INNER JOIN `image` ON image.pId = post.pId) " \
          f"INNER JOIN `houserent` ON house.hId = houserent.hId " \
          f"INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click " \
          f"FROM post " \
          f"LEFT OUTER JOIN browses ON browses.pId = post.pId " \
          f"GROUP BY post.pId) AS click  ON post.pId = click.pId " \
          f"WHERE `city` = '{selected_region}'"

    type_sql = "" if str(selected_type) == "All" else f" AND `type` = '{selected_type}'"
    pattern_sql = f" AND `bedRoom` {selected_pattern}"
    price_sql = f" AND `price` {selected_price}"
    tw_ping_sql = f" AND `twPing` {selected_tw_ping}"

    sql = sql + pattern_sql + price_sql + tw_ping_sql + type_sql + my_post_sql + selected_order
    results = get_post_data(sql)

    return render_template(
        'rentals.html',
        selected_region=selected_region,
        post_results=results
    )


@app.route('/my_post.html')
@login_required
def my_post():
    selected_u_id = current_user.get_id()

    rent_sql = f"SELECT * " \
               f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
               f"INNER JOIN `image` ON image.pId = post.pId) " \
               f"INNER JOIN `houserent` ON house.hId = houserent.hId " \
               f"INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click " \
               f"FROM post " \
               f"LEFT OUTER JOIN browses ON browses.pId = post.pId" \
               f" GROUP BY post.pId) AS click  ON post.pId = click.pId " \
               f"WHERE `uId` = {selected_u_id}"

    sell_sql = f"SELECT * " \
               f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
               f"INNER JOIN `image` ON image.pId = post.pId) " \
               f"INNER JOIN `housesell` ON house.hId = housesell.hId " \
               f"INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click " \
               f"FROM post " \
               f"LEFT OUTER JOIN browses ON browses.pId = post.pId" \
               f" GROUP BY post.pId) AS click  ON post.pId = click.pId " \
               f"WHERE `uId` = {selected_u_id}"
    rent_results = get_post_data(rent_sql)
    sell_results = get_post_data(sell_sql)

    return render_template(
        'my_post.html',
        post_rent_results=rent_results,
        post_sell_results=sell_results
    )


@app.route('/sell_info.html')
def sell_info():
    p_id = request.args.get('pId')
    u_id = current_user.get_id() if current_user.get_id() else 0

    db, cursor = link_sql()

    sql = f"SELECT house.*, post.*, image.*, housesell.* " \
          f"FROM ((`house` JOIN `post` ON house.pId = post.pId)" \
          f"JOIN `image` ON image.pId = post.pId)" \
          f"JOIN `housesell` ON house.hId = housesell.hId " \
          f"WHERE post.pId = {p_id} " \
          f"LIMIT 1"

    cursor.execute(sql)
    results = cursor.fetchone()
    db.close()

    sql = f"SELECT *FROM criticizes,(SELECT uId , name FROM user ) AS user " \
          f"where user.uId = criticizes.uId  AND pId = {p_id}"

    comment = get_post_data(sql)

    if u_id == results["uId"]:
        revise_permission = 1
    else:
        revise_permission = 0

    def sell_data(location, year):
        attr = ['date', 'address', 'pricePerTwPing', 'houseType']

        df = get_dataframe(location, attr, year)

        df = df[['year', 'month', 'city', 'pricePerTwPing', 'houseType']]
        df['pricePerTwPing'] = df['pricePerTwPing'] / 1000
        return df

    def data_sell_process(year: str, season: str):
        fetch_data = sell_data(f"./house_data/sell_{year}_{season}.csv", year)

        return fetch_data

    data_01 = data_sell_process("2022", "01")
    data_02 = data_sell_process("2022", "02")
    data_03 = data_sell_process("2022", "03")
    data_04 = data_sell_process("2022", "04")
    data_05 = data_sell_process("2023", "01")
    data_06 = data_sell_process("2023", "02")
    data = pd.concat([data_01, data_02, data_03, data_04, data_05, data_06], ignore_index=True)

    data = data.groupby(['year', 'month', 'city', 'houseType'])['pricePerTwPing'].agg(['mean', 'size']).reset_index()

    data = data[(data['city'] == results['city']) & (data['houseType'] == results['houseType'])]
    chart_data = data.to_json(orient='records')

    return render_template(
        'sell_info.html',
        pId=p_id,
        uId=u_id,
        revise_permission=revise_permission,
        criticizes=comment,
        postType="sell",
        post=results,
        chart_data=chart_data,
        google_api_key=GOOGLE_API_KEY
    )


@app.route('/rentals_info.html')
def rentals_info():
    p_id = request.args.get('pId')
    u_id = current_user.get_id() if current_user.get_id() else 0

    db, cursor = link_sql()

    sql = f"SELECT house.*, post.*, image.*, houserent.* " \
          f"FROM ((`house` JOIN `post` ON house.pId = post.pId)" \
          f"JOIN `image` ON image.pId = post.pId)" \
          f"JOIN `houserent` ON house.hId = houserent.hId " \
          f"WHERE post.pId = {request.args.get('pId')} " \
          f"LIMIT 1"

    cursor.execute(sql)
    results = cursor.fetchone()
    revise_permission = 1 if u_id == results["uId"] else 0

    db.close()

    sql = f"SELECT *FROM criticizes,(SELECT uId , name FROM user ) AS user " \
          f"where user.uId = criticizes.uId  AND pId = {p_id}"

    comment = get_post_data(sql)

    if results['type'] == '分租套房' or results['type'] == '獨立套房' or results['type'] == '雅房':
        results['type'] = '套房'

    def rent_data(location, year):
        attr = ['date', 'address', 'price', 'type']

        df = get_dataframe(location, attr, year)

        df = df[['year', 'month', 'city', 'price', 'type']]
        df['price'] = df['price'] / 100
        return df

    def data_rent_process(year: str, season: str):
        fetch_data = rent_data(f"./house_data/rent_{year}_{season}.csv", year)

        return fetch_data

    data_01 = data_rent_process("2022", "01")
    data_02 = data_rent_process("2022", "02")
    data_03 = data_rent_process("2022", "03")
    data_04 = data_rent_process("2022", "04")
    data_05 = data_rent_process("2023", "01")
    data_06 = data_rent_process("2023", "02")
    data = pd.concat([data_01, data_02, data_03, data_04, data_05, data_06], ignore_index=True)

    data = data.groupby(['year', 'month', 'city', 'type'])['price'].agg(['mean', 'size']).reset_index()
    data = data[(data['city'] == results['city']) & (data['type'] == results['type'])]

    chart_data = data.to_json(orient='records')

    return render_template(
        'rentals_info.html',
        pId=request.args.get('pId'),
        uId=u_id,
        postType="rent",
        revise_permission=revise_permission,
        criticizes=comment,
        post=results,
        chart_data=chart_data,
        google_api_key=GOOGLE_API_KEY
    )


@app.route('/upload_comment', methods=['POST', 'GET'])
@login_required
def add_comment():
    u_id = current_user.id
    p_id = request.form.get("pId")
    comment = request.form.get("comment")
    post_type = request.form.get("postType")
    now = dt.datetime.now()

    db, cursor = link_sql()
    cursor.execute("SELECT max(cId) AS final_cId FROM `criticizes`")
    final_c_id = cursor.fetchone()["final_cId"]
    if final_c_id is not None:
        c_id = final_c_id + 1
    else:
        c_id = 1
    sql = "INSERT INTO criticizes(cId,uId, pId, comment, reviseDateTime) VALUES (%s,%s, %s, %s, %s)"

    cursor.execute(sql, (c_id, u_id, p_id, comment, now))
    db.commit()
    db.close()
    flash('新增成功')
    if post_type == "sell":
        return redirect(f'sell_info.html?pId={p_id}')
    else:
        return redirect(f'rentals_info.html?pId={p_id}')


@app.route('/revise_comment', methods=['POST', 'GET'])
@login_required
def revise_comment():
    c_id = request.form.get("cId")
    p_id = request.form.get("pId")
    post_type = request.form.get("postType")
    comment = request.form.get("comment")
    now = dt.datetime.now()
    db, cursor = link_sql()
    sql = f"UPDATE criticizes SET comment = '{comment}', reviseDateTime = '{now}' " \
          f"WHERE cId = {c_id}"
    cursor.execute(sql)
    db.commit()
    db.close()
    flash('修改成功')
    if post_type == "sell":
        return redirect(f'sell_info.html?pId={p_id}')
    else:
        return redirect(f'rentals_info.html?pId={p_id}')


@app.route('/delete_comment', methods=['POST', 'GET'])
@login_required
def delete_comment():
    c_id = request.form.get("cId")
    p_id = request.form.get("pId")
    post_type = request.form.get("postType")
    db, cursor = link_sql()
    sql = f"DELETE FROM criticizes WHERE cId =  {c_id}"
    cursor.execute(sql)
    db.commit()
    db.close()
    flash('刪除成功')
    if post_type == "sell":
        return redirect(f'sell_info.html?pId={p_id}')
    else:
        return redirect(f'rentals_info.html?pId={p_id}')


@app.route('/add_post.html')
@login_required
def add_post():
    post_type = request.args.get('postType')

    return render_template(
        'add_post.html',
        postType=post_type)

@app.route('/predict', methods=['POST'])
@login_required
def predict_price():
    postType = request.form.get('post_type')
    address = request.form.get("address")
    
    coordination = get_coordination(address)
    data = request.form.get("predict_data")
    year = dt.datetime.now().year
    month = dt.datetime.now().month
    interval = dt.datetime.now() - dt.datetime(2020,1,1)
    total_seconds = interval.total_seconds()

    data = [[year,month,total_seconds]+list(coordination) +list(map(float, data.split(",")))]
    
    processed_data = predict_rent_price(data) if postType == "rent" else predict_sell_price(data)
    response = {'result': int(processed_data[0])}
    
    return jsonify(response)


@app.route('/upload_post', methods=['POST', 'GET'])
@login_required
def upload_post():
    u_id = current_user.get_id()

    db, cursor = link_sql()
    sql = f"SELECT `pId` from `post` ORDER BY `pId` DESC LIMIT 1"
    cursor.execute(sql)
    p_id = cursor.fetchone()["pId"] + 1
    sql = f"SELECT `hId` from `house` ORDER BY `hId` DESC LIMIT 1"
    cursor.execute(sql)
    h_id = cursor.fetchone()["hId"] + 1
    now = dt.datetime.now()

    def insert_data(entity, attrs, int_attrs=None, float_attrs=None, bool_attrs=None, now_attrs=None):
        if bool_attrs is None:
            bool_attrs = []
        if float_attrs is None:
            float_attrs = []
        if int_attrs is None:
            int_attrs = []
        if now_attrs is None:
            now_attrs = []
        result = []
        for attr in attrs:
            if attr == "pId":
                result.append(p_id)
            elif attr == "uId":
                result.append(u_id)
            elif attr == "hId":
                result.append(h_id)
            elif attr in int_attrs:
                result.append(int(request.form.get(attr)))
            elif attr in float_attrs:
                result.append(float(request.form.get(attr)))
            elif attr in bool_attrs:
                result.append(1) if request.form.get(attr) else result.append(0)
            elif attr in now_attrs:
                result.append(f'{now}')
            else:
                result.append(request.form.get(attr))

        fetch_sql = "INSERT INTO " + entity + str(attrs).replace("'", "`") + "VALUES" + str(tuple(result))
        cursor.execute(fetch_sql)
        db.commit()

    post = ('pId', 'uId', 'title', 'city', 'district', 'address', 'name', 'phone', 'description', 'reviseDateTime')
    insert_data('`post`', post, now_attrs=['reviseDateTime'])

    house = ('hId', 'type', 'twPing', 'floor', 'lived', 'bedRoom', 'livingRoom', 'restRoom', 'balcony', 'pId')
    insert_data('`house`', house, ['bedRoom', 'livingRoom', 'restRoom', 'balcony'], float_attrs=['twPing'],
                bool_attrs=['lived'])

    post_type = request.form.get("postType")

    if post_type == "sell":

        house_sell = ('hId', 'ratioOfPublicArea', 'pricePerTwPing', 'price', 'age', 'houseType', 'houseName')
        insert_data('`houseSell`', house_sell, int_attrs=['age'],
                    float_attrs=['ratioOfPublicArea', 'pricePerTwPing', 'price'])

    elif post_type == "rent":
        house_rent = ("hId", "price", "refrigerator", "washingMachine", "TV", "airConditioner",
                      "waterHeater", "bed", "closet", "paidTVChannel", "internet",
                      "gas", "sofa", "deskChair", "balcony", "elevator", "parkingSpace")

        house_rent_bool_attrs = ["refrigerator", "washingMachine", "TV", "airConditioner",
                                 "waterHeater", "bed", "closet", "paidTVChannel", "internet",
                                 "gas", "sofa", "deskChair", "balcony", "elevator", "parkingSpace"]
        insert_data('`houseRent`', house_rent, int_attrs=["price"], bool_attrs=house_rent_bool_attrs)

    image = request.files["image"]
    image_name = f"post{p_id}_" + secure_filename(image.filename)
    image_path = "../../static/images/post/" + image_name

    sql = f"INSERT INTO `Image`(`pId`,`image`) VALUES ({p_id},'{image_path}')"
    image.save(os.path.join(app.config['UPLOAD_POST_IMAGE_FOLDER'], image_name))
    cursor.execute(sql)
    db.commit()

    month = int(request.form.get("month"))
    pay_date = dt.date.today()
    end_date = pay_date + dt.timedelta(days=month * 30)
    pay_date = dt.date.strftime(pay_date, '%Y-%m-%d')
    end_date = dt.date.strftime(end_date, '%Y-%m-%d')

    pay_class = int(request.form.get("class"))
    exp_date = request.form.get("expDate")
    exp_year = int("20" + str(exp_date).split("/")[1])
    exp_month = int(str(exp_date).split("/")[0])
    exp_date = dt.date(exp_year, exp_month, 1)
    if pay_class == 1:
        cost = month * 300
    elif pay_class == 2:
        cost = month * 600
    else:
        cost = month * 1000
    card_number = request.form.get("cardNumber")

    payment = str(('pId', 'payDate', 'endDate', 'class', 'expDate', 'cardNumber', 'cost')).replace("'", "`")

    sql = f"INSERT INTO `Payment`{payment}" \
          f"VALUES ({p_id},'{pay_date}','{end_date}',{pay_class},'{exp_date}','{card_number}',{cost})"
    print(sql)
    cursor.execute(sql)
    db.commit()
    cursor.close()
    db.close()

    # 開啟圖片
    with Image.open("./static/images/post/" + image_name) as im:
        # 調整大小
        size = (600, 400)
        im_resized = im.resize(size)
        # 儲存圖片
        im_resized.save("./static/images/post/" + image_name)

    flash('貼文新增成功')
    return redirect(url_for('index'))


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')


@app.route('/search', methods=['GET', 'POST'])
def search():
    post_type = request.args.get('postType')
    post_results_str = request.args.get('post_results')
    if post_results_str:
        post_results = json.loads(post_results_str)
    else:
        post_results = []

    selected_region = session.get('selected_region', '台北市')

    return render_template(
        'search_results.html',
        postType=post_type,
        post_results=post_results,
        selected_region=selected_region
    )


@app.route('/search/advance', methods=['POST'])
def advance_search():
    search_type = request.form.get('searchType')
    query = request.form.get('query')
    selected_region = session.get('selected_region', '台北市')

    results = generate_sql_query(search_type, query, selected_region)

    return redirect(
        url_for(
            'search',
            postType=search_type,
            post_results=json.dumps(results, default=handle_datetime)
        )
    )


@app.route('/search/suggest')
def search_suggest():
    search_type = request.args.get('type')  # 獲取搜索類型
    query = request.args.get('query')  # 獲取搜索關鍵詞

    selected_region = session.get('selected_region', '台北市')

    db, cursor = link_sql()

    if search_type == 'rent':
        sql = "SELECT `pId`, `title`, `district`, `address` " \
              "FROM `post` " \
              "NATURAL JOIN `house` " \
              "NATURAL JOIN `houserent` " \
              "WHERE `city` = %s AND " \
              "(`address` LIKE %s OR " \
              "`district` LIKE %s OR " \
              "`title` LIKE %s)"
        query_values = (selected_region, f'%{query}%', f'%{query}%', f'%{query}%')
    else:
        sql = "SELECT `pId`, `title`, `district`, `address` " \
              "FROM `post` " \
              "NATURAL JOIN `house` " \
              "NATURAL JOIN `housesell` " \
              "WHERE `city` = %s AND " \
              "(`address` LIKE %s OR " \
              "`housename` LIKE %s OR " \
              "`district` LIKE %s OR " \
              "`title` LIKE %s)"
        query_values = (selected_region, f'%{query}%', f'%{query}%', f'%{query}%', f'%{query}%')

    cursor.execute(sql, query_values)
    results = cursor.fetchall()
    db.close()

    return jsonify(results)


@app.route('/revise_post', methods=['POST', 'GET'])
@login_required
def revise_post():
    db, cursor = link_sql()
    p_id = int(request.form.get("pId"))
    sql = f"SELECT `hId` from `house` where `pId` = {p_id}"
    cursor.execute(sql)
    db.close()

    h_id = cursor.fetchone()["hId"]
    now = dt.datetime.now()

    def update_data(entity, attrs, int_attrs=None, float_attrs=None, bool_attrs=None, now_attrs=None,
                    without_h_id=False):
        db_func, cursor_func = link_sql()

        if bool_attrs is None:
            bool_attrs = []
        if float_attrs is None:
            float_attrs = []
        if int_attrs is None:
            int_attrs = []
        if now_attrs is None:
            now_attrs = []
        set_sql = " SET "
        for attr in attrs:
            value = request.form.get(attr)
            if attr in ["pId", "uId", "hId"]:
                continue
            elif attr in bool_attrs:
                if attr == "balcony":
                    if int(value) > 0:
                        set_sql = set_sql + f"`{attr}` = 1, "
                    else:
                        set_sql = set_sql + f"`{attr}` = 0, "
                elif value:
                    set_sql = set_sql + f"`{attr}` = 1, "
                else:
                    set_sql = set_sql + f"`{attr}` = 0, "
            elif attr in now_attrs:
                set_sql = set_sql + f"`{attr}` = '{now}', "
            elif not value:
                continue
            elif attr in int_attrs:
                set_sql = set_sql + f"`{attr}` = {int(value)}, "
            elif attr in float_attrs:
                set_sql = set_sql + f"`{attr}` = {float(value)}, "
            else:

                set_sql = set_sql + f"`{attr}` = '{value}', "
        if without_h_id:
            fetch_sql = "UPDATE " + entity + set_sql[:-2] + f" where `pId` = {p_id}"
        else:
            fetch_sql = "UPDATE " + entity + set_sql[:-2] + f" where `hId` = {h_id}"

        print(fetch_sql)
        cursor_func.execute(fetch_sql)
        db_func.commit()
        db_func.close()

    post = ('pId', 'uId', 'title', 'city', 'district', 'address', 'name', 'phone', 'description', 'reviseDateTime')
    update_data('`post`', post, without_h_id=True, now_attrs=['reviseDateTime'])

    house = ('hId', 'type', 'twPing', 'floor', 'lived', 'bedRoom', 'livingRoom', 'restRoom', 'balcony', 'pId')
    update_data('`house`', house, ['bedRoom', 'livingRoom', 'restRoom', 'balcony'], float_attrs=['twPing'],
                bool_attrs=['lived'])

    post_type = request.form.get("postType")

    if post_type == "sell":

        house_sell = ('hId', 'ratioOfPublicArea', 'pricePerTwping', 'price', 'age', 'houseType', 'houseName')
        update_data('`houseSell`', house_sell, int_attrs=['age'],
                    float_attrs=['ratioOfPublicArea', 'pricePerTwping', 'price'])

    elif post_type == "rent":
        house_rent = ("hId", "price", "refrigerator", "washingMachine", "TV", "airConditioner",
                      "waterHeater", "bed", "closet", "paidTVChannel", "internet",
                      "gas", "sofa", "deskChair", "balcony", "elevator", "parkingSpace")

        house_rent_bool_attrs = ["refrigerator", "washingMachine", "TV", "airConditioner",
                                 "waterHeater", "bed", "closet", "paidTVChannel", "internet",
                                 "gas", "sofa", "deskChair", "balcony", "elevator", "parkingSpace"]
        update_data('`houseRent`', house_rent, int_attrs=["price"], bool_attrs=house_rent_bool_attrs)

    flash('貼文修改成功')
    return redirect(url_for('my_post'))


@app.route('/update/region', methods=['POST'])
def update_region():
    selected_region = request.json['region']
    session['selected_region'] = selected_region
    return 'susses'


@app.route('/update/priceOrder', methods=['POST'])
def update_price_order():
    selected_order = request.json['priceOrder']
    session['selected_order'] = selected_order
    return 'susses'


@app.route('/update/twPingOrder', methods=['POST'])
def update_tw_ping_order():
    selected_order = request.json['twPingOrder']
    session['selected_order'] = selected_order
    return 'susses'


@app.route('/update/pattern', methods=['POST'])
def update_pattern():
    selected_pattern = request.json['pattern']
    session['selected_pattern'] = selected_pattern
    return 'susses'


@app.route('/update/houseType', methods=['POST'])
def update_house_type():
    selected_house_type = request.json['houseType']
    session['selected_houseType'] = selected_house_type
    return 'susses'


@app.route('/update/type', methods=['POST'])
def update_type():
    selected_type = request.json['type']
    session['selected_type'] = selected_type
    return 'susses'


@app.route('/update/price', methods=['POST'])
def update_price():
    selected_price = request.json['price']
    session['selected_price'] = selected_price
    return 'susses'


@app.route('/update/twPing', methods=['POST'])
def update_tw_ping():
    selected_tw_ping = request.json['twPing']
    session['selected_twPing'] = selected_tw_ping
    return 'susses'


@app.route('/update/age', methods=['POST'])
def update_age():
    selected_age = request.json['age']
    session['selected_age'] = selected_age
    return 'susses'


@app.route('/update/region', methods=['POST'])
def update():
    selected_region = request.json['region']
    session['selected_region'] = selected_region
    return 'susses'


@app.route('/update/myPost', methods=['POST'])
def update_my_post():
    selected_my_post = request.json['myPost']

    session['selected_myPost'] = selected_my_post
    return 'susses'


@app.route('/update/browses', methods=['POST'])
def update_browses():
    u_id = current_user.get_id() if current_user.get_id() else 0
    p_id = request.json['pId']

    now = dt.datetime.now()
    db, cursor = link_sql()
    sql = f"SELECT * FROM `post` WHERE `pId` = {p_id} limit 1"
    cursor.execute(sql)
    post_author = cursor.fetchone()["uId"]

    sql = f"SELECT MAX(`browseTime`) AS `browseTime` FROM `browses` WHERE `pId` = {p_id} AND `uId` = {u_id} limit 1"
    cursor.execute(sql)

    last_visit = cursor.fetchone()['browseTime']

    if last_visit is not None and (now - last_visit <= dt.timedelta(1) or p_id == post_author):
        return "browses add deny"

    sql = f"INSERT INTO `browses`(`uId`,`pId`,`browseTime`) VALUES ({u_id},{p_id},'{now}')"
    cursor.execute(sql)
    db.commit()
    db.close()
    return "susses"


# 登入的 API
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    # 驗證使用者資訊
    db, cursor = link_sql()
    cursor.execute(f"SELECT * FROM `user` "
                   f"WHERE email = '{email}'")
    user = cursor.fetchone()
    cursor.close()
    db.close()

    if user is None:
        return 'invalid email'

    if user['password'] != password:
        return 'password error'

    # 如果驗證成功，使用 login_user 函數登入使用者
    login_user(User(user['uId'], user['email'], user['permission']))

    flash('成功登入')
    return 'success'


@app.route('/signup', methods=['POST'])
def signup():
    # 獲取表單提交的用戶詳細信息
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']

    # 檢查用戶是否已經註冊
    if check_user_exist(email):
        # 如果用戶已經註冊，返回錯誤消息
        flash('該用戶已經註冊')
        return 'already signup'

    # 如果用戶尚未註冊，將其詳細信息存儲到資料庫中
    db, cursor = link_sql()
    sql = "INSERT INTO `user` (`name`, `email`, `password`) VALUES (%s, %s, %s)"
    cursor.execute(sql, (name, email, password))
    db.commit()

    # 獲取用戶 ID
    sql = "SELECT * FROM `user` WHERE `email` = %s "
    cursor.execute(sql, (email,))
    user = cursor.fetchone()
    db.close()
    # 登入用戶
    user = User(user['uId'], user['email'], user['permission'])
    login_user(user)

    # 返回一個成功消息
    flash('用戶註冊成功')
    return 'success'


# 登出的 API

@app.route('/logout')
@login_required
def logout():
    # 使用 logout_user 函數登出使用者
    logout_user()
    flash('成功登出')
    return redirect(url_for('index'))


@app.route('/delete_post_sell', methods=['POST'])
def delete_post_sell():
    db, cursor = link_sql()
    p_id = request.form['delete-pId']

    sql = "DELETE house, post, image, housesell, payment, browses " \
          "FROM house " \
          "JOIN post ON house.pId = post.pId " \
          "JOIN image ON image.pId = post.pId " \
          "JOIN housesell ON house.hId = housesell.hId " \
          "JOIN payment ON payment.pId = post.pId " \
          "JOIN browses ON browses.pId = post.pId " \
          "WHERE post.pId = %s "
    cursor.execute(sql, (p_id,))
    db.commit()
    flash('貼文刪除成功')

    return redirect(url_for('sell'))


@app.route('/delete_post_rent', methods=['POST'])
def delete_post_rent():
    db, cursor = link_sql()
    p_id = request.form['delete-pId']

    sql = "DELETE house, post, image, houserent, payment, browses  " \
          "FROM house JOIN post ON house.pId = post.pId " \
          "JOIN image ON image.pId = post.pId " \
          "JOIN houserent ON house.hId = houserent.hId " \
          "JOIN payment ON payment.pId = post.pId " \
          "JOIN browses ON browses.pId = post.pId " \
          "WHERE post.pId = %s"

    cursor.execute(sql, (p_id,))
    db.commit()
    flash('貼文刪除成功')

    return redirect(url_for('rentals'))


@app.route('/browses_record.html')
@login_required
def browses_record():
    selected_u_id = current_user.id
    # rent_sql = f"SELECT * " \
    #        f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
    #        f"INNER JOIN `image` ON image.pId = post.pId) " \
    #        f"INNER JOIN `houserent` ON house.hId = houserent.hId " \
    #        f"INNER JOIN (SELECT post.pId,browses.uId " \
    #        f"FROM post " \
    #        f"INNER JOIN browses ON browses.pId = post.pId " \
    #        f"WHERE browses.uId = {selected_u_id}) AS record ON post.pId = record.pId"
    rent_sql = f"SELECT * " \
               f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
               f"INNER JOIN `image` ON image.pId = post.pId) " \
               f"INNER JOIN `houserent` ON house.hId = houserent.hId " \
               f"INNER JOIN (SELECT post.pId,COUNT(browses.uId) as click " \
               f"FROM post LEFT OUTER JOIN `browses` ON browses.pId = post.pId " \
               f"GROUP BY post.pId) AS click  ON post.pId = click.pId " \
               f"INNER JOIN (SELECT DISTINCT post.pId, browses.uId " \
               f"FROM post " \
               f"INNER JOIN browses ON browses.pId = post.pId " \
               f"WHERE browses.uId = {selected_u_id}) AS record ON post.pId = record.pId"

    sell_sql = f"SELECT * " \
               f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
               f"INNER JOIN `image` ON image.pId = post.pId) " \
               f"INNER JOIN `housesell` ON house.hId = housesell.hId " \
               f"INNER JOIN (SELECT post.pId,COUNT(browses.uId) as click " \
               f"FROM post LEFT OUTER JOIN `browses` ON browses.pId = post.pId " \
               f"GROUP BY post.pId) AS click  ON post.pId = click.pId " \
               f"INNER JOIN (SELECT DISTINCT post.pId, browses.uId " \
               f"FROM post " \
               f"INNER JOIN browses ON browses.pId = post.pId " \
               f"WHERE browses.uId = {selected_u_id}) AS record ON post.pId = record.pId"

    rent_results = get_post_data(rent_sql)
    sell_results = get_post_data(sell_sql)

    return render_template(
        'browses_record.html',
        record_rent_results=rent_results,
        record_sell_results=sell_results
    )


if __name__ == '__main__':
    app.run(debug=True)
