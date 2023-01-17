from flask import Flask, render_template, redirect, request
from flask_graphql import GraphQLView
from flask_sqlalchemy import SQLAlchemy
import typing
import graphene
import os
import json
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
import traceback
import werkzeug
import smtplib
from smtplib import SMTPException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

required_env_vars = ["SENDGRID_API_KEY","SQLALCHEMY_DATABASE_URI","SENDGRID_FROM_EMAIL","SENDGRID_TO_EMAILS"]
for env_var in required_env_vars:
    env_val = os.environ.get(env_var)
    if env_val == None:
        raise Exception("Required env var {env_var} not set".format(env_var=env_var))

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.do')
app.config.from_file(os.path.join(".", "config/default_app_config.json"), load=json.load,silent=False)  #default settings
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI","Specified environment variable is not set.")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS","Specified environment variable is not set.")
app.config["SQLALCHEMY_POOL_RECYCLE"] = 60
db = SQLAlchemy(app)
logger = logging.getLogger("werkzeug")
handler = logging.FileHandler("log/joekalb.log")
logger.addHandler(handler)

from models import Feature as FeatureModel
from models import Tag as TagModel
from models import Area as AreaModel
from models import AreaFeature as AreaFeatureModel

from selectable import Selectable
from selectable import SelectableFilter


def send_success_email(payload):
    logger.info("Sending success email: {payload}".format(payload=payload))
    sender = os.environ.get("SENDGRID_FROM_EMAIL")
    receivers = os.environ.get("SENDGRID_TO_EMAILS").split(",")
    subject = 'Holistic Resource added to directory'
    html_content = "Holistic resource added to directory, please confirm via your PythonAnywhere database account. {payload}".format(payload=payload)
    message = Mail(
        from_email=sender,
        to_emails=receivers,
        subject=subject,
        html_content=html_content)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        logger.info("Responses for holistic resource added-to-directory email...")
        logger.info(response.status_code)
        logger.info(response.body)
        logger.info(response.headers)
    except Exception:
        traceback.print_exc()
        logger.info("Error: unable to send email")

def generate_geo_json_data_features(features):
    features_json_dicts = []

    for feature in features:
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

def generate_areas_map_data():
    all_areas = AreaModel.query.all()
    area_entries = []
    for area in all_areas:
        str = '"{area_short_name}": {{"short_name":"{area_short_name}", "display_name":"{display_name}"}}'.format(area_short_name=area.short_name,display_name=area.name)
        area_entries.append(str)
    area_map_data = '{{{area_entries}}}'.format(area_entries=(", ".join(area_entries)))
    return area_map_data

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
            logger.info(tag)
            fm.tags.append(TagModel.query.filter(TagModel.tag_name==tag).first())
        fm.areas.append(swfl_area_model)
        db.session.add(fm)

    db.session.commit()
    return json_obj

def generate_json_from_database():
    features_json_dicts = []
    all_enabled_features = FeatureModel.query.filter(FeatureModel.enabled==True)
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

@app.route("/")
def home_page():
    logger.info("Redirecting from / to /dev")
    return redirect("/dev")

@app.route("/dev")
def dev_home_page():
    logger.info("Rendering dev/index.html")
    return render_template("dev/index.html")

@app.route("/dev/index.html")
def dev_home_page_redirect():
    logger.info("Redirecting from /dev/index.html to /dev")
    return redirect("/dev")

@app.route("/dev/experience.html")
def dev_experience_page():
    logger.info("Rendering dev/experience.html")
    return render_template("dev/experience.html")

@app.route("/dev/about.html")
def dev_about_page():
    logger.info("Rendering dev/about.html")
    return render_template("dev/about.html")

@app.route("/dev/contact.html")
def dev_contact_page():
    logger.info("Rendering dev/contact.html")
    return render_template("dev/contact.html")

