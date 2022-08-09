from flask import Flask, render_template, redirect, request
from flask_graphql import GraphQLView
from flask_sqlalchemy import SQLAlchemy
import typing
import graphene
import os
import json
from sqlalchemy.exc import IntegrityError
import traceback
import werkzeug
import smtplib
from smtplib import SMTPException

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.do')
app.config.from_file(os.path.join(".", "config/default_app_config.json"), load=json.load,silent=False)  #default settings
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI","Specified environment variable is not set.")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS","Specified environment variable is not set.")
app.config["SQLALCHEMY_POOL_RECYCLE"] = 60
db = SQLAlchemy(app)

from models import Feature as FeatureModel
from models import Tag as TagModel
from models import Area as AreaModel


def send_success_email(payload):
    sender = 'from@fromdomain.com'
    receivers = ['joekalb@protonmail.com']

    message = """From: From Person <from@fromdomain.com>
To: Joe Kalb <joekalb@protonmail.com>
Subject: SMTP e-mail test

This is a test e-mail message.
"""

    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender,receivers,message)
        print("Successfully sent email")
    except Exception:
        traceback.print_exc()
        print("Error: unable to send email")


def generate_geo_json_data(area):
    features_json_dicts = []

    for feature in area.features:
        if feature.enabled:
            features_json_dicts.append(feature.to_json_dict())

    j = {
        "features": features_json_dicts,
        "type": "FeatureCollection"
    }

    return json.dumps(j)

def generate_tags_json_data():
    tags_json_dicts = []
    all_tags = TagModel.query.all()
    for tag in all_tags:
        tags_json_dicts.append({
            tag.tag_name: {
                "tag_name": tag.tag_name,
                "description": tag.description,
                "parent_category": tag.parent_category,
                "plural_description": tag.plural_description
            }
        })
    j = {
        "tags": tags_json_dicts
    }
    return json.dumps(j)

def generate_tags_map_data():
    all_tags = TagModel.query.all()
    tag_entries = []
    for tag in all_tags:
        str = '"{tag_name}": {{"tag_name":"{tag_name}", "description": "{description}", "parent_category": "{parent_category}", "plural_description": "{plural_description}"}}'.format(tag_name=tag.tag_name,description=tag.description,parent_category=tag.parent_category,plural_description=tag.plural_description)
        tag_entries.append(str)
    tag_map_data = '{{{tag_entries}}}'.format(tag_entries=(", ".join(tag_entries)))
    return tag_map_data

def load_database_from_json():
    json_obj = ""
    with open("./static/json/wapf-naples.json", "r") as json_file:
        json_obj = json.load(json_file)

    swfl_area_model = AreaModel(short_name="swfl",name="Southwest Florida",wapf_chapter_name="WAPF Naples Chapter",short_display_name="SWFL",latitude=26.142198,longitude=-81.794294)

    for tag in json_obj['tagDescriptions']:
        tm = TagModel(tag_name=tag['tag'],
            description=tag['description'],
            parent_category=tag['parent_category'],
            plural_description=tag['plural_description']
        )
        db.session.add(tm)
    for feature in json_obj['features']:
        phone = ""
        try:
            phone = feature['properties']['phone']
        except KeyError:
            phone = ""

        fm = FeatureModel(short_name=feature['properties']['short_name'],
            enabled=feature['properties']['enabled'],
            name=feature['properties']['name'],
            description=feature['properties']['description'],
            why_on_wapf_list=feature['properties']['why_on_wapf_list'],
            primary_tag=feature['properties']['primary_tag'],
            address=feature['properties']['address'],
            phone=phone,
            url=feature['properties']['url'],
            longitude=feature['geometry']['coordinates'][0],
            latitude=feature['geometry']['coordinates'][1],
            type=feature['geometry']['type']
        )
        for tag in feature['properties']['tags']:
            print(tag)
            fm.tags.append(TagModel.query.filter_by(tag_name=tag).first())
        fm.areas.append(swfl_area_model)
        db.session.add(fm)

    db.session.commit()
    return json_obj

