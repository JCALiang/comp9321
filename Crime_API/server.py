from mongoengine import connect, queryset
from models import xlms2json, postcode_dict, Lga
from flask import request, render_template, Flask, make_response, abort, jsonify
from flask_cors import CORS
from functools import wraps
import requests
import csv, os
import json
from werkzeug.contrib.atom import AtomFeed, FeedEntry
from datetime import datetime
from dicttoxml import dicttoxml
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)

SECRET_KEY= 'SECRET_KEY'
postcode, lgaa=postcode_dict()


app = Flask(__name__)
CORS(app)


connect(
    host='mongodb://DBLiang:1234@ds249249.mlab.com:49249/9321lab7'
)

def authenticate_by_token(token):
    if token is None:
        return False
    s=Serializer(SECRET_KEY)

    try:
        user = s.loads(token.encode())
    except SignatureExpired:
        return False # valid token, but expired
    except BadSignature:
        return False # invalid token
    if user=='admin':
        return True
    return False


def login_required(f, message="Not Authoriszed"):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("AUTH_TOKEN")
        if authenticate_by_token(token):
            return f(*args, **kwargs)
        return jsonify(message=message), 401
    return decorated_function

def generate_token(username):
    s = Serializer(SECRET_KEY, expires_in = 600)
    return s.dumps(username)


def posting(district):
    url='http://www.bocsar.nsw.gov.au/Documents/RCS-Annual/'+district+'lga.xlsx'

    r=requests.get(url)
    if r.status_code==404:
        return 0

    with open("temp.xlsx", 'wb') as f:
        f.write(r.content)

    d= xlms2json("temp.xlsx", district)
    os.remove("temp.xlsx")

    connect('lga')
    d.save()
    return 1

def check_duplicate(item):
    connect('lga')
    found=0
    for i in Lga.objects:
        if i.id==item:
            return 1
    return 0

def jsontoXML(doc, d):
    xjson = doc.to_json()
    xjson= json.loads(xjson)
    xml = dicttoxml(xjson, custom_root='data', attr_type=False)
    xml = xml.decode('utf-8')
    xml = xml[39:]
    entry=FeedEntry(id= "http://127.0.0.1:5000/lga/"+d, content_type="xhtml",content=xml,  author="Chieh An Liang", 
                    title=d.upper()+' Recorded Crime Statistics',
                    updated=datetime.now())
    return entry





@app.route('/')
def index():
    return render_template('client.html')


@app.route('/login', methods=['POST'])
def login():
    r=request.get_json()
    if r is None:
    	return jsonify(Error="Require parameters: username and password")

    attempted_username = r['username']
    attempted_password = r['password']
   
    if attempted_username=='admin' and attempted_password==str(1234):
        token=generate_token(attempted_username)
        return jsonify(token=token.decode()), 200
    return jsonify(Error="Not Authenticated"), 401



@app.route('/lga', methods=["POST"])
@login_required
def load():
    r=request.get_json()
    print('xxxx')
    if r['lgaName']:
        district = r['lgaName']
        district=district.lower()

        feed = AtomFeed(title='NSW Recorded Crime Statistics',
                        id= "http://127.0.0.1:5000/lga/"+district,
                        author="Chieh An Liang")
        feed.add(id= "http://127.0.0.1:5000/lga/"+district, author="Chieh An Liang", 
                        title=district.upper()+' Recorded Crime Statistics',
                        updated=datetime.now(), content=" ")

        if check_duplicate(district):
            return feed.get_response(), 200

        posting(district)
        if posting(district) == 0:
            return jsonify(error="Invalid address"), 404
        return feed.get_response(), 201

    else:
        code = r['postcode']
        code=int(code)
        if code not in postcode:
            return jsonify(message="Cannot identify LGA"), 400

        ddd=postcode[code]
        print(ddd)
        entry=[]
        status=201

        feed = AtomFeed(title='NSW Recorded Crime Statistics',
                        id= "http://127.0.0.1:5000/lga/"+str(code),
                        author="Chieh An Liang")

        for d in ddd:
            feed.add(id= "http://127.0.0.1:5000/lga/"+d,  author="Chieh An Liang", 
                title=d.upper()+' Recorded Crime Statistics', content=" ",
                updated=datetime.now())

            if check_duplicate(d):
                status=200
                continue
            posting(d)

        return feed.get_response(), status 



@app.route('/lga/<item>', methods=["Delete"])
@login_required
def delete(item):
    connect('lga')
    for i in Lga.objects:
        if i.id==item:
            i.delete()
            return jsonify(message="Success"), 200

    return jsonify(message="No record Found"), 404