@app.route("/dev/sendContactEmail", methods = ['POST'])
def dev_send_contact_email_page():
    try:
        logger.info("\r\n\r\n\r\n\r\n")
        logger.info("Before get_json(), request is: {request}".format(request=request))
        input_payload = request.get_json()

        logger.info("Loaded input_payload {input_payload}".format(input_payload=input_payload))

        name = None
        email = None
        message = None

        try:
            name = input_payload["name"]
            email = input_payload["email"]
            message = input_payload["message"]

        except KeyError as ke:
            error_j = {"status":"error","error_message":"Missing required field {key}".format(key=ke)}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        subject = "Message from {name} on JoeKalb.com/dev".format(name=name)
        html_message =  subject + "<br /><br />From Email: " + email + "<br /><br />" + message
        email_message = Mail(
            from_email=os.environ.get("SENDGRID_FROM_EMAIL"),
            to_emails=os.environ.get("SENDGRID_TO_EMAILS").split(","),
            subject="Message from {name} on JoeKalb.com/dev".format(name=name),
            html_content=html_message)

        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(email_message)
        logger.info("Responses for sending contact email for JoeKalb.com/dev...")
        logger.info(response.status_code)
        logger.info(response.body)
        logger.info(response.headers)
        success_j = j = {
            "status": "success"
        }
        return json.dumps(success_j),200,{'Content-Type': 'application/json'}

    except werkzeug.exceptions.BadRequest as br:
        traceback.print_exc()
        error_j = {
            "status":"error",
            "error_message":str(br)
        }
        return json.dumps(error_j),400,{'Content-Type': 'application/json'}

    except Exception as ex:
        traceback.print_exc()
        error_message = "Could not send contact email. Technical reason: {reason}".format(reason=str(ex))
        error_j = {
            "status":"error",
            "error_message":error_message
        }
        return json.dumps(error_j),500,{'Content-Type': 'application/json'}
    return

def add_selectable_to_by_letter_dict(selectable,starting_letter,by_letter_dict):
    if starting_letter not in by_letter_dict:
        by_letter_dict.update({starting_letter:[selectable]})
    else:
        selectables_list = by_letter_dict[starting_letter]
        selectables_list.append(selectable)
        selectables_list = sorted(selectables_list, key=lambda s: s.display_name)
        by_letter_dict.update({starting_letter:selectables_list})
    return by_letter_dict

def add_feature_to_by_primary_tag(feature,primary_tag,by_primary_tag_dict):
    if primary_tag not in by_primary_tag_dict:
        by_primary_tag_dict.update({primary_tag:[feature]})
    else:
        features_list = by_primary_tag_dict[primary_tag]
        features_list.append(feature)
        features_list = sorted(features_list, key=lambda f: f.name)
    return by_primary_tag_dict

def get_category_selectables_by_letter(features):
    selectables_by_letter = {}
    category_tags = set()
    selectable_type = "category"
    for feature in features:
        for tag in feature.tags:
            category_tags.add(tag)

    for tag in category_tags:
        starting_letter = tag.plural_description[0].upper()
        selectable = Selectable(type=selectable_type,display_name=tag.plural_description,short_name=tag.tag_name,starting_letter=starting_letter)
        selectables_by_letter = add_selectable_to_by_letter_dict(selectable=selectable,starting_letter=starting_letter,by_letter_dict=selectables_by_letter)

    return selectables_by_letter

def get_city_selectables_by_letter(areas):
    selectables_by_letter = {}
    for area in areas:
        starting_letter = area.name[0].upper()
        selectable = Selectable(type="city",display_name=area.name,short_name=area.short_name,starting_letter=starting_letter)
        selectables_by_letter = add_selectable_to_by_letter_dict(selectable=selectable,starting_letter=starting_letter,by_letter_dict=selectables_by_letter)

    return selectables_by_letter

def get_resource_selectables_by_letter(features):
    selectables_by_letter = {}
    for feature in features:
        starting_letter = feature.name[0].upper()
        selectable = Selectable(type="resource",display_name=feature.name,short_name=feature.short_name,starting_letter=starting_letter)
        selectables_by_letter = add_selectable_to_by_letter_dict(selectable=selectable,starting_letter=starting_letter,by_letter_dict=selectables_by_letter)

    return selectables_by_letter