def generate_json_from_database():
    features_json_dicts = []
    all_enabled_features = FeatureModel.query.filter_by(enabled=True)
    for feature in all_enabled_features:
        features_json_dicts.append(feature.to_json_dict())

    tags_json_dicts = []
    all_tags = TagModel.query.all()
    for tag in all_tags:
        tags_json_dicts.append(tag.to_json_dict())

    j = {
        "features": features_json_dicts,
        "type": "FeatureCollection",
        "tagDescriptions": tags_json_dicts
    }

    return json.dumps(j,indent=2)

@app.route("/holistic")
def holistic_home_page_redirect():
    return redirect("/holistic/");

@app.route("/holistic/")
def holistic_home():
    all_areas = AreaModel.query.all()
    return render_template("home.html",areas=all_areas)

@app.route("/swflholistic")
def swflholistic_redirect():
    return redirect("/holistic/area/swfl")

@app.route("/swflholistic/viewtag.html")
def viewtag_redirect():
    return redirect("/holistic/tag/{tag}".format(tag=request.args.get("tag")))

@app.route("/swflholistic/viewdetail.html")
def viewdetail_redirect():
    return redirect("/holistic/feature/{feature_short_name}".format(feature_short_name=request.args.get("short_name")))


@app.route("/holistic/area/<area_short_name>")
def index(area_short_name):
    area = AreaModel.query.filter_by(short_name=area_short_name).first()
    areas = AreaModel.query.all()
    if area == None:
        return "No area in data set with identifier {area_short_name}".format(area_short_name=area_short_name)
    geo_json_data = generate_geo_json_data(area)
    tags_map_data = generate_tags_map_data()
    area_enabled_features = []
    for feature in area.features:
        if feature.enabled:
            area_enabled_features.append(feature)
    return render_template("main_page.html",features=area_enabled_features,geo_json_data=geo_json_data,tags_map_data=tags_map_data,area=area,areas=areas)

@app.route("/holistic/feature/<short_name>")
def featurePage(short_name):
    feature = FeatureModel.query.filter_by(short_name = short_name, enabled = True).first()
    return render_template("feature.html",feature=feature)

@app.route("/holistic/tag/<tag_name>")
def tagPage(tag_name):
    tag = TagModel.query.filter_by(tag_name = tag_name).first()
    print(tag.features)
    return render_template("tag.html",tag=tag)

@app.route("/holistic/load-json-from-database")
def build_json_from_database():
    return generate_json_from_database()

@app.route("/holistic/load-database-from-json-XYZ")
def load_database_from_json_xyz():
    load_database_from_json()
    return "Loaded the database."

@app.route("/holistic/addfeature")
def add_feature():
    all_areas = AreaModel.query.all()
    all_tags = TagModel.query.all()
    return render_template("new_feature.html",all_areas=all_areas,all_tags=all_tags)

