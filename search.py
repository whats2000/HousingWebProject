import openai
import json

import pymysql

from database import link_sql

# OpenAI API key
with open("setting.json") as f:
    data = json.load(f)
    openai.api_key = data["OpenAIKey"]


def generate_sql_query(search_type: str = None, query: str = None, selected_region: str = None):
    if query is None:
        return ''

    if search_type == 'buy':
        sql = f"""
            SELECT *
            FROM ((`house` INNER JOIN `post` ON house.pId = post.pId)
            INNER JOIN `image` ON image.pId = post.pId)
            INNER JOIN `housesell` ON house.hId = housesell.hId
            INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click
            FROM post
            LEFT OUTER JOIN browses ON browses.pId = post.pId
            GROUP BY post.pId) AS click  ON post.pId = click.pId
            WHERE (`city` = '{selected_region}') """

        prompt = f"""
            ### HouseWebsite SQL tables, with their properties:
            #
            # post(pId, uId, title, city: 市or縣, district 區or縣轄市or鄉, address: full address remove [city, district], 
            # name: 負責人名, phone, description, reviseDateTime)
            # house(hId, pId, type: enum {{'住宅', '獨立套房', '分租套房', '雅房'}}, twPing: unit is '台灣坪', floor, lived, 
            # bedRoom: int >= 0, livingRoom: int >= 0, restRoom: int >= 0, balcony: int >= 0)
            # housesell(hId, ratioOfPubicArea: unit is '公共設施比率', pricePerTwping, price: int unit is '萬', age, 
            # houseType: enum {{'華夏', '電梯大樓', '公寓', '透天厝', '別墅'}}, houseName: 社區名稱)
            #
            ### A query to find the possible post which matches the condition is '{query}', 
            don't let query contain anything not in enum and don't judge unconditional relations
            ### Below is my SQL need to find the posts complete something behind "Where"
            SELECT *
            FROM ((`house` INNER JOIN `post` ON house.pId = post.pId)
            INNER JOIN `image` ON image.pId = post.pId)
            INNER JOIN `housesell` ON house.hId = housesell.hId
            INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click
            FROM post
            LEFT OUTER JOIN browses ON browses.pId = post.pId
            GROUP BY post.pId) AS click  ON post.pId = click.pId
            WHERE (`city` = '{selected_region}') """
    else:
        sql = f"""
            SELECT *
            FROM ((`house` INNER JOIN `post` ON house.pId = post.pId)
            INNER JOIN `image` ON image.pId = post.pId)
            INNER JOIN `houserent` ON house.hId = houserent.hId
            INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click
            FROM post
            LEFT OUTER JOIN browses ON browses.pId = post.pId
            GROUP BY post.pId) AS click  ON post.pId = click.pId
            WHERE (`city` = '{selected_region}') """

        prompt = f"""
            ### HouseWebsite SQL tables, with their properties:
            #
            # post(pId, uId, title, city: 市or縣, district 區or縣轄市or鄉, address: full address remove [city, district], 
            # name: 負責人名, phone, description, reviseDateTime)
            # house(hId, pId, type: enum {{'住宅', '獨立套房', '分租套房', '雅房'}}, twPing: unit is '台灣坪', floor, lived, 
            # bedRoom: int >= 0, livingRoom: int >= 0, restRoom: int >= 0, balcony: int >= 0)
            # houserent(hId, price, refrigerator, washingMachine, TV, airCondition, waterHeater, bed, closet, 
            # paidTVChannel: 第四台, internet, gas, sofa, deskChair, elevator, parkingSpace)
            ### A query to find the possible post which matches the condition is '{query}', 
            don't let query contain anything not in enum and don't judge unconditional relations
            ### Below is my SQL need to find the posts complete something behind "Where"
            SELECT *
            FROM ((`house` INNER JOIN `post` ON house.pId = post.pId)
            INNER JOIN `image` ON image.pId = post.pId)
            INNER JOIN `houserent` ON house.hId = houserent.hId
            INNER JOIN  (SELECT post.pId,COUNT(browses.uId) as click
            FROM post
            LEFT OUTER JOIN browses ON browses.pId = post.pId
            GROUP BY post.pId) AS click  ON post.pId = click.pId
            WHERE (`city` = '{selected_region}') """

    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )

    response_sql = response.choices[0].text.strip()

    db, cursor = link_sql()
    sql += response_sql

    try:
        cursor.execute(sql)
        result = cursor.fetchall()
        db.close()

        return result
    except pymysql.err.MySQLError:
        print(pymysql.err.MySQLError, sql)
        return None