def get_features_by_primary_tag(features):
    features_by_primary_tag = {}
    for feature in features:
        primary_tag = feature.primary_tag_obj
        features_by_primary_tag = add_feature_to_by_primary_tag(feature=feature,primary_tag=primary_tag,by_primary_tag_dict=features_by_primary_tag)

    return features_by_primary_tag

@app.route("/holistic")
@app.route("/holistic/")
def holistic_home():
    logger.info("Redirecting someone to /holistic/area/swfl")
    return redirect("/holistic/area/swfl")

#Holistic Search
"""
selectable_type (category/city/resource) [e.g. "Find Resources by _____"]

selectable_filter_type (city/category/None)
[e.g. "Find Resources by Category for _______"]

selectable_filter_value (string or None)

selectables
	display_name
	short_name
    starting_letter
"""
@app.route("/holistic/search")
@app.route("/holistic/search/")
def holistic_search():
    search_type = "category"   #default to Category
    city_filter = None
    tag_filter = None

    args = request.args
    if "type" in args:
        if args["type"].upper() == "CATEGORY":
            search_type = "category"
        elif args["type"].upper() == "CITY":
            search_type = "city"
        elif args["type"].upper() == "RESOURCE":
            search_type = "resource"

    if "cities" in args:
        cities = args["cities"].split(",")
        short_names = []
        display_names = []
        for city in cities:
            area = AreaModel.query.filter_by(short_name=city).first()
            if area != None:
                short_names.append(area.short_name)
                display_names.append(area.name)

        if len(short_names) > 0:
            city_filter = SelectableFilter(type="city",short_names=short_names,display_names=display_names)

    if "tags" in args and search_type == "resource":
        tags = args["tags"].split(",")
        short_names = []
        display_names = []

        for tag_name in tags:
            tag = TagModel.query.filter_by(tag_name=tag_name).first()
            if tag != None:
                short_names.append(tag.tag_name)
                display_names.append(tag.plural_description)

            if len(short_names) > 0:
                tag_filter = SelectableFilter(type="tag",short_names=short_names,display_names=display_names)

    all_areas = AreaModel.query.all()
    all_tags = TagModel.query.all()

    all_cities = []

    for area in all_areas:
        all_cities.append(area)
    all_cities = sorted(all_areas, key=lambda a: a.name)

    all_tags = sorted(all_tags, key=lambda a: a.description)

    filtered_features = FeatureModel.query.filter(FeatureModel.enabled==True)
    if tag_filter != None:
        filtered_features = filtered_features.filter(FeatureModel.tags.any(TagModel.tag_name.in_(tag_filter.short_names)))
    if city_filter != None:
        filtered_features = filtered_features.filter(FeatureModel.areas.any(AreaModel.short_name.in_(city_filter.short_names)))

    if search_type == "category":
        selectables_by_letter = get_category_selectables_by_letter(filtered_features)
    elif (search_type == "city"):
        selectables_by_letter = get_city_selectables_by_letter(all_cities)
    elif (search_type == "resource"):
        selectables_by_letter = get_resource_selectables_by_letter(filtered_features)

    geo_json_data = generate_geo_json_data_features(filtered_features)
    tags_map_data = generate_tags_map_data()
    areas_map_data = generate_areas_map_data()

    logger.info("Rendering holistic/search.html for selectable_type {search_type}, city_filter {city_filter}, tag_filter {tag_filter}".format(search_type=search_type,city_filter=(city_filter.short_names if city_filter != None else None),tag_filter=(tag_filter.short_names if tag_filter != None else None)))
    return render_template("holistic/search.html",selectable_type=search_type,city_filter=city_filter,tag_filter=tag_filter,selectables_by_letter=selectables_by_letter,all_cities=all_cities,all_tags=all_tags,geo_json_data=geo_json_data,tags_map_data=tags_map_data,cities_map_data=areas_map_data)

@app.route("/swflholistic")
@app.route("/swflholistic/")
def swflholistic_redirect():
    logger.info("Redirect from /swflholistic to /holistic/area/swfl")
    return redirect("/holistic/area/swfl")