@app.route("/holistic/api/feature", methods = ['POST'])
def api_feature():
    try:
        print("\r\n\r\n\r\n\r\n")
        print("Before get_json(), request is: {request}".format(request=request))
        input_payload = request.get_json()

        print("Loaded input_payload {input_payload}".format(input_payload=input_payload))

        name = None
        enabled = None
        short_name = None #not required
        description = None
        why_on_wapf_list = None
        longitude = None
        latitude = None
        primary_tag = None
        address = None
        phone = None    #not required
        url = None  #not required
        type = None

        try:
            name = input_payload["name"]
            enabled = input_payload["enabled"]
            description = input_payload["description"]
            why_on_wapf_list = input_payload["why_on_wapf_list"]
            longitude = input_payload["longitude"]
            latitude = input_payload["latitude"]
            primary_tag = input_payload["primary_tag"]
            address = input_payload["address"]
            type = input_payload["type"]
        except KeyError as ke:
            error_j = {"status":"error","error_message":"Missing required field {key}".format(key=ke)}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        try:
            short_name = input_payload["short_name"]
        except KeyError as ke:
            print("optional field short_name not entered")

        try:
            phone = input_payload["phone"]
        except KeyError as ke:
            print("optional field phone not entered")

        try:
            url = input_payload["url"]
        except KeyError as ke:
            print("optional field url not entered")

        if short_name != None and not isinstance(short_name,str):
            error_j = {"status":"error","error_message":"short_name must be of type string."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        if short_name == None or short_name == "":
            short_name = "autogen"

        f = FeatureModel.query.filter_by(short_name=short_name).first()
        if f != None:
            i = 0
            while True:
                str_gen_short_name = "{short_name}{i}".format(short_name=short_name,i=i)
                f = FeatureModel.query.filter_by(short_name=str_gen_short_name).first()
                if f != None:
                    i = i + 1
                else:
                    short_name = str_gen_short_name
                    break

        if not isinstance(name,str) or name == "":
            error_j = {"status":"error","error_message":"name must have a string value with length >= 1."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(enabled,bool):
            error_j = {"status":"error","error_message":"enabled must have a boolean value."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(description,str) or description == "":
            error_j = {"status":"error","error_message":"description must have a string value with length >= 1."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(why_on_wapf_list,str) or why_on_wapf_list == "":
            error_j = {"status":"error","error_message":"why_on_wapf_list must have a string value with length >= 1."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(longitude,float):
            error_j = {"status":"error","error_message":"longitude must be a float"}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(latitude,float):
            error_j = {"status":"error","error_message":"latitude must be a float"}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(primary_tag,str) or primary_tag == "":
            error_j = {"status":"error","error_message":"primary_tag must have a string value with length >= 1"}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif TagModel.query.filter_by(tag_name=primary_tag).first() == None:
            error_j = {"status":"error","error_message":"Entered primary_tag {primary_tag} is not a valid value.".format(primary_tag=primary_tag)}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(address,str) or address == "":
            error_j = {"status":"error","error_message":"address must have a string value with length >= 1."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}
        elif not isinstance(type,str) or type == "":
            error_j = {"status":"error","error_message":"type must have a string value with length >= 1."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        tags = input_payload["tags"]
        areas = input_payload["areas"]

        new_fm = FeatureModel(name=name,
            enabled=enabled,
            short_name=short_name,
            description=description,
            why_on_wapf_list=why_on_wapf_list,
            longitude=longitude,
            latitude=latitude,
            primary_tag=primary_tag,
            address=address,
            phone=phone,url=url,
            type=type)

        for tag in tags:
            tm = TagModel.query.filter_by(tag_name=tag).first()
            if tm != None:
                new_fm.tags.append(tm)
            else:
                error_j = {"status":"error","error_message":"tags entry '{tag_name}' is invalid.".format(tag_name=tag)}
                return json.dumps(error_j),500,{'Content-Type': 'application/json'}


        for area in areas:
            am = AreaModel.query.filter_by(short_name=area).first()
            if am != None:
                new_fm.areas.append(am)
            else:
                error_j = {"status":"error","error_message":"areas entry '{area_short_name}' is invalid.".format(area_short_name=area)}
                return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        db.session.add(new_fm)
        db.session.commit()

        send_success_email(input_payload)

        success_j = j = {
            "status": "success",
            "short_name": short_name
        }
        return json.dumps(success_j),200,{'Content-Type': 'application/json'}
    except werkzeug.exceptions.BadRequest as br:
        traceback.print_exc()
        error_j = {
            "status":"error",
            "error_message":str(br)
        }
        return json.dumps(error_j),400,{'Content-Type': 'application/json'}
    except IntegrityError as ie:
        traceback.print_exc()
        error_j = {
            "status":"error",
            "error_message":"Could not insert feature into database; data integrity error (technical issue). Details: {details}".format(details=str(ie))
        }
        return json.dumps(error_j),500,{'Content-Type': 'application/json'}
    except Exception as ex:
        traceback.print_exc()
        error_message = "Could not insert feature into database. Technical reason: {reason}".format(reason=str(ex))
        error_j = {
            "status":"error",
            "error_message":error_message
        }
        return json.dumps(error_j),500,{'Content-Type': 'application/json'}

if __name__ == "__main__":
    app.run()
