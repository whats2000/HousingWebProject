import datetime as dt
import os

from PIL import Image
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_login import logout_user, LoginManager, login_user, login_required, UserMixin
from werkzeug.utils import secure_filename

from database import link_sql, check_user_exist

app = Flask(__name__, template_folder='./templates')
app.secret_key = '12345678'
app.config['UPLOAD_POST_IMAGE_FOLDER'] = "static/images/post/"
login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, user_id, email, permission):
        self.id = user_id
        self.email = email
        self.permission = permission

    def __repr__(self):
        return f'<User {self.email}>'


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

    db.close()

    return render_template(
        'index.html',
        selected_region=selected_region,
        recommend_post=results[0],
        family_post=results[1],
        suite_post=results[2],
        shared_post=results[3]
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
    u_id = session.get("uId", 0)

    sql = f"SELECT * " \
          f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
          f"INNER JOIN `image` ON image.pId = post.pId) " \
          f"INNER JOIN `housesell` ON house.hId = housesell.hId " \
          f"WHERE `city` = '{selected_region}' AND type = '住宅'"

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

    sql = sql + house_type_sql + pattern_sql + price_sql + tw_ping_sql + age_sql + my_post_sql

    print(sql)

    db, cursor = link_sql()
    cursor.execute(sql)
    results = cursor.fetchall()

    db.close()

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
    u_id = session.get("uId", 0)

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
          f"WHERE `city` = '{selected_region}' "

    type_sql = "" if str(selected_type) == "All" else f" AND `type` = '{selected_type}'"
    pattern_sql = f" AND `bedRoom` {selected_pattern}"
    price_sql = f" AND `price` {selected_price}"
    tw_ping_sql = f" AND `twPing` {selected_tw_ping}"

    sql = sql + pattern_sql + price_sql + tw_ping_sql + type_sql + my_post_sql
    db, cursor = link_sql()

    cursor.execute(sql)
    results = cursor.fetchall()

    db.close()

    return render_template(
        'rentals.html',
        selected_region=selected_region,
        post_results=results
    )


@app.route('/my_post.html')
def my_post():
    selected_u_id = session.get("uId", 0)
    rent_sql = f"SELECT * " \
               f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
               f"INNER JOIN `image` ON image.pId = post.pId) " \
               f"INNER JOIN `houserent` ON house.hId = houserent.hId " \
               f"WHERE `uId` = {selected_u_id}"

    sell_sql = f"SELECT * " \
               f"FROM ((`house` INNER JOIN `post` ON house.pId = post.pId) " \
               f"INNER JOIN `image` ON image.pId = post.pId) " \
               f"INNER JOIN `housesell` ON house.hId = housesell.hId " \
               f"WHERE `uId` = {selected_u_id}"

    db, cursor = link_sql()

    cursor.execute(rent_sql)
    rent_results = cursor.fetchall()
    cursor.execute(sell_sql)
    sell_results = cursor.fetchall()

    db.close()

    return render_template(
        'my_post.html',
        post_rent_results=rent_results,
        post_sell_results=sell_results
    )


@app.route('/sell_info.html')
def sell_info():
    p_id = request.args.get('pId')
    u_id = session.get("uId", 0)
    selected_region = session.get('selected_region', '台北市')
    db, cursor = link_sql()

    sql = f"SELECT house.*, post.*, image.*, housesell.* " \
          f"FROM ((`house` JOIN `post` ON house.pId = post.pId)" \
          f"JOIN `image` ON image.pId = post.pId)" \
          f"JOIN `housesell` ON house.hId = housesell.hId " \
          f"WHERE post.pId = {p_id} "\
          f"LIMIT 1"

    cursor.execute(sql)
    results = cursor.fetchone()
    db.close()
    
    if u_id == results["uId"]:
        revise_permission = 1
    else:
        revise_permission = 0

    return render_template(
        'sell_info.html',
        pId=p_id,
        revise_permission=revise_permission,
        postType="sell",
        post=results
    )


@app.route('/rentals_info.html')
def rentals_info():
    u_id = session.get("uId", 0)
    selected_region = session.get('selected_region', '台北市')
    db, cursor = link_sql()

    sql = f"SELECT house.*, post.*, image.*, houserent.* " \
          f"FROM ((`house` JOIN `post` ON house.pId = post.pId)" \
          f"JOIN `image` ON image.pId = post.pId)" \
          f"JOIN `houserent` ON house.hId = houserent.hId " \
          f"WHERE `city` = '{selected_region}' AND " \
          f"    post.pId = {request.args.get('pId')} " \
          f"LIMIT 1"

    cursor.execute(sql)
    results = cursor.fetchone()
    revise_permission = 1 if u_id == results["uId"] else 0

    db.close()
    print(u_id, results["uId"])
    return render_template(
        'rentals_info.html',
        pId=request.args.get('pId'),
        postType="rent",
        revise_permission=revise_permission,
        post=results
    )


@app.route('/add_post.html')
def add_post():
    post_type = request.args.get('postType')

    return render_template(
        'add_post.html',
        postType=post_type)


@app.route('/upload_post', methods=['POST', 'GET'])
def upload_post():
    u_id = session.get('uId', 0)
    db, cursor = link_sql()
    sql = f"SELECT `pId` from `post` ORDER BY `pId` DESC LIMIT 1"
    cursor.execute(sql)
    p_id = cursor.fetchone()["pId"] + 1
    sql = f"SELECT `hId` from `house` ORDER BY `hId` DESC LIMIT 1"
    cursor.execute(sql)
    h_id = cursor.fetchone()["hId"] + 1

    def insert_data(entity, attrs, int_attrs=None, float_attrs=None, bool_attrs=None):
        if bool_attrs is None:
            bool_attrs = []
        if float_attrs is None:
            float_attrs = []
        if int_attrs is None:
            int_attrs = []
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
            else:
                result.append(request.form.get(attr))

        fetch_sql = "INSERT INTO " + entity + str(attrs).replace("'", "`") + "VALUES" + str(tuple(result))
        cursor.execute(fetch_sql)
        db.commit()

    post = ('pId', 'uId', 'title', 'city', 'district', 'address', 'name', 'phone', 'description')
    insert_data('`post`', post)

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
                      "gas", "sofa", "deskChair", "rent-balcony", "elevator", "parkingSpace")

        house_rent_bool_attrs = ["refrigerator", "washingMachine", "TV", "airConditioner",
                                 "waterHeater", "bed", "closet", "paidTVChannel", "internet",
                                 "gas", "sofa", "deskChair", "rent-balcony", "elevator", "parkingSpace"]
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
    exp_year = int(str(exp_date).split("/")[1])
    exp_month = int(str(exp_date).split("/")[0])
    exp_date =dt.date(exp_year,exp_month,1)
    if pay_class == 1:
        cost = month * 300
    elif pay_class == 2:
        cost = month * 600
    else:
        cost = month * 1000
    card_number = request.form.get("cardNumber")

    payment = str(('pId', 'payDate', 'endDate', 'class', 'expDate', 'cardNumber', 'cost')).replace("'", "`")
    sql = f"INSERT INTO `Payment`{payment} " \
          f"VALUES ({p_id},'{pay_date}','{end_date}','{pay_class}','{exp_date}','{card_number}',{cost})"
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