@app.route("/swflholistic/viewtag.html")
def viewtag_redirect():
    logger.info("Redirect from viewtag.html")
    return redirect("/holistic/tag/{tag}".format(tag=request.args.get("tag")))

@app.route("/swflholistic/viewdetail.html")
def viewdetail_redirect():
    logger.info("Redirect from viewdetail.html")
    return redirect("/holistic/feature/{feature_short_name}".format(feature_short_name=request.args.get("short_name")))

@app.route("/holistic/about")
def about():
    logger.info("Rendering holistic/about.html")
    return render_template("holistic/about.html")

@app.route("/holistic/contact")
def holistic_contact():
    logger.info("Rendering holistic/contact.html")
    return render_template("holistic/contact.html")

@app.route("/holistic/area/<area_short_name>")
def index(area_short_name):
    logger.info("Redirecting from /holistic/area/{area_short_name} to holistic/map/...".format(area_short_name=area_short_name))
    return redirect("/holistic/map?cities={area_short_name}".format(area_short_name=area_short_name))

@app.route("/holistic/map")
def map():
    citiesArg = request.args.get("cities")
    tagsArg = request.args.get("tags")

    all_areas = AreaModel.query.all()

    filtered_areas = []
    filtered_area_short_names = []
    filtered_tags = TagModel.query.all()
    filtered_tag_names = []

    if citiesArg != None:
        cities = citiesArg.split(",")
        filtered_areas = AreaModel.query.filter(AreaModel.short_name.in_(cities)).all()
        if len(filtered_areas) == 0:
            #Default to swfl if no valid cities filter was applied
            filtered_areas = AreaModel.query.filter(AreaModel.short_name == "swfl").all()
    if tagsArg != None:
        tags = tagsArg.split(",")
        filtered_tags = TagModel.query.filter(TagModel.tag_name.in_(tags)).all()
        if len(filtered_tags) == 0:
            #Default to all_tags if no valid tags filter was applied
            filtered_tags = TagModel.query.all()

    for area in filtered_areas:
        filtered_area_short_names.append(area.short_name)
    for tag in filtered_tags:
        filtered_tag_names.append(tag.tag_name)

    filtered_features = FeatureModel.query.filter(FeatureModel.enabled==True)
    filtered_features = filtered_features.filter(FeatureModel.tags.any(TagModel.tag_name.in_(filtered_tag_names)))
    filtered_features = filtered_features.filter(FeatureModel.areas.any(AreaModel.short_name.in_(filtered_area_short_names)))

    geo_json_data = generate_geo_json_data_features(filtered_features.all())
    tags_map_data = generate_tags_map_data()
    areas_map_data = generate_areas_map_data()

    features_by_primary_tag = get_features_by_primary_tag(features=filtered_features)

    logger.info("Rendering holistic/map2.html for filtered_city_short_names = {filtered_area_short_names}, filtered_tags = {filtered_tags}".format(filtered_features=filtered_features,filtered_area_short_names=filtered_area_short_names,filtered_tags=filtered_tags))
    return render_template("holistic/map2.html",features=filtered_features,geo_json_data=geo_json_data,tags_map_data=tags_map_data,cities_map_data=areas_map_data,city=filtered_areas[0],filtered_city_short_names=filtered_area_short_names,filtered_cities=filtered_areas,all_cities=all_areas,features_by_primary_tag=features_by_primary_tag,filtered_tags=filtered_tags)

@app.route("/holistic/feature/<short_name>")
def featurePage(short_name):
    feature = FeatureModel.query.filter(and_(FeatureModel.short_name == short_name, FeatureModel.enabled == True)).first()
    logger.info("Rendering holistic/feature.html for {feature}".format(feature=feature))
    return render_template("holistic/feature.html",feature=feature)

@app.route("/holistic/tag/<tag_name>")
def tagPage(tag_name):
    tag = TagModel.query.filter(TagModel.tag_name == tag_name).first()
    logger.info("Rendering holistic/tag.html for {tag}".format(tag=tag))
    return render_template("holistic/tag.html",tag=tag)

@app.route("/holistic/load-json-from-database")
def build_json_from_database():
    return generate_json_from_database()

