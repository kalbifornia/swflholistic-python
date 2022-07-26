from flask import Flask, render_template
from flask_graphql import GraphQLView
from flask_sqlalchemy import SQLAlchemy
import typing
import graphene
import os
import json

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.do')
app.config.from_file(os.path.join(".", "config/default_app_config.json"), load=json.load,silent=False)  #default settings
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("SQLALCHEMY_DATABASE_URI","Specified environment variable is not set.")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = os.environ.get("SQLALCHEMY_TRACK_MODIFICATIONS","Specified environment variable is not set.")
db = SQLAlchemy(app)

from models import Feature as FeatureModel
from models import Tag as TagModel

def generate_geo_json_data():
    features_json_dicts = []
    all_enabled_features = FeatureModel.query.filter_by(enabled=True)
    for feature in all_enabled_features:
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
    with open("static/json/wapf-naples.json", "r") as json_file:
        json_obj = json.load(json_file)

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
def index():
    geo_json_data = generate_geo_json_data()
    tags_map_data = generate_tags_map_data()
    all_enabled_features = FeatureModel.query.filter_by(enabled=True)
    return render_template("main_page.html",features=all_enabled_features,geo_json_data=geo_json_data,tags_map_data=tags_map_data)

@app.route("/feature/<short_name>")
def featurePage(short_name):
    feature = FeatureModel.query.filter_by(short_name = short_name, enabled = True).first()
    return render_template("feature.html",feature=feature)

@app.route("/tag/<tag_name>")
def tagPage(tag_name):
    tag = TagModel.query.filter_by(tag_name = tag_name).first()
    print(tag.features)
    return render_template("tag.html",tag=tag)

@app.route("/viewdetails.html")
def details():
    return render_template("viewdetails.html")

@app.route("/viewtag.html")
def tag():
    return render_template("viewtag.html")

@app.route("/load-json-from-database")
def build_json_from_database():
    return generate_json_from_database()

@app.route("/load-database-from-json-XYZ")
def load_database_from_json_xyz():
    load_database_from_json()
    return "Loaded the database."

@app.route("/do-the-load")
def do_the_load():
    feature1 = FeatureModel(short_name="dagostino",enabled=True,name="D'Agostino Chiropractic",description="Family chiropractic center which aims to help their patients thrive by correcting their underlying structural and chemical health imbalances by scientifically utilizing natural healing methods",why_on_wapf_list="Dr. D'Agostino is a WAPF member who utilizes diet and other natural healing methods",primary_tag="chiro",address="1338 Del Prado Blvd S, Cape Coral, FL 33990",phone="239-573-8918",url="https://www.drtonycapecoral.com",longitude=-81.940857,latitude=26.627038,type="Point")
    feature2 = FeatureModel(short_name="doctorbrie",enabled=True,name="Pediatric and Perinatal Chiropractic Center",description="Pediatric and Perinatal Chiropractic Center is a holistic chiropractic center in Fort Myers. The doctors at this office can serve as primary care provider for both children and their parents. They also have their own whole foods supplements.",why_on_wapf_list="Dr. Brie and her teammates employ holistic and natural practices to encourage health in their patients, and they are generally in line with WAPF principles. They encourage parental freedoms and choice when it comes to vaccines.",primary_tag="chiro",address="12731 World Plaza Ln. Bldg 83 Suite 1, Fort Myers Fort Myers, FL 33907",phone="239-887-3283",url="https://www.doctorbrie.com",longitude=-81.87827,latitude=26.55856,type="Point")

    chiro_tag = TagModel(tag_name="chiro",description="Chiropractic",plural_description="Chiropractors",parent_category="healing_arts")
    wapf_member_operated_tag = TagModel(tag_name="wapf_member_operated",description="Operated by WAPF Member",plural_description="Operated by WAPF Members",parent_category="other")
    healing_arts_tag = TagModel(tag_name="healing_arts",description="Healing Arts",plural_description="Healing Arts",parent_category="healing_arts")
    pediatrics_tag = TagModel(tag_name="pediatrics",description="Pediatrics",parent_category="healing_arts",plural_description="Pediatricians")

    feature1.tags.append(chiro_tag)
    feature1.tags.append(wapf_member_operated_tag)
    feature1.tags.append(healing_arts_tag)

    feature2.tags.append(chiro_tag)
    feature2.tags.append(healing_arts_tag)
    feature2.tags.append(pediatrics_tag)

    db.session.add(feature1)
    db.session.add(feature2)
    db.session.commit()

    tags_json_dicts = []
    allTags = TagModel.query.all()
    for tag in allTags:
        tags_json_dicts.append(tag.to_json_dict())

    j = {
        "features": [feature1.to_json_dict(),feature2.to_json_dict()],
        "type": "FeatureCollection",
        "tagDescriptions": tags_json_dicts,

    }

    json_output = json.dumps(j,indent=2)

    output = "Did the load... {json_output}.".format(json_output=json_output)

    with open("static/json/new_json.json", "w") as fo:
        fo.write(json_output)

    return output


if __name__ == "__main__":
    app.run()