@app.route('/lga/<item>', methods=['GET'])
def get_lga(item):
    connect('lga')

    if request.args.get('tag') not in ["0","1"]:
    	return jsonify(Error="Please enter a valid file format: 0 for ATOM, 1 for JSON"), 404

    found=0
    for i in Lga.objects:
        if i.id==item:
            x=i
            found=1
            break

    if not found:
        return jsonify(message="No record found"), 404

    xjson = x.to_json()
    xjson= json.loads(xjson)
    if request.args.get('tag')=='1':
        xjson=json.dumps(xjson)
        return xjson, 200
    
    if request.args.get('tag')=='0':
	    xml = dicttoxml(xjson, custom_root='data', attr_type=False)
	    xml = xml.decode('utf-8')
	    xml = xml[39:]


	    entry= [FeedEntry(id= "http://127.0.0.1:5000/lga/"+item, content_type="xhtml", content=xml,  author="Chieh An Liang", 
	                    title=item+' Recorded Crime Statistics',
	                    updated=datetime.now())]

	    feed = AtomFeed(title='NSW Recorded Crime Statistics',
	            id="http://127.0.0.1:5000/lga/"+item,
	            author="Chieh An Liang",
	            entries=entry)
	    return feed.get_response(),200




@app.route('/lga', methods=['GET'])
def get_all():

    connect('lga')

    if request.args.get('tag')=='1':
        q_set = Lga.objects()
        xjson= q_set.to_json()
        xjson= json.loads(xjson)
        xjson=json.dumps(xjson)
        return xjson, 200

    feed = AtomFeed(title='NSW Recorded Crime Statistics',
            id="http://127.0.0.1:5000/lga",
            author="Chieh An Liang")

    if request.args.get('tag')=='0':
        for i in Lga.objects:
            xml=jsontoXML(i, i.district)

            feed.add(id= "http://127.0.0.1:5000/lga/"+i.id, content_type="xhtml",content=xml,  author="Chieh An Liang", 
                        title=i.id+' Recorded Crime Statistics',
                        updated=datetime.now())
        return feed.get_response(), 200
    return jsonify(Error="Please supply a valid file format: 0 for ATOM, 1 for JSON"), 404



@app.route('/lga/filter', methods=['GET'])
def filter():
    url= request.url
    params= url.replace('http://127.0.0.1:5000/lga/filter?','')
    params=params.lower()
    params= params.split()
    feed = AtomFeed(title='NSW Recorded Crime Statistics',
            id="http://127.0.0.1:5000/lga/filter",
            author="Chieh An Liang")

    connect('lga')
    
    for i in range(len(params)):
        #two query case
        if params[i] in ['and', 'or']:
            separator= params[i]
            term1= params[:i]
            term2= params[i+1:]

            if term1[1]!='eq' or term1[0]!='lganame' or term2[1]!='eq' :
                return jsonify(Error="Filter mode not supported"), 404

            lgaValue1= term1[2:]
            lgaValue1= ''.join(lgaValue1)
            
            if separator=='or':
                lgaValue2= term2[2:]
                lgaValue2= ''.join(lgaValue2)
                print('lgaValue2: ',lgaValue2)
                if term2[0]!='lganame':
                	return jsonify(Error="Filter mode not supported"), 404
                x1= Lga.objects(district=lgaValue1)
                x2= Lga.objects(district=lgaValue2)
                if not (x1 or x2):
                    return jsonify(Error="Lga Names not found"), 404
                elif not x1:
                    feed.add(jsontoXML(x2, lgaValue2))
                elif not x2:
                     feed.add(jsontoXML(x1, lgaValue1))
                else:
                    feed.add(jsontoXML(x1, lgaValue1))
                    feed.add(jsontoXML(x2, lgaValue2))
                return feed.get_response(), 200

            else:
                print(term1)
                print(term2)

                try:
                    yearFind= term2[2]
                except:
                    return jsonify(Error="Please input year value"), 404
                try:
                    int(yearFind)
                except:
                    return jsonify(Error="Year should be 4 digits value"), 404

                if len(yearFind)!=4:
                    return jsonify(Error="Year should be 4 digits value"), 404
                if term2[0]!='year':
                    return jsonify(Error="Filter mode not supported"), 404

                x1=Lga.objects(district=lgaValue1)
                if not x1:
                    return jsonify(Error="lgaName not Found"), 404



                x1= x1.to_json()
                x1=json.loads(x1)

                qResult=[]
                for dict_item in x1:
                    for k, v in dict_item.items():
                        if k=="offencegroups":
                            for k1, v1 in v.items():
                                for k2, v2 in v1.items():
                                    if k2=="offencetypes":
                                        for k3, v3 in v2.items():
                                            for k4, v4 in v3.items():
                                                if k4=="years":
                                                    for year, vfinal in v4.items():
                                                        if year== yearFind:
                                                            qResult.append(vfinal)

                qr= dicttoxml(qResult, attr_type=False)
                xml=qr.decode('utf-8')
                xml = xml[63:-7]
                feed.add(FeedEntry(id= "http://127.0.0.1:5000/lga/"+lgaValue1, content_type="xhtml",content=xml,  author="Chieh An Liang", 
                    title=lgaValue1.upper()+' Recorded Crime Statistics ' + yearFind,
                    updated=datetime.now()))
                return feed.get_response(), 200



    #single query case
    lgaValue= params[2:]
    lgaValue= ''.join(lgaValue)
    if params[1]!='eq' or params[0]!='lganame':
        return jsonify(Error="Filter mode not supported"), 404
    #check if value found
    x= Lga.objects(district=lgaValue)
    if not x:
        return jsonify(Error="Lga Names not found"), 404
    feed.add(jsontoXML(x, lgaValue))
    return feed.get_response(), 200





if __name__ == '__main__':
    # save_information()
    app.run()