@app.route("/holistic/addfeature")
def add_feature():
    all_areas = AreaModel.query.all()
    all_tags = TagModel.query.all()
    logger.info("Rendering holistic/new_feature.html")
    return render_template("holistic/new_feature.html",all_areas=all_areas,all_tags=all_tags)

@app.route("/holistic/api/feature", methods = ['POST'])
def api_feature():
    try:
        logger.info("\r\n\r\n\r\n\r\n")
        logger.info("Before get_json(), request is: {request}".format(request=request))
        input_payload = request.get_json()

        logger.info("Loaded input_payload {input_payload}".format(input_payload=input_payload))

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
            logger.info("optional field short_name not entered")

        try:
            phone = input_payload["phone"]
        except KeyError as ke:
            logger.info("optional field phone not entered")

        try:
            url = input_payload["url"]
        except KeyError as ke:
            logger.info("optional field url not entered")

        if short_name != None and not isinstance(short_name,str):
            error_j = {"status":"error","error_message":"short_name must be of type string."}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        if short_name == None or short_name == "":
            short_name = "autogen"

        f = FeatureModel.query.filter(FeatureModel.short_name==short_name).first()
        if f != None:
            i = 0
            while True:
                str_gen_short_name = "{short_name}{i}".format(short_name=short_name,i=i)
                f = FeatureModel.query.filter(FeatureModel.short_name==str_gen_short_name).first()
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
        elif TagModel.query.filter(TagModel.tag_name==primary_tag).first() == None:
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
            tm = TagModel.query.filter(TagModel.tag_name==tag).first()
            if tm != None:
                new_fm.tags.append(tm)
            else:
                error_j = {"status":"error","error_message":"tags entry '{tag_name}' is invalid.".format(tag_name=tag)}
                return json.dumps(error_j),500,{'Content-Type': 'application/json'}


        for area in areas:
            am = AreaModel.query.filter(AreaModel.short_name==area).first()
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

@app.route("/holistic/sendContactEmail", methods = ['POST'])
def holistic_send_contact_email_page():
    try:
        logger.info("\r\n\r\n\r\n\r\nSENDING HOLISTIC CONTACT EMAIL")
        logger.info("Before get_json(), request is: {request}".format(request=request))
        input_payload = request.get_json()

        logger.info("Loaded input_payload {input_payload}".format(input_payload=input_payload))

        name = None
        email = None
        message = None

        try:
            name = input_payload["name"]
            email = input_payload["email"]
            message = input_payload["message"]

        except KeyError as ke:
            error_j = {"status":"error","error_message":"Missing required field {key}".format(key=ke)}
            return json.dumps(error_j),500,{'Content-Type': 'application/json'}

        subject = "Message from {name} on JoeKalb.com/holistic".format(name=name)
        html_message =  subject + "<br /><br />From Email: " + email + "<br /><br />" + message
        email_message = Mail(
            from_email=os.environ.get("SENDGRID_FROM_EMAIL"),
            to_emails=os.environ.get("SENDGRID_TO_EMAILS").split(","),
            subject="Message from {name} on JoeKalb.com/holistic".format(name=name),
            html_content=html_message)

        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(email_message)
        logger.info("Responses for sending contact email for JoeKalb.com/holistic...")
        logger.info(response.status_code)
        logger.info(response.body)
        print(response.headers)
        success_j = j = {
            "status": "success"
        }
        return json.dumps(success_j),200,{'Content-Type': 'application/json'}

    except werkzeug.exceptions.BadRequest as br:
        traceback.print_exc()
        error_j = {
            "status":"error",
            "error_message":str(br)
        }
        return json.dumps(error_j),400,{'Content-Type': 'application/json'}

    except Exception as ex:
        traceback.print_exc()
        error_message = "Could not send contact email. Technical reason: {reason}".format(reason=str(ex))
        error_j = {
            "status":"error",
            "error_message":error_message
        }
        return json.dumps(error_j),500,{'Content-Type': 'application/json'}
    return

if __name__ == "__main__":
    app.run()