@app.route('/revise_post', methods=['POST', 'GET'])
def revise_post():
    db, cursor = link_sql()
    p_id = int(request.form.get("pId"))
    sql = f"SELECT `hId` from `house` where `pId` = {p_id}"
    cursor.execute(sql)
    h_id = cursor.fetchone()["hId"]

    def update_data(entity, attrs, int_attrs=None, float_attrs=None, bool_attrs=None, without_h_id=False):

        if bool_attrs is None:
            bool_attrs = []
        if float_attrs is None:
            float_attrs = []
        if int_attrs is None:
            int_attrs = []
        set_sql = " SET "
        for attr in attrs:
            value = request.form.get(attr)
            if attr in ["pId", "uId", "hId"]:
                continue
            elif attr in bool_attrs:
                if value:
                    set_sql = set_sql + f"`{attr}` = 1, "
                else:
                    set_sql = set_sql + f"`{attr}` = 0, "
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
        try:
            cursor.execute(fetch_sql)
            db.commit()
        except ConnectionError:
            print(fetch_sql)

    post = ('pId', 'uId', 'title', 'city', 'district', 'address', 'name', 'phone', 'description')
    update_data('`post`', post, without_h_id=True)

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
        session['manager'] = 0
        return 'invalid email'

    if user['password'] != password:
        session['manager'] = 0
        return 'password error'

    # 如果驗證成功，使用 login_user 函數登入使用者
    login_user(User(user['uId'], user['email'], user['permission']))
    if user['permission'] == 'manager':
        session['manager'] = 1
        print("manager value:", session['manager'])
    else:
        session['manager'] = 0

    session['uId'] = user['uId']
    session['login_status'] = 1
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

    if user.permission == 'manager':
        session['manager'] = 1
        print("manager value:", session['manager'])
    else:
        session['manager'] = 0

    session['login_status'] = 1

    # 返回一個成功消息
    flash('用戶註冊成功')
    return 'success'


# 登出的 API
@app.route('/logout')
@login_required
def logout():
    # 使用 logout_user 函數登出使用者
    logout_user()
    session['login_status'] = 0
    session['manager'] = 0
    session['uId'] = 0
    flash('成功登出')
    return redirect(url_for('index'))


@app.route('/delete_post_sell')
def delete_post_sell():
    db, cursor = link_sql()
    p_id = request.args.get('pId')

    sql = "DELETE house, post, image, housesell, payment " \
          "FROM house " \
          "JOIN post ON house.pId = post.pId " \
          "JOIN image ON image.pId = post.pId " \
          "JOIN housesell ON house.hId = housesell.hId " \
          "JOIN payment ON payment.pId = post.pId " \
          "WHERE post.pId = %s "
    cursor.execute(sql, (p_id,))
    db.commit()
    flash('貼文刪除成功')

    return redirect(url_for('sell'))


@app.route('/delete_post_rent')
def delete_post_rent():
    db, cursor = link_sql()
    p_id = request.args.get('pId')

    sql = "DELETE house, post, image, houserent, payment " \
          "FROM house JOIN post ON house.pId = post.pId " \
          "JOIN image ON image.pId = post.pId " \
          "JOIN houserent ON house.hId = houserent.hId " \
          "JOIN payment ON payment.pId = post.pId " \
          "WHERE post.pId = %s"

    cursor.execute(sql, (p_id,))
    db.commit()
    flash('貼文刪除成功')

    return redirect(url_for('rentals'))


if __name__ == '__main__':
    app.run(debug=True)
