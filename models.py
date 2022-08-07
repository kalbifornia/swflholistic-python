from sqlalchemy import Column,Integer,Float,String,Boolean,create_engine,ForeignKey,UniqueConstraint,PrimaryKeyConstraint
from sqlalchemy.orm import (scoped_session, sessionmaker, relationship, backref)
from sqlalchemy.ext.declarative import declarative_base
from app import db
import json

class Feature(db.Model):
    __tablename__ = "feature"
    short_name = Column("short_name",String(20),primary_key=True)
    enabled = Column("enabled",Boolean)
    name = Column("name",String(100))
    description = Column("description",String(1000))
    why_on_wapf_list = Column("why_on_wapf_list",String(1000))
    tags = relationship("Tag",secondary="featuretag", order_by="FeatureTag.tag_name", back_populates="features")
    areas = relationship("Area",secondary="areafeature", order_by="AreaFeature.area_short_name", back_populates="features")
    primary_tag = Column("primary_tag",String(20),ForeignKey("tag.tag_name"))
    primary_tag_obj = relationship("Tag",back_populates="features_primary_tag_for")
    longitude = Column("longitude",Float)
    latitude = Column("latitude",Float)
    address = Column("address",String(200))
    phone = Column("phone",String(30))
    url = Column("url",String(150))
    type = Column("type",String(30))

    def to_json_dict(self):
        tag_names = []
        for tag in self.tags:
            tag_names.append(tag.tag_name)

        j = {
            "type": "Feature",
            "properties": {
                "short_name": self.short_name,
                "enabled": self.enabled,
                "name": self.name,
                "description": self.description,
                "why_on_wapf_list": self.why_on_wapf_list,
                "tags": tag_names,
                "primary_tag": self.primary_tag,
                "address": self.address,
                "phone": self.phone,
                "url": self.url
            },
            "geometry": {
                "coordinates": [self.longitude, self.latitude],
                "type": self.type
            }
        }
        return j

class Tag(db.Model):
    __tablename__ = "tag"
    tag_name = Column("tag_name",String(20),primary_key=True)
    description = Column("description",String(100))
    parent_category = Column("parent_category",String(20))
    plural_description = Column("plural_description",String(100))
    features = relationship("Feature",secondary="featuretag", order_by="FeatureTag.feature_short_name", back_populates="tags")
    features_primary_tag_for = relationship("Feature", order_by="Feature.short_name", back_populates="primary_tag_obj")

    def to_json_dict(self):
        j = {
            "tag": self.tag_name,
            "description": self.description,
            "parent_category": self.parent_category,
            "plural_description": self.plural_description
        }
        return j

class Area(db.Model):
    __tablename__ = "area"
    short_name = Column("short_name",String(20),primary_key=True)
    short_display_name = Column("short_display_name",String(30))
    name = Column("name",String(100))
    wapf_chapter_name = Column("wapf_chapter_name",String(100))
    longitude = Column("longitude",Float)
    latitude = Column("latitude",Float)
    features = relationship("Feature",secondary="areafeature", order_by="AreaFeature.feature_short_name", back_populates="areas")

class AreaFeature(db.Model):
    __tablename__ = "areafeature"
    area_short_name = Column("area_short_name",String(20),ForeignKey("area.short_name"))
    feature_short_name = Column("feature_short_name",String(20),ForeignKey("feature.short_name"))
    __table_args__ = (PrimaryKeyConstraint("area_short_name","feature_short_name"),)

class FeatureTag(db.Model):
    __tablename__ = "featuretag"
    feature_short_name = Column("feature_short_name",String(20),ForeignKey("feature.short_name"))
    tag_name = Column("tag_name",String(20),ForeignKey("tag.tag_name"))
    __table_args__ = (PrimaryKeyConstraint("feature_short_name","tag_name"),)

db.create_all()
