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

from models import Feature as FeatureModel
from models import Tag as TagModel
from models import Area as AreaModel
from models import AreaFeature as AreaFeatureModel

from selectable import Selectable


def send_success_email(payload):
    sender = os.environ.get("SENDGRID_FROM_EMAIL")
    receivers = os.environ.get("SENDGRID_TO_EMAILS").split(",")
    subject = 'Holistic Resource added to directory'
    html_content = """Holistic resource added to directory, please confirm via your PythonAnywhere database account.

    {payload}
    """.format(payload=payload)
    message = Mail(
        from_email=sender,
        to_emails=receivers,
        subject=subject,
        html_content=html_content)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        print("Responses for holistic resource added-to-directory email...")
        print(response.status_code)
        print(response.body)
        print(response.headers)
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

@app.route("/")
def home_page():
    return redirect("/dev")

@app.route("/dev")
def dev_home_page():
    return render_template("dev/index.html")

@app.route("/dev/index.html")
def dev_home_page_redirect():
    return redirect("/dev")

@app.route("/dev/experience.html")
def dev_experience_page():
    return render_template("dev/experience.html")

@app.route("/dev/about.html")
def dev_about_page():
    return render_template("dev/about.html")

@app.route("/dev/contact.html")
def dev_contact_page():
    return render_template("dev/contact.html")

@app.route("/dev/sendContactEmail", methods = ['POST'])
def dev_send_contact_email_page():
    try:
        print("\r\n\r\n\r\n\r\n")
        print("Before get_json(), request is: {request}".format(request=request))
        input_payload = request.get_json()

        print("Loaded input_payload {input_payload}".format(input_payload=input_payload))

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
        print("Responses for sending contact email for JoeKalb.com/dev...")
        print(response.status_code)
        print(response.body)
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

def get_category_selectables_by_letter(features):
    selectables_by_letter = {}
    category_tags = set()
    selectable_type = "Category"
    for feature in features:
        category_tags.add(feature.primary_tag_obj)

    for tag in category_tags:
        starting_letter = tag.plural_description[0].upper()
        selectable = Selectable(type=selectable_type,display_name=tag.plural_description,short_name=tag.tag_name,starting_letter=starting_letter)

        if starting_letter not in selectables_by_letter:
            selectables_by_letter.update({starting_letter:[selectable]})
        else:
            selectables_list = selectables_by_letter[starting_letter]
            selectables_list.append(selectable)
            selectables_list = sorted(selectables_list, key=lambda s: s.display_name)
            selectables_by_letter.update({starting_letter:selectables_list})
    return selectables_by_letter

@app.route("/holistic")
@app.route("/holistic/")
def holistic_home():
    return redirect("/holistic/area/swfl")

#Holistic Search
"""
selectable_type (Category/City/Resource) [e.g. "Find Resources by _____"]

selectable_filter_type (City/Category/None)
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
    search_type = "Category"   #default to Category
    selectable_filter_type = None
    selectable_filter_value = None

    args = request.args
    if "type" in args:
        if args["type"] == "category":
            search_type = "Category"
        elif args["type"] == "city":
            search_type = "City"
        elif args["type"] == "resource":
            search_type = "Resource"

    if "city" in args:
        area = AreaModel.query.filter_by(short_name=args["city"]).first()
        if area != None:
            selectable_filter_type = "City"
            selectable_filter_short_name = area.short_name
            selectable_filter_display_value = area.name

    all_areas = AreaModel.query.all()
    all_cities = []
    for area in all_areas:
        all_cities.append(area)
    all_cities = sorted(all_areas, key=lambda a: a.name)

    if (search_type == "Category" and selectable_filter_short_name == None):
        all_enabled_features = FeatureModel.query.filter_by(enabled=True)
        selectables_by_letter = get_category_selectables_by_letter(all_enabled_features)
    elif (search_type == "Category" and selectable_filter_short_name != None):
        all_areafeatures_for_city = AreaFeatureModel.query.filter_by(area_short_name=selectable_filter_short_name)
        all_enabled_features_for_city = []
        for areafeature in all_areafeatures_for_city:
            feature = FeatureModel.query.filter_by(short_name=areafeature.feature_short_name).first()
            if feature.enabled:
                all_enabled_features_for_city.append(feature)
        selectables_by_letter = get_category_selectables_by_letter(all_enabled_features_for_city)

    return render_template("holistic/search.html",selectable_type=search_type,selectable_filter_type=selectable_filter_type,selectable_filter_display_value=selectable_filter_display_value,selectable_filter_short_name=selectable_filter_short_name,selectables_by_letter=selectables_by_letter,all_cities=all_cities)

@app.route("/swflholistic")
@app.route("/swflholistic/")
def swflholistic_redirect():
    return redirect("/holistic/area/swfl")

@app.route("/swflholistic/viewtag.html")
def viewtag_redirect():
    return redirect("/holistic/tag/{tag}".format(tag=request.args.get("tag")))

@app.route("/swflholistic/viewdetail.html")
def viewdetail_redirect():
    return redirect("/holistic/feature/{feature_short_name}".format(feature_short_name=request.args.get("short_name")))

@app.route("/holistic/about")
def about():
    return render_template("holistic/about.html")

@app.route("/holistic/area/<area_short_name>")
def index(area_short_name):
    area = AreaModel.query.filter_by(short_name=area_short_name).first()
    areas = AreaModel.query.all()
    tags = TagModel.query.all()
    if area == None:
        return "No area in data set with identifier {area_short_name}".format(area_short_name=area_short_name)
    geo_json_data = generate_geo_json_data(area)
    tags_map_data = generate_tags_map_data()
    area_enabled_features = []
    for feature in area.features:
        if feature.enabled:
            area_enabled_features.append(feature)
    return render_template("holistic/main_page.html",tags=tags,features=area_enabled_features,geo_json_data=geo_json_data,tags_map_data=tags_map_data,area=area,areas=areas)

@app.route("/holistic/feature/<short_name>")
def featurePage(short_name):
    feature = FeatureModel.query.filter_by(short_name = short_name, enabled = True).first()
    return render_template("holistic/feature.html",feature=feature)

@app.route("/holistic/tag/<tag_name>")
def tagPage(tag_name):
    tag = TagModel.query.filter_by(tag_name = tag_name).first()
    print(tag.features)
    return render_template("holistic/tag.html",tag=tag)

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
    return render_template("holistic/new_feature.html",all_areas=all_areas,all_tags=all_tags)

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
